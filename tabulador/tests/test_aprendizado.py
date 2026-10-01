"""Loop de aprendizado do quadro (src/aprendizado.py) e coluna de palavras-chave (codeframe).
Sem IA, sem nuvem e sem planilha: frame, respostas e classificação entram por dicionário, e os
arquivos vão para uma pasta temporária.

Rodar:  python -m unittest tests.test_aprendizado -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="tabulador_aprendizado_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aprendizado as A  # noqa: E402
import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import nuvem  # noqa: E402

QID = "QX"


def _frame() -> dict:
    return {"pergunta": QID, "status": "aprovado", "fixo": False, "versao": 1, "historico": [],
            "categorias": [
                {"codigo": 1, "nome": "Professores", "definicao": "fala dos professores", "exemplos": ["bons professores"], "keywords": ["professor"], "fixa": False},
                {"codigo": 2, "nome": "Estrutura", "definicao": "prédio, salas, quadra", "exemplos": ["quadra"], "fixa": False},
                {"codigo": 3, "nome": "Preço", "definicao": "mensalidade, valor", "exemplos": [], "fixa": False},
                *[dict(f) for f in CF.FIXAS]]}


def _base():
    """12 respostas: professores (1-5), estrutura (6-9), preço (10-11), uma em Outros (12)."""
    textos = {1: "os professores são ótimos", 2: "professores muito dedicados", 3: "ótimos professores e coordenação",
              4: "professores atenciosos", 5: "a didática dos professores", 6: "a quadra está velha", 7: "salas quentes, sem ar",
              8: "quadra coberta faz falta", 9: "banheiros sujos", 10: "mensalidade cara", 11: "o valor da mensalidade subiu",
              12: "gostaria de mais passeios"}
    respostas = [{"rid": r, "texto": t, "n": 1 + (r == 1), "chave": t, "nsnr": False, "respondent_ids": [r]} for r, t in textos.items()]
    humano = lambda rid, prim, **kw: {"rid": rid, "primaria": prim, "secundaria": None, "confianca": 1.0, "origem": "humano", **kw}
    conf = lambda rid, prim, por="humano": {"rid": rid, "primaria": prim, "secundaria": None, "confianca": 0.9, "origem": "llm",
                                            "validado": True, "validado_por": por}
    itens = [conf(1, 1), conf(2, 1), conf(3, 1), humano(4, 1, corrigido_de=2), humano(5, 1, corrigido_de=2),
             conf(6, 2), conf(7, 2), conf(8, 2, por="auto"), humano(9, 2),
             conf(10, 3), humano(11, 3, corrigido_de=97),
             {"rid": 12, "primaria": 97, "secundaria": None, "confianca": 0.4, "origem": "llm",
              "auditoria": {"ok": False, "primaria": 2, "nota": "passeio é estrutura?"}}]
    return respostas, itens


class TestDossie(unittest.TestCase):
    def setUp(self):
        self.frame = _frame()
        self.respostas, self.itens = _base()
        self.d = A.dossie_de(self.frame, self.respostas, self.itens)

    def test_conferido_por_humano_nao_conta_auto(self):
        self.assertTrue(A.conferido_por_humano(self.itens[0]))
        self.assertTrue(A.conferido_por_humano(self.itens[3]))
        self.assertFalse(A.conferido_por_humano(self.itens[7]))  # aceite automático
        self.assertFalse(A.conferido_por_humano(self.itens[11]))  # só IA

    def test_volume_e_matriz_de_confusao(self):
        self.assertEqual(self.d[1]["n"], 5)
        self.assertEqual(self.d[1]["n_humano"], 5)
        self.assertEqual(self.d[2]["n_humano"], 3)  # o auto-aceito (rid 8) não conta
        self.assertEqual(self.d[1]["confusoes_entrada"], {2: 2})
        self.assertEqual(self.d[2]["confusoes_saida"], {1: 2})
        self.assertEqual(self.d[97]["confusoes_saida"], {3: 1})

    def test_auditor_e_confianca(self):
        self.assertEqual(self.d[97]["n_auditor_discorda"], 1)
        self.assertEqual(self.d[97]["sugestoes_auditor"], {2: 1})
        self.assertEqual(self.d[97]["conf_media"], 0.4)
        self.assertEqual(self.d[97]["pct_conf_baixa"], 1.0)

    def test_ancoras_so_de_humano_e_limites(self):
        todas = [t for e in self.d.values() for t in e["ancoras"]]
        self.assertNotIn("quadra coberta faz falta", todas)  # auto-aceito nunca vira exemplo
        self.assertEqual(self.d[1]["ancoras"][0], "os professores são ótimos")  # a mais frequente primeiro
        self.assertLessEqual(len(self.d[1]["ancoras"]), 3)
        self.assertEqual({l["de"] for l in self.d[1]["limites"]}, {2})
        self.assertEqual(self.d[1]["limites"][0]["de_nome"], "Estrutura")

    def test_keywords_sugeridas_distinguem_a_categoria(self):
        kws = A.keywords_sugeridas_de(self.frame, self.respostas, self.itens)
        self.assertIn("professores", kws[1])
        self.assertNotIn("professores", kws.get(2, []))
        self.assertNotIn(97, kws)  # categorias fixas não ganham keyword

    def test_prompt_leva_ancoras_limites_e_keywords(self):
        ens = A.ensino_de(self.frame, self.respostas, self.itens)
        bloco = A.bloco_categorias(self.frame, ens)
        linhas = bloco.splitlines()
        self.assertTrue(linhas[0].startswith("  1: Professores - fala dos professores [termos típicos, só como pista: professor]"))
        self.assertIn("(ex.: os professores são ótimos;", linhas[0])  # âncora humana no lugar do exemplo da indução
        self.assertIn('caso já corrigido: "', bloco)
        self.assertIn("-> é 1, não 2 (Estrutura)", bloco)
        self.assertNotIn("quadra coberta faz falta", bloco)
        # o modo teste (simulador) continua lendo o frame do prompt
        import simulador
        cats = simulador._frame_prompt(bloco)
        self.assertEqual([c["codigo"] for c in cats], [1, 2, 3, 97, 98])
        self.assertEqual(cats[0]["nome"], "Professores")

    def test_prompt_sem_revisao_usa_exemplos_da_inducao(self):
        bloco = A.bloco_categorias(self.frame, {})
        self.assertIn("  2: Estrutura - prédio, salas, quadra (ex.: quadra)", bloco)
        self.assertNotIn("caso já corrigido", bloco)

    def test_prompt_de_classificacao_usa_o_bloco(self):
        with mock.patch.object(CF, "instrucoes_completas", return_value=""):
            _, user = CD._prompt(QID, self.frame, "Pergunta?", [{"rid": 1, "texto": "x"}], A.ensino_de(self.frame, self.respostas, self.itens))
        self.assertIn("caso já corrigido", user)
        self.assertIn('rid 1: "x"', user)

    def test_saude(self):
        tipos = {a["tipo"] for a in A.saude_de(self.frame, self.d)}
        self.assertIn("outros", tipos)  # 1 de 12 = 8% > 5%
        self.assertNotIn("confusao", tipos)  # 2 correções ficam abaixo do mínimo (5)... mas é 100% das saídas de 2
        with mock.patch.object(A, "_limiar", side_effect=lambda n: {"SAUDE_CONFUSAO_MIN": 2}.get(n, getattr(A.config, n))):
            alertas = A.saude_de(self.frame, self.d)
        conf = [a for a in alertas if a["tipo"] == "confusao" and a["codigo"] == 2]
        self.assertEqual(conf[0]["par"], 1)

    def test_saude_keyword_compartilhada(self):
        f = _frame()
        f["categorias"][1]["keywords_auto"] = ["Professor"]
        alertas = A.saude_de(f, self.d)
        self.assertTrue(any(a["tipo"] == "keyword_compartilhada" for a in alertas))

    def test_keywords_ativas_respeita_bloqueadas(self):
        c = {"keywords": ["professor", "Aula"], "keywords_auto": ["aula", "didática"], "keywords_bloqueadas": ["didatica"]}
        self.assertEqual(A.keywords_ativas(c), ["professor", "Aula"])


class TestArquivos(unittest.TestCase):
    """Edição de keywords, histórico com antes/depois, versão do frame e o aprendizado gravado."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="perg_", dir=_TMP))

        def pasta(qid):
            p = self.dir / qid
            p.mkdir(parents=True, exist_ok=True)
            return p
        for obj, nome, novo in ((CF, "pasta", pasta), (nuvem, "ativa", lambda: False)):
            p = mock.patch.object(obj, nome, novo)
            p.start()
            self.addCleanup(p.stop)
        respostas, itens = _base()
        CF._gravar(QID, "frame.json", _frame())
        CF._gravar(QID, "respostas.json", {"pergunta": QID, "respostas": respostas})
        CF._gravar(QID, "codificacao.json", {"pergunta": QID, "status": "rascunho", "itens": itens})

    def test_renomear_guarda_antes_e_depois_e_sobe_versao(self):
        f = CF.renomear(QID, 2, "Estrutura", "prédio e salas de aula", por="Sara")
        h = f["historico"][-1]
        self.assertEqual(h["acao"], "definir")
        self.assertEqual((h["definicao_de"], h["definicao_para"]), ("prédio, salas, quadra", "prédio e salas de aula"))
        self.assertEqual(h["por"], "Sara")
        self.assertEqual(f["versao"], 2)
        self.assertEqual(CF._cat(f, 2)["atualizado_por"], "humano:Sara")
        # sem mudança nada é registrado
        self.assertEqual(len(CF.renomear(QID, 2, "Estrutura")["historico"]), 1)

    def test_editar_keywords(self):
        f = CF.editar_keywords(QID, 1, adicionar=["Didática", "didatica", " professor "])
        self.assertEqual(CF._cat(f, 1)["keywords"], ["professor", "didática"])
        CF._gravar(QID, "frame.json", dict(f, categorias=[dict(c, keywords_auto=["coordenação", "aula"]) if c["codigo"] == 1 else c for c in f["categorias"]]))
        f = CF.editar_keywords(QID, 1, fixar=["coordenacao"], remover=["aula", "professor"])
        c = CF._cat(f, 1)
        self.assertEqual(c["keywords"], ["didática", "coordenação"])
        self.assertEqual(c["keywords_auto"], [])
        self.assertEqual(c["keywords_bloqueadas"], ["aula", "professor"])
        self.assertEqual(f["historico"][-1]["acao"], "keywords")
        # adicionar de novo tira do bloqueio
        c = CF._cat(CF.editar_keywords(QID, 1, adicionar=["aula"]), 1)
        self.assertEqual(c["keywords_bloqueadas"], ["professor"])

    def test_frame_antigo_sem_keywords_continua_valendo(self):
        f = CF.frame(QID)
        self.assertNotIn("keywords", CF._cat(f, 3))
        self.assertIn("  3: Preço - mensalidade, valor", A.bloco_categorias(f))
        self.assertIn("Preço", CF.texto_frame(QID))

    def test_aprender_grava_keywords_de_humano_e_respeita_bloqueio(self):
        with mock.patch.object(A, "_limiar", side_effect=lambda n: getattr(A.config, n)):
            r = A.aprender(QID)  # 10 conferidas < 25: ainda não
            self.assertFalse(r["rodou"])
            CF.editar_keywords(QID, 1, remover=["ótimos"])
            r = A.aprender(QID, forcar=True)
        self.assertTrue(r["rodou"])
        f = CF.frame(QID)
        c1 = CF._cat(f, 1)
        self.assertIn("professores", c1["keywords_auto"])
        self.assertNotIn("ótimos", c1["keywords_auto"])
        self.assertEqual(c1["atualizado_por"], "auto")
        self.assertEqual(f["historico"][-1]["acao"], "aprendizado_auto")
        self.assertEqual(f["aprendizado"]["n_conferidas"], 10)
        self.assertGreater(f["versao"], 1)

    def test_revisado_por_e_frame_versao(self):
        item = CD.atualizar_item(QID, 12, primaria=2, por="João")
        self.assertEqual(item["revisado_por"], "João")
        self.assertEqual(item["corrigido_de"], 97)
        self.assertEqual(CD.validar(QID, [10], False, por="João"), 1)
        self.assertEqual(CD.validar(QID, [10], True, por="Sara"), 1)
        it = next(i for i in CD.codificacao(QID)["itens"] if i["rid"] == 10)
        self.assertEqual(it["revisado_por"], "Sara")

    def test_refinar_preserva_o_que_a_revisao_ensinou(self):
        CF.editar_keywords(QID, 1, adicionar=["didática"], remover=["chato"])
        saida = {"raciocinio": "ok", "categorias": [
            {"codigo_anterior": 1, "incorpora": [], "nome": "Professores", "definicao": "professores", "exemplos": [], "keywords": ["chato", "aula"]},
            {"codigo_anterior": 2, "incorpora": [3], "nome": "Estrutura e preço", "definicao": "x", "exemplos": [], "keywords": []},
            {"codigo_anterior": None, "incorpora": [], "nome": "Passeios", "definicao": "passeios", "exemplos": [], "keywords": ["passeio"]}]}
        with mock.patch.object(CF, "respostas", return_value={"respostas": [], "n_unicas": 0}), \
             mock.patch.object(CF.V, "por_id", return_value={"rotulo": "Q"}), \
             mock.patch.object(CF, "instrucoes_completas", return_value=""), \
             mock.patch.object(CF.llm, "chamar_json", return_value=saida):
            f = CF.refinar(QID, "junte estrutura e preço, crie passeios")
        c1 = CF._cat(f, 1)
        self.assertEqual(c1["keywords"], ["professor", "didática", "aula"])  # 'chato' bloqueado não volta
        self.assertEqual(CF._cat(f, 4)["keywords"], ["passeio"])
        self.assertEqual(f["historico"][-1]["acao"], "refinar_ia")


if __name__ == "__main__":
    unittest.main()
