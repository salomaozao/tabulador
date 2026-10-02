"""Fase 1 dos grupos (docs/IP_grupos_de_perguntas.md): amostra com cota por pergunta, cobertura,
edição do quadro compartilhado (remapeia a classificação de TODAS as perguntas) e regra de um atributo.

Rodar:  python -m unittest tests.test_grupos_fase1 -v
"""
from __future__ import annotations

import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix="tabulador_grupos_f1_")
os.environ["TABULADOR_OUTPUT"] = _TMP  # nuvem desligada; nada vai para a pasta real
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codeframe as CF  # noqa: E402
import config  # noqa: E402
import grupos_frame  # noqa: E402
import variables as V  # noqa: E402


class Projeto:
    PERGUNTAS = [
        {"id": "Q32", "tipo": "aberta", "codificar": True, "rotulo": "Provavelmente vai trocar"},
        {"id": "Q33", "tipo": "aberta", "codificar": True, "rotulo": "Certamente vai trocar"},
    ]
    GRUPOS = {"motivo_troca": {"rotulo": "Motivo para trocar", "perguntas": ["Q32", "Q33"], "instrucoes_frame": ""}}


def resposta(rid, origem, n=1, texto=None):
    return {"rid": rid, "origem_qid": origem, "n": n, "texto": texto or f"resposta {rid}", "nsnr": False}


def cat(codigo, nome, definicao="x"):
    return {"codigo": codigo, "nome": nome, "definicao": definicao, "exemplos": [], "keywords": [], "fixa": False}


class Base(unittest.TestCase):
    def setUp(self):
        V.ativar(Projeto())
        self.dir = Path(tempfile.mkdtemp(prefix="g1_"))
        for alvo, valor in (("OUTPUT_DIR", self.dir), ("PERGUNTAS_OUT", self.dir / "perguntas")):
            p = patch.object(config, alvo, valor)
            p.start()
            self.addCleanup(p.stop)

    def quadro_do_grupo(self, status="rascunho"):
        f = {"grupo": "motivo_troca", "status": status, "historico": [], "versao": 1,
             "categorias": [cat(1, "Preço"), cat(2, "Mensalidade"), cat(3, "Distância")] + [dict(c) for c in CF.FIXAS]}
        grupos_frame._gravar_grupo("motivo_troca", "frame.json", f)
        return f

    def classificar(self, qid, primarias):
        itens = [{"rid": i + 1, "primaria": p, "secundaria": None, "origem": "ia", "validado": False} for i, p in enumerate(primarias)]
        CF._gravar(qid, "codificacao.json", {"status": "rascunho", "itens": itens})

    def primarias(self, qid):
        return [i["primaria"] for i in CF._ler(qid, "codificacao.json")["itens"]]


class TestAmostra(Base):
    def test_cabe_no_limite_le_tudo(self):
        dados = {"respostas": [resposta(1, "Q32"), resposta(2, "Q33")], "n_unicas": 2}
        escolhidas, cob = CF._amostra_inducao(dados)
        self.assertEqual(len(escolhidas), 2)
        self.assertFalse(cob["amostra"])
        self.assertEqual(cob["perguntas"], {"Q32": {"unicas": 1, "lidas": 1}, "Q33": {"unicas": 1, "lidas": 1}})

    def test_pergunta_pequena_nao_some_do_sorteio(self):
        with patch.object(config, "MAX_RESPOSTAS_INDUCAO", 100):
            grande = [resposta(i, "Q32") for i in range(1, 301)]
            pequena = [resposta(1000 + i, "Q33") for i in range(30)]
            dados = {"respostas": grande + pequena, "n_unicas": 330}
            escolhidas, cob = CF._amostra_inducao(dados)
        self.assertEqual(len(escolhidas), 100)
        self.assertTrue(cob["amostra"])
        self.assertGreaterEqual(cob["perguntas"]["Q33"]["lidas"], 25)  # cota = 100 // (2*2)
        self.assertEqual(sum(c["lidas"] for c in cob["perguntas"].values()), 100)

    def test_grupo_leva_todas_as_repetidas_ate_metade_do_limite(self):
        with patch.object(config, "MAX_RESPOSTAS_INDUCAO", 100):
            rep = [resposta(i, "Q32", n=5) for i in range(1, 21)]
            unicas = [resposta(100 + i, "Q33") for i in range(200)]
            escolhidas, _ = CF._amostra_inducao({"respostas": rep + unicas, "n_unicas": 220})
        self.assertTrue({r["rid"] for r in rep} <= {r["rid"] for r in escolhidas})

    def test_pergunta_sozinha_mantem_o_sorteio_antigo(self):
        with patch.object(config, "MAX_RESPOSTAS_INDUCAO", 50):
            resp = [resposta(i, None, n=2 if i <= 10 else 1) for i in range(1, 121)]
            for r in resp:
                r.pop("origem_qid")
            novo, _ = CF._amostra_inducao({"respostas": resp, "n_unicas": 120})
            rep = [r for r in resp if r["n"] > 1][:50]
            resto = [r for r in resp if r["n"] == 1]
            antigo = sorted(rep + random.Random(0).sample(resto, 50 - len(rep)), key=lambda r: r["rid"])
        self.assertEqual([r["rid"] for r in novo], [r["rid"] for r in antigo])


