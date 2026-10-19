"""Série cronológica do cabeçalho do painel (src/historico.py): % de perguntas classificadas e
revisadas ao longo dos dias. Sem IA, sem nuvem e sem projeto de verdade — os dados entram por
dicionário e o llm_log é uma pasta temporária de arquivos vazios.

Rodar:  python -m unittest tests.test_historico -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="tabulador_historico_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config  # noqa: E402
import historico as H  # noqa: E402

HOJE = date.today().isoformat()


def _pergunta(qid: str, n_unicas: int, n_codificadas: int, n_revisadas: int) -> dict:
    """O mesmo formato que report.status_pergunta devolve (é o que o /api/status passa adiante)."""
    return {"qid": qid, "rotulo": f"Pergunta {qid}", "n_unicas": n_unicas, "n_codificadas": n_codificadas,
            "n_revisadas": n_revisadas, "n_faltantes": n_unicas - n_codificadas}


def _confirmada(dia: str) -> dict:
    return {"rid": 1, "primaria": 1, "origem": "llm", "validado": True, "validado_em": f"{dia}T10:00:00"}


def _corrigida(dia: str) -> dict:
    return {"rid": 2, "primaria": 1, "origem": "humano", "revisado_em": f"{dia}T11:00:00"}


class TestSerieCronologica(unittest.TestCase):
    def setUp(self):
        self.log = Path(tempfile.mkdtemp(prefix="log_", dir=_TMP))
        patch = mock.patch.object(config, "LLM_LOG_OUT", self.log)
        patch.start()
        self.addCleanup(patch.stop)

    def _log(self, dia: str, nome: str) -> None:
        """Um arquivo de log com o nome que o llm.py usa: AAAAMMDD_HHMMSS_<n>_<nome>.json"""
        (self.log / f"{dia}_101010_1_{nome}.json").write_text("{}", encoding="utf-8")

    def test_carrega_o_dia_das_chamadas_de_classificacao(self):
        self._log("20260922", "code_Q1_2")
        self._log("20260924", "code_Q1_3")   # mesma pergunta, mais tarde: vale o último dia
        self._log("20260924", "code_Q2_1")
        self._log("20260924", "frame_Q3")    # indução de categorias não é classificação
        self._log("20260924", "teste_conexao")
        self.assertEqual(H.dias_de_classificacao(), {"Q1": "2026-09-24", "Q2": "2026-09-24"})

    def test_serie_acumula_por_dia_e_usa_perguntas_como_denominador(self):
        perguntas = [_pergunta("Q1", 10, 10, 10), _pergunta("Q2", 20, 20, 5), _pergunta("Q3", 30, 0, 0)]
        self._log("20260922", "code_Q1_1")
        self._log("20260922", "code_Q2_1")
        cod = {"itens": [_confirmada("2026-09-24")]}
        with mock.patch.object(H.CD, "codificacao", return_value=cod):
            r = H.resumo(perguntas)
        self.assertEqual(r["total"], 3)
        self.assertEqual((r["n_classificadas"], r["n_revisadas"], r["n_andamento"], r["n_a_iniciar"]), (2, 1, 1, 1))
        self.assertAlmostEqual(r["pct_revisadas"], 1 / 3)
        self.assertEqual(r["respostas"]["unicas"], 60)
        self.assertEqual(r["respostas"]["classificadas"], 30)
        self.assertEqual(r["respostas"]["revisadas"], 15)
        self.assertEqual(r["respostas"]["faltam"], 45)

        serie = r["serie"]
        # um ponto por dia com movimento + o dia de hoje no fim (a curva termina no presente)
        self.assertEqual([p["dia"] for p in serie], ["2026-09-22", "2026-09-24", HOJE] if HOJE != "2026-09-24"
                         else ["2026-09-22", "2026-09-24"])
        self.assertEqual((serie[0]["n_classificadas"], serie[0]["n_revisadas"]), (2, 0))
        self.assertEqual((serie[-1]["n_classificadas"], serie[-1]["n_revisadas"]), (2, 1))
        self.assertAlmostEqual(serie[-1]["pct_classificadas"], 2 / 3)
        # série também traz a contagem absoluta de respostas e o total
        self.assertEqual(serie[0]["respostas_revisadas"], 0)
        self.assertEqual(serie[-1]["respostas_total"], 60)
        self.assertEqual(serie[-1]["respostas_revisadas"], 15)
        # denominador = perguntas do projeto, nunca as respostas classificadas
        self.assertNotAlmostEqual(serie[-1]["pct_revisadas"], 15 / 30)
        # nunca anda para trás
        for antes, depois in zip(serie, serie[1:]):
            self.assertGreaterEqual(depois["n_revisadas"], antes["n_revisadas"])
            self.assertGreaterEqual(depois["n_classificadas"], antes["n_classificadas"])
            self.assertGreaterEqual(depois["respostas_revisadas"], antes["respostas_revisadas"])

    def test_classificacao_parcial_nao_entra_na_curva(self):
        perguntas = [_pergunta("Q1", 10, 4, 4)]  # amostra classificada, base inteira pendente
        self._log("20260922", "code_Q1_1")
        with mock.patch.object(H.CD, "codificacao", return_value={"itens": []}):
            r = H.resumo(perguntas)
        self.assertEqual(r["n_classificadas"], 0)
        self.assertEqual(r["n_revisadas"], 0)
        self.assertEqual(r["serie"], [])  # sem curva: nada concluído ainda
        self.assertEqual(r["respostas"]["classificadas"], 4)  # mas o progresso fino continua visível

    def test_revisao_confirmada_e_corrigida_valem_como_revisadas(self):
        perguntas = [_pergunta("Q1", 10, 10, 10)]
        self._log("20260922", "code_Q1_1")
        cod = {"itens": [_confirmada("2026-09-24"), _corrigida("2026-09-25")]}
        with mock.patch.object(H.CD, "codificacao", return_value=cod):
            r = H.resumo(perguntas)
        self.assertEqual(r["n_revisadas"], 1)
        self.assertEqual(r["perguntas"][0]["dia_revisada"], "2026-09-25")  # o carimbo mais recente
        self.assertEqual(r["serie"][0]["dia"], "2026-09-22")
        self.assertEqual(r["serie"][-1]["n_revisadas"], 1)

    def test_revisao_sem_carimbo_conta_a_partir_de_hoje(self):
        perguntas = [_pergunta("Q1", 10, 10, 10)]
        self._log("20260922", "code_Q1_1")
        cod = {"itens": [{"rid": 1, "primaria": 1, "origem": "humano", "revisado_em": None}]}
        with mock.patch.object(H.CD, "codificacao", return_value=cod):
            r = H.resumo(perguntas)
        self.assertEqual(r["n_revisadas"], 1)
        self.assertIsNone(r["perguntas"][0]["dia_revisada"])
        self.assertEqual(r["serie"][-1]["dia"], HOJE)
        self.assertEqual(r["serie"][-1]["n_revisadas"], 1)

    def test_projeto_sem_trabalho_nao_quebra(self):
        with mock.patch.object(H.CD, "codificacao", return_value=None):
            r = H.resumo([_pergunta("Q1", 10, 0, 0)])
        self.assertEqual((r["total"], r["n_revisadas"], r["n_a_iniciar"]), (1, 0, 1))
        self.assertEqual((r["pct_revisadas"], r["pct_classificadas"]), (0.0, 0.0))
        self.assertEqual(r["serie"], [])

    def test_sem_llm_log_a_serie_sai_do_carimbo_de_revisao(self):
        perguntas = [_pergunta("Q1", 10, 10, 10)]
        with mock.patch.object(H.CD, "codificacao", return_value={"itens": [_confirmada("2026-09-24")]}):
            r = H.resumo(perguntas)
        self.assertEqual([p["dia"] for p in r["serie"] if p["dia"] != HOJE], ["2026-09-24"])
        self.assertEqual(r["serie"][-1]["n_revisadas"], 1)


if __name__ == "__main__":
    unittest.main()
