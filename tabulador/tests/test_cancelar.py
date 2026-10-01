"""Testes para o cancelamento de lote (pedir_parada) e garantia de que lotes com erro
não corrompem 'Outros' (código 97) nem 'origem: erro' nos itens (TASK-01).

Rodar: python -m unittest tests.test_cancelar -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="tabulador_cancelar_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import progresso  # noqa: E402


class TestCancelarETratamentoErros(unittest.TestCase):
    def test_pedir_parada_e_reset(self):
        progresso.iniciar("Teste", [("ia", "IA")])
        self.assertFalse(progresso.parada_pedida())
        progresso.pedir_parada()
        self.assertTrue(progresso.parada_pedida())
        progresso.iniciar("Outro", [("ia", "IA")])
        self.assertFalse(progresso.parada_pedida())

    def test_lote_com_erro_nao_grava_codigo_97_nem_origem_erro(self):
        """Respostas de lotes que falham não entram em itens, permanecendo pendentes."""
        itens = {}
        codigos_validos = {1: {"codigo": 1, "nome": "Cat 1", "definicao": "Def 1"}}
        pendentes = [
            {"rid": 1, "texto": "Resposta 1", "n": 1, "nsnr": False},
            {"rid": 2, "texto": "Resposta 2", "n": 1, "nsnr": False},
        ]
        frame = {
            "categorias": [
                {"codigo": 1, "nome": "Cat 1", "definicao": "Def 1"},
                {"codigo": 97, "nome": "Outros", "definicao": "Outras", "fixa": True},
            ]
        }

        with mock.patch("coding.llm.chamar_json", side_effect=RuntimeError("Erro simulado")):
            with mock.patch("config.LLM_LOTE", 10):
                with self.assertRaises(RuntimeError):
                    CD._chamar_lote("Q1", frame, "Pergunta 1", pendentes, itens, codigos_validos)

        # O lote falhou: itens deve continuar vazio! Nenhuma resposta virou 97 (Outros)
        self.assertEqual(itens, {})

    def test_lote_parcial_com_erro_preserva_lote_sucesso(self):
        """Se 1 lote der certo e 1 lote falhar, o de sucesso é gravado e o de erro fica pendente."""
        itens = {}
        codigos_validos = {1: {"codigo": 1, "nome": "Cat 1", "definicao": "Def 1"}}
        pendentes = [
            {"rid": 1, "texto": "Resposta 1", "n": 1, "nsnr": False},
            {"rid": 2, "texto": "Resposta 2", "n": 1, "nsnr": False},
        ]
        frame = {
            "categorias": [
                {"codigo": 1, "nome": "Cat 1", "definicao": "Def 1"},
                {"codigo": 97, "nome": "Outros", "definicao": "Outras", "fixa": True},
            ]
        }

        def fake_llm(system, user, schema, nome=""):
            if "code_Q1_1" in nome:
                return {
                    "codificacoes": [
                        {"rid": 1, "primaria": 1, "secundaria": None, "confianca": 0.95, "justificativa": "ok"}
                    ]
                }
            raise RuntimeError("Erro no lote 2")

        with mock.patch("coding.llm.chamar_json", side_effect=fake_llm):
            with mock.patch("config.LLM_LOTE", 1):
                with mock.patch("config.paralelo", return_value=1):
                    info = CD._chamar_lote("Q1", frame, "Pergunta 1", pendentes, itens, codigos_validos)

        # Apenas a resposta 1 foi gravada
        self.assertIn(1, itens)
        self.assertEqual(itens[1]["primaria"], 1)
        self.assertEqual(itens[1]["origem"], "llm")
        # A resposta 2 NÃO está em itens (não virou código 97)
        self.assertNotIn(2, itens)

    def test_codificacao_limpa_legado_de_erro(self):
        """Versões antigas gravavam erro de IA como 'Outros' (origem 'erro'). Na leitura, o item some
        (volta a 'não classificada'), salvo se tiver comentário; o que alguém confirmou vira humano."""
        gravado = {"itens": [
            {"rid": 1, "primaria": 97, "confianca": 0.0, "origem": "erro"},
            {"rid": 2, "primaria": 97, "confianca": 0.0, "origem": "erro", "validado": True},
            {"rid": 3, "primaria": 97, "confianca": 0.0, "origem": "erro", "comentario": "é elogio"},
            {"rid": 4, "primaria": 1, "confianca": 0.9, "origem": "llm"},
        ]}
        with mock.patch("coding.CF._ler", return_value=gravado):
            cod = CD.codificacao("Q1")
        por_rid = {i["rid"]: i for i in cod["itens"]}
        self.assertNotIn(1, por_rid)
        self.assertEqual(por_rid[2]["origem"], "humano")
        self.assertEqual(por_rid[3]["origem"], "erro")
        self.assertEqual(por_rid[4]["origem"], "llm")

    def test_parada_pedida_deixa_lotes_nao_iniciados_pendentes(self):
        itens = {}
        codigos_validos = {1: {"codigo": 1}}
        pendentes = [{"rid": r, "texto": f"R{r}", "n": 1, "nsnr": False} for r in (1, 2, 3)]
        frame = {"categorias": [{"codigo": 1, "nome": "Cat 1", "definicao": "Def 1"}]}

        def fake_llm(system, user, schema, nome=""):
            rid = int(nome.rsplit("_", 1)[1])
            if rid == 1:
                progresso.pedir_parada()  # a pessoa clica em Parar durante o 1º lote
            else:
                time.sleep(0.3)  # o 2º já foi disparado pelo pool (termina); o 3º ainda não começou
            return {"codificacoes": [{"rid": rid, "primaria": 1, "secundaria": None, "confianca": 0.9, "justificativa": ""}]}

        progresso.iniciar("Teste", [("ia", "IA")])
        with mock.patch("coding.llm.chamar_json", side_effect=fake_llm),                 mock.patch("config.LLM_LOTE", 1), mock.patch("config.paralelo", return_value=1):
            info = CD._chamar_lote("Q1", frame, "Pergunta 1", pendentes, itens, codigos_validos)
        self.assertTrue(info["parado_usuario"])
        self.assertIn(1, itens)
        self.assertNotIn(3, itens)  # cancelado antes de começar: continua pendente
        self.assertEqual(info["nao_tentados"], 1)


if __name__ == "__main__":
    unittest.main()
