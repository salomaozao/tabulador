"""Testes do status 'alterada' e reconferência após mudanças no quadro (codeframe e coding).
Verifica que alterações na definição, mesclagem (fundir) e exclusão (remover)
marcam respostas já conferidas com 'alterada' para reconferência.

Rodar:  python -m unittest tests.test_alterada -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="tabulador_alterada_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import protecao  # noqa: E402

QID = "Q_TESTE"


class TestStatusAlterada(unittest.TestCase):
    def setUp(self):
        self.qid = f"Q_{self._testMethodName}"
        self.frame = {
            "pergunta": self.qid, "status": "aprovado", "fixo": False, "versao": 1, "historico": [],
            "categorias": [
                {"codigo": 1, "nome": "Professores", "definicao": "fala dos professores", "exemplos": ["bons professores"], "keywords": ["professor"], "fixa": False},
                {"codigo": 2, "nome": "Estrutura", "definicao": "prédio, salas, quadra", "exemplos": ["quadra"], "fixa": False},
                {"codigo": 3, "nome": "Preço", "definicao": "mensalidade, valor", "exemplos": [], "fixa": False},
                *[dict(f) for f in CF.FIXAS]
            ]
        }
        self.respostas = {
            "pergunta": self.qid, "enunciado": "Teste", "n_respondeu": 4, "n_unicas": 4, "n_nsnr_auto": 0,
            "respostas": [
                {"rid": 1, "texto": "os professores são ótimos", "n": 1, "chave": "os professores sao otimos", "nsnr": False, "respondent_ids": [1]},
                {"rid": 2, "texto": "professores atenciosos", "n": 1, "chave": "professores atenciosos", "nsnr": False, "respondent_ids": [2]},
                {"rid": 3, "texto": "a quadra é boa", "n": 1, "chave": "a quadra e boa", "nsnr": False, "respondent_ids": [3]},
                {"rid": 4, "texto": "mensalidade barata", "n": 1, "chave": "mensalidade barata", "nsnr": False, "respondent_ids": [4]},
            ]
        }
        # rid 1: confirmada em Professores (1)
        # rid 2: corrigida em Professores (1)
        # rid 3: confirmada em Estrutura (2)
        # rid 4: pendente em Preço (3)
        self.cod = {
            "pergunta": self.qid, "status": "aprovado",
            "itens": [
                {"rid": 1, "primaria": 1, "secundaria": None, "confianca": 0.9, "origem": "llm", "validado": True, "validado_por": "humano"},
                {"rid": 2, "primaria": 1, "secundaria": None, "confianca": 1.0, "origem": "humano", "corrigido_de": 2},
                {"rid": 3, "primaria": 2, "secundaria": None, "confianca": 0.85, "origem": "llm", "validado": True, "validado_por": "humano"},
                {"rid": 4, "primaria": 3, "secundaria": None, "confianca": 0.7, "origem": "llm"},
            ]
        }
        CF._gravar(self.qid, "frame.json", self.frame)
        CF._gravar(self.qid, "respostas.json", self.respostas)
        CF._gravar(self.qid, "codificacao.json", self.cod, permitir_reducao=True)

    def test_renomear_definicao_marca_alterada(self):
        # Mudar a definição da categoria 1
        CF.renomear(self.qid, 1, "Professores", nova_definicao="fala dos professores e pedagogia (não inclui estrutura)")

        cod = CF._ler(self.qid, "codificacao.json")
        por_rid = {i["rid"]: i for i in cod["itens"]}

        # rid 1 e rid 2 estavam em Professores e foram revisados -> devem estar 'alterada'
        self.assertTrue(por_rid[1].get("alterada"))
        self.assertIn("alterada", por_rid[1].get("alterada_motivo", "").lower())
        self.assertEqual(CD.situacao_revisao(por_rid[1]), "alterada")

        self.assertTrue(por_rid[2].get("alterada"))
        self.assertEqual(CD.situacao_revisao(por_rid[2]), "alterada")

        # rid 3 estava em Estrutura (2) -> intocado
        self.assertFalse(por_rid[3].get("alterada"))
        self.assertEqual(CD.situacao_revisao(por_rid[3]), "confirmada")

        # rid 4 era pendente -> intocado
        self.assertFalse(por_rid[4].get("alterada"))
        self.assertEqual(CD.situacao_revisao(por_rid[4]), "pendente")

        # resumo_revisao reporta n_alteradas = 2
        resumo = CD.resumo_revisao(self.qid)
        self.assertEqual(resumo["n_alteradas"], 2)
        # n_revisadas só conta as que estão confirmadas/corrigidas efetivamente
        self.assertEqual(resumo["n_revisadas"], 1)  # apenas rid 3

    def test_revalidar_limpa_status_alterada(self):
        # Altera definição
        CF.renomear(self.qid, 1, "Professores", nova_definicao="nova definicao")

        # Reconferir rid 1 via validar
        n = CD.validar(self.qid, [1], valor=True, por="revisor")
        self.assertEqual(n, 1)

        cod = CF._ler(self.qid, "codificacao.json")
        por_rid = {i["rid"]: i for i in cod["itens"]}
        self.assertFalse(por_rid[1].get("alterada"))
        self.assertEqual(CD.situacao_revisao(por_rid[1]), "confirmada")

        # Reconferir rid 2 via atualizar_item (corrigindo para Estrutura)
        CD.atualizar_item(self.qid, 2, primaria=2, por="revisor")
        cod = CF._ler(self.qid, "codificacao.json")
        por_rid = {i["rid"]: i for i in cod["itens"]}
        self.assertFalse(por_rid[2].get("alterada"))
        self.assertEqual(CD.situacao_revisao(por_rid[2]), "corrigida")
        self.assertEqual(por_rid[2]["primaria"], 2)

    def test_fundir_marca_alterada(self):
        # Mesclar categoria 2 em 1
        CF.fundir(self.qid, 1, 2)

        cod = CF._ler(self.qid, "codificacao.json")
        por_rid = {i["rid"]: i for i in cod["itens"]}

        # rid 3 era da categoria 2 -> remapeado para 1 e marcado alterada
        self.assertEqual(por_rid[3]["primaria"], 1)
        self.assertTrue(por_rid[3].get("alterada"))
        self.assertEqual(por_rid[3].get("alterada_de"), 2)
        self.assertIn("mesclada", por_rid[3].get("alterada_motivo", "").lower())
        self.assertEqual(CD.situacao_revisao(por_rid[3]), "alterada")

    def test_remover_marca_alterada(self):
        # Remover categoria 3 (rid 4 é pendente, mas vamos confirmar rid 4 primeiro)
        CD.validar(self.qid, [4], valor=True)
        CF.remover(self.qid, 3)

        cod = CF._ler(self.qid, "codificacao.json")
        por_rid = {i["rid"]: i for i in cod["itens"]}

        # rid 4 vai para Outros (97) e fica como alterada
        self.assertEqual(por_rid[4]["primaria"], 97)
        self.assertTrue(por_rid[4].get("alterada"))
        self.assertEqual(por_rid[4].get("alterada_de"), 3)
        self.assertEqual(CD.situacao_revisao(por_rid[4]), "alterada")


if __name__ == "__main__":
    unittest.main()
