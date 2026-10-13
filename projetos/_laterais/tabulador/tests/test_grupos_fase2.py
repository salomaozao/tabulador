"""Fase 2 dos grupos (docs/IP_grupos_de_perguntas.md): aprovação do quadro POR PERGUNTA, grupo fechado
quando todas as perguntas concluem e aviso de impacto antes de mexer num quadro já usado.

Rodar:  python -m unittest tests.test_grupos_fase2 -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["TABULADOR_OUTPUT"] = tempfile.mkdtemp(prefix="tabulador_grupos_f2_")  # nuvem desligada
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import config  # noqa: E402
import grupos_frame  # noqa: E402
import variables as V  # noqa: E402
from tests.test_grupos_fase1 import Base, Projeto, cat  # noqa: E402


class TestAprovacaoPorPergunta(Base):
    def test_aprovar_uma_nao_aprova_a_outra(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        self.assertEqual(CF.frame("Q32")["status"], "aprovado")
        self.assertEqual(CF.frame("Q33")["status"], "rascunho")

    def test_trava_de_classificacao_segue_a_aprovacao_da_pergunta(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        self.assertEqual(CF._exigir_frame("Q32")["status"], "aprovado")  # é o que coding.py checa
        self.assertNotEqual(CF._exigir_frame("Q33")["status"], "aprovado")

    def test_status_gravado_no_grupo_nao_vaza_de_uma_pergunta_para_a_outra(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        CF.adicionar("Q32", "Transporte")  # leitura por Q32 e gravação de volta
        self.assertEqual(CF.frame("Q33")["status"], "rascunho")
        bruto = grupos_frame.frame("motivo_troca")
        self.assertNotIn("aprovado_em", bruto)
        self.assertEqual(bruto["status"], "aprovado" if bruto["aprovacoes"] else "rascunho")

    def test_pergunta_fora_do_grupo_nao_aprova(self):
        self.quadro_do_grupo()
        with self.assertRaises(ValueError):
            grupos_frame.aprovar_pergunta("motivo_troca", "Q1")

    def test_quadro_antigo_aprovado_vale_para_todas(self):
        f = self.quadro_do_grupo(status="aprovado")  # formato antigo: sem "aprovacoes"
        self.assertNotIn("aprovacoes", f)
        self.assertEqual(CF.frame("Q32")["status"], "aprovado")
        self.assertEqual(CF.frame("Q33")["status"], "aprovado")

    def test_gerar_do_zero_limpa_as_aprovacoes(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        grupos_frame._gravar_grupo("motivo_troca", "respostas.json", {
            "n_unicas": 1, "n_total": 1, "respostas": [{"rid": 1, "origem_qid": "Q32", "n": 1, "texto": "caro", "nsnr": False}]})
        saida = {"raciocinio": "", "categorias": [{"nome": "Preço", "definicao": "d", "exemplos": [], "keywords": []}]}
        with patch.object(grupos_frame, "preparar", lambda nome: grupos_frame.respostas(nome)), \
                patch("llm.chamar_json", lambda *a, **k: saida):
            grupos_frame.induzir("motivo_troca", forcar=True)
        self.assertEqual(CF.frame("Q32")["status"], "rascunho")
        self.assertEqual(grupos_frame.frame("motivo_troca")["aprovacoes"], {})
        self.assertEqual(grupos_frame.frame("motivo_troca")["cobertura"]["perguntas"]["Q32"], {"unicas": 1, "lidas": 1})


class TestFechamentoDoGrupo(Base):
    def test_fecha_so_quando_todas_estao_concluidas(self):
        self.quadro_do_grupo()
        self.assertFalse(grupos_frame.fechado("motivo_troca"))
        for q, status in (("Q32", "aprovado"), ("Q33", "rascunho")):
            CF._gravar(q, "codificacao.json", {"status": status, "itens": [{"rid": 1, "primaria": 1, "secundaria": None, "origem": "ia", "validado": False}]})
        self.assertFalse(grupos_frame.fechado("motivo_troca"))
        CF._gravar("Q33", "codificacao.json", {"status": "aprovado", "itens": [{"rid": 1, "primaria": 1, "secundaria": None, "origem": "ia", "validado": False}]})
        self.assertTrue(grupos_frame.fechado("motivo_troca"))

    def test_andamento_por_pergunta(self):
        self.quadro_do_grupo()
        CF.aprovar("Q33")
        a = {x["qid"]: x for x in grupos_frame.andamento("motivo_troca")}
        self.assertFalse(a["Q32"]["quadro_aprovado"])
        self.assertTrue(a["Q33"]["quadro_aprovado"])
        self.assertIsNone(a["Q33"]["classificacao"])


class TestImpacto(Base):
    def test_sem_trabalho_feito_nao_pede_confirmacao(self):
        self.quadro_do_grupo()
        self.assertEqual(grupos_frame.impacto_edicao("motivo_troca", "fundir")["nivel"], "baixo")

    def test_com_classificacao_pede_confirmacao_e_diz_quanto(self):
        self.quadro_do_grupo()
        self.classificar("Q33", [1, 2])
        imp = grupos_frame.impacto_edicao("motivo_troca", "fundir")
        self.assertEqual(imp["nivel"], "alto")
        self.assertIn("Q33: 2 respostas classificadas", imp["avisos"][0])

    def test_acao_leve_nunca_pede(self):
        self.quadro_do_grupo()
        self.classificar("Q33", [1])
        self.assertEqual(grupos_frame.impacto_edicao("motivo_troca", "keywords")["nivel"], "baixo")

    def test_aprovacao_sem_classificacao_avisa_mas_nao_bloqueia(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        imp = grupos_frame.impacto_edicao("motivo_troca", "fundir")
        self.assertEqual(imp["nivel"], "baixo")
        self.assertIn("Q32: já aprovou", imp["avisos"][0])

    def test_gerar_do_zero_com_aprovacao_pede_confirmacao(self):
        self.quadro_do_grupo()
        CF.aprovar("Q32")
        self.assertEqual(grupos_frame.impacto_edicao("motivo_troca", "induzir")["nivel"], "alto")


class TestRotaConfirmacao(Base):
    def setUp(self):
        super().setUp()
        import app as APP
        self.APP = APP

    def chamar(self, qid, acao, confirmado=None):
        with self.APP.app.test_request_context():
            r = self.APP._precisa_confirmar(qid, acao, confirmado)
            if r is None:
                return None, None
            resp, status = r
            return status, resp.get_json()

    def test_409_com_avisos_e_liberado_com_confirmado(self):
        self.quadro_do_grupo()
        self.classificar("Q33", [1])
        status, corpo = self.chamar("Q32", "fundir")
        self.assertEqual(status, 409)
        self.assertTrue(corpo["precisa_confirmar"])
        self.assertIn("Q33", corpo["avisos"][0])
        self.assertEqual(self.chamar("Q32", "fundir", confirmado=True), (None, None))

    def test_pergunta_sem_grupo_nunca_pede(self):
        self.assertEqual(self.chamar("Q1", "fundir"), (None, None))


if __name__ == "__main__":
    unittest.main()