class TestEdicaoDoGrupo(Base):
    def test_quadro_vive_no_grupo_e_nao_na_pergunta(self):
        self.quadro_do_grupo()
        CF.adicionar("Q32", "Transporte")
        self.assertIn("Transporte", [c["nome"] for c in grupos_frame.frame("motivo_troca")["categorias"]])
        self.assertFalse((config.PERGUNTAS_OUT / "Q32" / "frame.json").exists())
        self.assertIn("Transporte", [c["nome"] for c in CF.frame("Q33")["categorias"]])  # a outra pergunta enxerga

    def test_mesclar_remapeia_as_duas_perguntas(self):
        self.quadro_do_grupo()
        self.classificar("Q32", [1, 2, 3, 2])
        self.classificar("Q33", [2, 2, 1])
        CF.fundir("Q32", 1, 2)  # 2 -> 1
        self.assertEqual(self.primarias("Q32"), [1, 1, 3, 1])
        self.assertEqual(self.primarias("Q33"), [1, 1, 1])
        self.assertNotIn(2, [c["codigo"] for c in CF.frame("Q33")["categorias"]])

    def test_remover_manda_para_outros_nas_duas(self):
        self.quadro_do_grupo()
        self.classificar("Q32", [3, 1])
        self.classificar("Q33", [3])
        CF.remover("Q33", 3)
        self.assertEqual(self.primarias("Q32"), [CF.CODIGO_OUTROS, 1])
        self.assertEqual(self.primarias("Q33"), [CF.CODIGO_OUTROS])

    def test_renomear_e_keywords(self):
        self.quadro_do_grupo()
        CF.renomear("Q32", 1, "Valor", "Preço percebido")
        CF.editar_keywords("Q33", 1, adicionar=["caro"])
        c = CF.frame("Q32")["categorias"][0]
        self.assertEqual((c["nome"], c["definicao"], c["keywords"]), ("Valor", "Preço percebido", ["caro"]))

    def test_sem_classificacao_a_edicao_volta_para_rascunho(self):
        self.quadro_do_grupo(status="aprovado")
        CF.adicionar("Q32", "Transporte")
        self.assertEqual(grupos_frame.frame("motivo_troca")["status"], "rascunho")

    def test_com_classificacao_em_qualquer_pergunta_a_edicao_mantem_aprovado(self):
        self.quadro_do_grupo(status="aprovado")
        self.classificar("Q33", [1])  # só a Q33 foi classificada; a edição é feita pela Q32
        CF.adicionar("Q32", "Transporte")
        self.assertEqual(grupos_frame.frame("motivo_troca")["status"], "aprovado")


class TestRefinoDoGrupo(Base):
    def test_refino_usa_respostas_das_duas_perguntas_e_guarda_avisos(self):
        self.quadro_do_grupo()
        grupos_frame._gravar_grupo("motivo_troca", "respostas.json", {
            "n_unicas": 2, "respostas": [resposta(1, "Q32", texto="muito caro"), resposta(2, "Q33", texto="longe de casa")]})
        vistos = {}

        def falso(system, user, schema, nome=""):
            vistos["user"], vistos["schema"] = user, schema
            return {"raciocinio": "ok", "avisos": ["Preço e Distância são atributos distintos: mantive separados."],
                    "categorias": [{"codigo_anterior": c, "incorpora": [], "nome": n, "definicao": "d", "exemplos": [], "keywords": []}
                                   for c, n in ((1, "Preço"), (2, "Mensalidade"), (3, "Distância"))]}

        with patch.object(CF.llm, "chamar_json", falso):
            f = CF.refinar("Q32", "junte Preço e Distância")
        self.assertIn("[Q32] muito caro", vistos["user"])
        self.assertIn("[Q33] longe de casa", vistos["user"])
        self.assertIn("GRUPO DE PERGUNTAS", vistos["user"])
        self.assertIn("avisos", vistos["schema"]["required"])
        self.assertEqual(f["avisos_ultimo_refino"], ["Preço e Distância são atributos distintos: mantive separados."])
        self.assertEqual([c["nome"] for c in grupos_frame.frame("motivo_troca")["categorias"][:3]], ["Preço", "Mensalidade", "Distância"])


class TestUmAtributo(unittest.TestCase):
    def test_avisa_nome_com_dois_atributos(self):
        f = {"categorias": [cat(1, "Preço e atendimento"), cat(2, "Segurança"), cat(3, "Estrutura / limpeza"), dict(CF.FIXAS[0])]}
        self.assertEqual([a["codigo"] for a in CF.avisos_atributo(f)], [1, 3])

    def test_sem_quadro_nao_explode(self):
        self.assertEqual(CF.avisos_atributo(None), [])


if __name__ == "__main__":
    unittest.main()
