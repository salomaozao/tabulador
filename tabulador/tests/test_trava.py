"""Trava de confirmações da pergunta (PEND-42): ligada, nada é confirmado nem aprovado até alguém desmarcar.

Sem IA, sem nuvem e sem planilha: frame, respostas e classificação entram por dicionário.
Rodar:  python -m unittest tests.test_trava -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="tabulador_trava_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import eventos  # noqa: E402
import supervisao as SUP  # noqa: E402


class TestTrava(unittest.TestCase):
    def setUp(self):
        self.qid = f"Q_{self._testMethodName}"
        CF._gravar(self.qid, "frame.json", {
            "pergunta": self.qid, "status": "aprovado", "fixo": False, "versao": 1, "historico": [],
            "categorias": [{"codigo": 1, "nome": "Professores", "definicao": "x", "exemplos": [], "fixa": False},
                           {"codigo": 2, "nome": "Estrutura", "definicao": "y", "exemplos": [], "fixa": False},
                           *[dict(f) for f in CF.FIXAS]]})
        CF._gravar(self.qid, "respostas.json", {
            "pergunta": self.qid, "enunciado": "Teste", "n_respondeu": 3, "n_unicas": 3, "n_nsnr_auto": 0,
            "respostas": [{"rid": r, "texto": f"resposta {r}", "n": 1, "chave": f"resposta {r}", "nsnr": False, "respondent_ids": [r]} for r in (1, 2, 3)]})
        CF._gravar(self.qid, "codificacao.json", {
            "pergunta": self.qid, "status": "rascunho",
            "itens": [{"rid": r, "primaria": 1, "secundaria": None, "confianca": 0.95, "origem": "llm",
                       "auditoria": {"por": "x", "ok": True, "em": "2026-10-02T10:00:00"}} for r in (1, 2, 3)]}, permitir_reducao=True)

    def test_travada_bloqueia_todas_as_formas_de_confirmar(self):
        t = CD.definir_trava(self.qid, True, por="Sara")
        self.assertEqual(t["por"], "Sara")
        self.assertEqual(CD.resumo_revisao(self.qid)["confirmacao_travada"]["por"], "Sara")
        with self.assertRaises(CD.ConfirmacaoTravada):
            CD.atualizar_item(self.qid, 1, validado=True)
        with self.assertRaises(CD.ConfirmacaoTravada):
            CD.validar(self.qid, [1, 2])
        with self.assertRaises(CD.ConfirmacaoTravada):
            SUP.auto_aceitar(self.qid, 0.5)
        with self.assertRaises(CD.ConfirmacaoTravada):
            CD.aprovar(self.qid)
        self.assertEqual(CD.resumo_revisao(self.qid)["n_confirmadas"], 0)  # nada mudou

    def test_travada_ainda_deixa_corrigir_e_desfazer_confirmacao(self):
        CD.validar(self.qid, [2])
        CD.definir_trava(self.qid, True)
        CD.atualizar_item(self.qid, 1, primaria=2, por="Ana")  # corrigir categoria é permitido
        self.assertEqual(CD.validar(self.qid, [2], valor=False), 1)  # desconfirmar também
        r = CD.resumo_revisao(self.qid)
        self.assertEqual((r["n_corrigidas"], r["n_confirmadas"]), (1, 0))

    def test_destravar_libera_e_fica_no_log(self):
        CD.definir_trava(self.qid, True, por="Sara")
        self.assertIsNone(CD.definir_trava(self.qid, False, por="João"))
        self.assertEqual(CD.validar(self.qid, [1, 2]), 2)
        acoes = [(e["acao"], e["quem"]) for e in eventos.listar(self.qid)]
        self.assertIn(("travar_confirmacoes", "Sara"), acoes)
        self.assertIn(("destravar_confirmacoes", "João"), acoes)

    def test_reclassificar_nao_destrava(self):
        CD.definir_trava(self.qid, True, por="Sara")
        CD.codificar(self.qid, forcar=True, somente_faltantes=True)  # nada falta: só regrava a codificação
        self.assertEqual(CD.codificacao(self.qid)["confirmacao_travada"]["por"], "Sara")


if __name__ == "__main__":
    unittest.main()
