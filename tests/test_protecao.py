"""Proteção contra perda da base classificada (src/protecao.py, PEND-24).

Cobre as três camadas nos dois modos (arquivo local e nuvem, esta com SQLite local no lugar do Turso):
guarda que recusa gravação que apaga trabalho conferido, versões anteriores com retenção, backup diário
e restauração de ponta a ponta (a restauração é a prova de que o backup serve).

Rodar:  python -m unittest tests.test_protecao -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codeframe as CF  # noqa: E402
import config  # noqa: E402
import nuvem  # noqa: E402
import protecao as P  # noqa: E402

QID = "Q1"


def _item(rid: int, origem: str = "llm", validado_por: str | None = None) -> dict:
    i = {"rid": rid, "primaria": 1, "origem": origem}
    if validado_por:
        i.update(validado=True, validado_por=validado_por)
    return i


def _cod(n: int = 20, humanos: int = 5, autos: int = 3) -> dict:
    itens = [_item(r) for r in range(n)]
    for r in range(humanos):
        itens[r] = _item(r, "llm", "humano")
    for r in range(humanos, humanos + autos):
        itens[r] = _item(r, "llm", "auto")
    return {"qid": QID, "status": "rascunho", "itens": itens}


class _Base(unittest.TestCase):
    usa_nuvem = False

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="tabulador_protecao_")
        self._antes = (config.TURSO_URL, config.TURSO_TOKEN, config.PROJETO, config.PERGUNTAS_OUT)
        config.PERGUNTAS_OUT = Path(self._tmp) / "perguntas"
        config.PROJETO = "projeto_teste"
        config.TURSO_URL, config.TURSO_TOKEN = (f"file:{Path(self._tmp) / 'teste.db'}" if self.usa_nuvem else None), None
        nuvem._cliente, nuvem._tabela_pronta = None, False
        nuvem._cache.clear()
        P._ultima_versao.clear()

    def tearDown(self):
        nuvem.fechar()
        nuvem._cliente, nuvem._tabela_pronta = None, False
        config.TURSO_URL, config.TURSO_TOKEN, config.PROJETO, config.PERGUNTAS_OUT = self._antes


class TestGuarda(_Base):
    def test_perder_conferido_e_recusado_e_nada_muda(self):
        CF._gravar(QID, "codificacao.json", _cod())
        ruim = _cod()
        ruim["itens"][0] = _item(0)  # um conferido por pessoa volta a "só IA"
        with self.assertRaises(P.GravacaoSuspeita):
            CF._gravar(QID, "codificacao.json", ruim)
        self.assertEqual(len(P._humanos(CF._ler(QID, "codificacao.json"))), 5)
        log = Path(config.PERGUNTAS_OUT).parent / "_backup" / "bloqueios.log"
        self.assertIn(QID, log.read_text(encoding="utf-8"))

    def test_encolher_mais_de_20_por_cento_e_recusado(self):
        CF._gravar(QID, "codificacao.json", _cod(n=100, humanos=0, autos=0))
        with self.assertRaises(P.GravacaoSuspeita):
            CF._gravar(QID, "codificacao.json", {"itens": [_item(r) for r in range(70)]})
        CF._gravar(QID, "codificacao.json", {"itens": [_item(r) for r in range(85)]})  # 15%: passa

    def test_base_pequena_nao_dispara_o_percentual(self):
        CF._gravar(QID, "codificacao.json", _cod(n=6, humanos=0, autos=0))
        CF._gravar(QID, "codificacao.json", {"itens": [_item(0), _item(1)]})

    def test_aceite_automatico_nao_conta_como_conferencia(self):
        CF._gravar(QID, "codificacao.json", _cod(n=20, humanos=0, autos=5))
        CF._gravar(QID, "codificacao.json", _cod(n=20, humanos=0, autos=0))  # desfazer o auto não perde trabalho humano

    def test_liberacao_explicita_deixa_reduzir(self):
        CF._gravar(QID, "codificacao.json", _cod())
        CF._gravar(QID, "codificacao.json", {"itens": []}, permitir_reducao=True)
        self.assertEqual(CF._ler(QID, "codificacao.json")["itens"], [])

    def test_apagar_codificacao_com_conferido_exige_liberacao_e_guarda_versao(self):
        CF._gravar(QID, "codificacao.json", _cod())
        with self.assertRaises(P.GravacaoSuspeita):
            CF._remover(QID, "codificacao.json")
        self.assertTrue(CF._existe(QID, "codificacao.json"))
        self.assertTrue(CF._remover(QID, "codificacao.json", permitir_reducao=True))
        self.assertFalse(CF._existe(QID, "codificacao.json"))
        self.assertEqual(CF.versoes(QID)["codificacao.json"][0]["motivo"], "antes de apagar")


class _Versoes:
    """Mesmos testes nos dois modos: a camada de versões e a restauração de ponta a ponta."""

    def test_salvar_antes_de_sobrescrever_e_throttle(self):
        CF._gravar(QID, "codificacao.json", _cod(humanos=5))
        self.assertEqual(CF.versoes(QID)["codificacao.json"], [])  # 1ª gravação: nada a guardar
        CF._gravar(QID, "codificacao.json", _cod(humanos=6))
        CF._gravar(QID, "codificacao.json", _cod(humanos=7))
        v = CF.versoes(QID)["codificacao.json"]
        self.assertEqual(len(v), 1, "dentro dos 15 min só o primeiro snapshot é gravado")
        self.assertEqual((v[0]["n_itens"], v[0]["n_humano"]), (20, 5))

    def test_snapshot_antes_ignora_o_intervalo(self):
        CF._gravar(QID, "codificacao.json", _cod(humanos=5))
        CF.snapshot_antes(QID, "classificar")
        CF.snapshot_antes(QID, "auditar")
        motivos = [v["motivo"] for v in CF.versoes(QID)["codificacao.json"]]
        self.assertEqual(sorted(motivos), ["auditar", "classificar"])

    def test_restaurar_de_ponta_a_ponta(self):
        original = _cod(n=30, humanos=10)
        CF._gravar(QID, "codificacao.json", original)
        CF.snapshot_antes(QID, "antes do desastre")
        CF._gravar(QID, "codificacao.json", {"itens": []}, permitir_reducao=True)  # o "desastre"
        self.assertEqual(CF._ler(QID, "codificacao.json")["itens"], [])
        quando = CF.versoes(QID)["codificacao.json"][0]["gravado_em"]
        r = CF.restaurar_versao(QID, "codificacao.json", quando)
        self.assertEqual((r["n_itens"], r["n_humano"]), (30, 10))
        self.assertEqual(CF._ler(QID, "codificacao.json"), original)
        motivos = [v["motivo"] for v in CF.versoes(QID)["codificacao.json"]]
        self.assertIn("antes de restaurar", motivos)  # a restauração também pode ser desfeita

    def test_restaurar_versao_inexistente_falha(self):
        with self.assertRaises(ValueError):
            CF.restaurar_versao(QID, "codificacao.json", "2000-01-01T00:00:00+00:00")
        with self.assertRaises(ValueError):
            CF.restaurar_versao(QID, "respostas.json", "x")

    def test_backup_do_projeto_e_diario(self):
        CF._gravar(QID, "codificacao.json", _cod())
        CF._gravar(QID, "frame.json", {"categorias": [{"codigo": 1, "nome": "A"}]})
        destino = P.backup_se_preciso()
        self.assertIsNotNone(destino)
        linhas = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual({(l["qid"], l["arquivo"]) for l in linhas}, {(QID, "codificacao.json"), (QID, "frame.json")})
        self.assertIsNone(P.backup_se_preciso(), "no mesmo dia não faz outro")
        self.assertIsNotNone(P.backup_se_preciso(forcar=True))


class TestVersoesLocal(_Versoes, _Base):
    pass


class TestVersoesNuvem(_Versoes, _Base):
    usa_nuvem = True


class TestRetencao(unittest.TestCase):
    def test_sete_dias_completos_depois_um_por_dia_ate_60(self):
        agora = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

        def ts(d, h):
            return (agora - timedelta(days=d)).replace(hour=h).isoformat()

        quando = [ts(1, 9), ts(1, 10), ts(6, 8),  # recentes: ficam todos
                  ts(10, 8), ts(10, 15), ts(30, 9),  # um por dia: sai o mais velho do dia 10
                  ts(61, 9), ts(90, 9)]  # além de 60 dias: saem
        self.assertEqual(sorted(P.a_podar(quando, agora)), sorted([ts(10, 8), ts(61, 9), ts(90, 9)]))


if __name__ == "__main__":
    unittest.main()
