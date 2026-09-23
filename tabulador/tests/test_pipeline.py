"""Testes do pipeline (sem chamar a OpenAI: o LLM é substituído por uma função determinística).

Rodar:  python -m unittest -v          (ou: python -m pytest tests -q)
Os testes escrevem em uma pasta temporária (ASSERTIVA_OUTPUT), nunca em output/.
Precisam da planilha-fonte (somente leitura) em config.FONTE_XLSX.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="assertiva_test_")
os.environ["ASSERTIVA_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import backcoding  # noqa: E402
import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import config  # noqa: E402
import crosstabs  # noqa: E402
import llm  # noqa: E402
import load  # noqa: E402
import projetos  # noqa: E402
import variables as V  # noqa: E402

projetos.ativar("assertiva")


def _llm_fake(system: str, user: str, schema: dict) -> dict:
    """Frame: 3 categorias fixas. Codificação: primária por palavra-chave; secundária quando há 'e'."""
    if "categorias" in schema["properties"]:
        return {"raciocinio": "fake", "categorias": [
            {"nome": "Confiança", "definicao": "cita confiança", "exemplos": ["Confiança"]},
            {"nome": "Preço", "definicao": "cita preço/custo", "exemplos": ["preço alto"]},
            {"nome": "Conhece pouco", "definicao": "não conhece bem", "exemplos": ["Conheco pouco"]},
        ]}
    import re
    saida = []
    for m in re.finditer(r'rid (\d+): "(.*?)"\n', user + "\n"):
        rid, texto = int(m.group(1)), m.group(2).lower()
        # códigos válidos vêm do frame impresso no prompt; usa 1..4 (back-coding) ou 1..3 (fake)
        if "CODE FRAME" in user and "Sócio(a)/Diretoria" in user:
            prim = 1 if "propriet" in texto or "mei" == texto else 4
        elif "Serviços financeiros" in user:
            prim = 1
        elif "confi" in texto:
            prim = 1
        elif "pre" in texto or "cust" in texto:
            prim = 2
        elif "conhe" in texto:
            prim = 3
        else:
            prim = 97
        sec = 2 if (prim == 1 and " e " in texto) else None
        saida.append({"rid": rid, "primaria": prim, "secundaria": sec, "confianca": 0.9 if prim != 97 else 0.4, "justificativa": "fake"})
    return {"codificacoes": saida}


@unittest.skipUnless(config.FONTE_XLSX.exists(), "planilha-fonte não disponível")
class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        projetos.ativar("assertiva")
        llm.set_cliente(_llm_fake)
        cls.df, cls.registro = load.executar(verbose=False)

    def setUp(self):
        projetos.ativar("assertiva")

    @classmethod
    def tearDownClass(cls):
        llm.set_cliente(None)

    # ---- 1. load ---------------------------------------------------------------------
    def test_load_cabecalho_duplo_e_fontes(self):
        df = self.df
        self.assertIn("Q02_CARGO", df.columns)
        self.assertIn("Q34_AVAL_ATRIBUTOS__CONFIABILIDADE", df.columns)
        self.assertEqual(set(df["fonte"]), {"autopreenchido", "telefone"})
        self.assertEqual(df["respondent_id"].nunique(), len(df))
        # rótulos das duas abas convergem (sufixos '(Microempresa)' etc. removidos)
        self.assertTrue(set(df["Q05_PORTE"].dropna()) <= set(V.por_id("Q05_PORTE")["niveis"]))
        self.assertTrue(set(df["Q04_SEGMENTO"].dropna()).isdisjoint({"Outro"}))  # virou 'Outro. Qual?'

    def test_load_pii_expurgada(self):
        cols = " ".join(self.df.columns).lower()
        for pii in ("ip_address", "email", "first_name", "last_name", "whatsapp", "whatsap", "nome_completo", "nome completo"):
            self.assertNotIn(pii, cols)
        # também não pode sobreviver na base salva em disco
        salvo = (config.BASE_OUT / "base.json").read_text(encoding="utf-8").lower()
        for pii in ("ip_address", "email_address", "first_name", "last_name"):
            self.assertNotIn(pii, salvo)

    def test_load_multiplas_binarias(self):
        df = self.df
        itens = [c for c in df.columns if c.startswith("Q24_FONTES__")]
        self.assertGreater(len(itens), 5)
        for c in itens:
            self.assertTrue(set(df[c].dropna().unique()) <= {0, 1}, c)
        # Q31 tem base 'conhece_assertiva': fora da base fica NaN, dentro 0/1
        conhece = V.FILTROS["conhece_assertiva"](df)
        self.assertTrue(df.loc[~conhece, "Q31_ASSOCIACOES__INOVACAO"].isna().all())
        self.assertTrue(df.loc[conhece, "Q31_ASSOCIACOES__INOVACAO"].notna().all())

    def test_load_bases_e_derivadas(self):
        df = self.df
        self.assertEqual(df["Q32_NPS"].notna().sum(), V.FILTROS["conhece_assertiva"](df).sum())
        self.assertEqual(df["PORTE3"].isna().sum(), 0)
        self.assertEqual((df["NPS_GRUPO"] == "Promotores (9-10)").sum(), df["Q32_NPS"].between(9, 10).sum())
        self.assertEqual((df["USA_IA2"] == "Sim").sum(), df["Q09_USA_IA"].str.startswith("Usamos IA").sum())
        # TOM por telefone: 'Outra. Qual?' foi fundido com o texto
        self.assertFalse(df["Q22_TOM"].fillna("").str.startswith("Outra").any())

    # ---- 2. back-coding --------------------------------------------------------------
    def test_backcoding_fecha_banners(self):
        backcoding.rodar()
        backcoding.aplicar()
        df, _ = load.carregar_base()
        self.assertEqual((df["CARGO4"] == "Outro").sum(), 0)
        self.assertEqual(df["CARGO4"].isna().sum(), 0)
        self.assertEqual((df["SEGMENTO4"] == "Outro").sum(), 0)
        self.assertEqual(df["SEGMENTO4"].isna().sum(), 0)
        # quem respondeu 'Sócio(a) e/ou Diretor(a)' continua Diretoria
        self.assertTrue((df.loc[df["Q02_CARGO"].eq("Sócio(a) e/ou Diretor(a)"), "CARGO4"] == "Diretoria").all())

    # ---- 3. code frame + codificação --------------------------------------------------
    def test_codeframe_e_codificacao(self):
        qid = "Q33_MOTIVO_NPS"
        dados = CF.preparar(qid)
        self.assertEqual(dados["n_respondeu"], int(self.df[qid].notna().sum()))
        self.assertTrue(any(r["nsnr"] for r in dados["respostas"]))  # 'Não sei' detectado por regra
        f = CF.induzir(qid)
        self.assertEqual(f["status"], "rascunho")
        codigos = [c["codigo"] for c in f["categorias"]]
        self.assertEqual(codigos, [1, 2, 3, CF.CODIGO_OUTROS, CF.CODIGO_NSNR])
        with self.assertRaises(RuntimeError):
            CD.codificar(qid)  # frame não aprovado
        CF.aprovar(qid)
        cod = CD.codificar(qid)
        self.assertEqual(len(cod["itens"]), dados["n_unicas"])
        t = CD.tabela(qid)
        self.assertTrue(t.loc[t["nsnr_regra"], "primaria"].eq(CF.CODIGO_NSNR).all())
        self.assertTrue(t["primaria"].isin(codigos).all())
        self.assertTrue((t["secundaria"].dropna() != t.loc[t["secundaria"].notna(), "primaria"]).all())
        # fundir 2 -> 1 remapeia a codificação; com a classificação já iniciada, o frame segue aprovado
        CF.fundir(qid, 1, 2)
        t2 = CD.tabela(qid)
        self.assertFalse(t2["primaria"].eq(2).any())
        self.assertEqual(CF.frame(qid)["status"], "aprovado")
        # revisão humana via xlsx
        p = CD.exportar_revisao(qid)
        rev = pd.read_excel(p, sheet_name="revisao")
        rev = rev.astype({"REVISAO_PRIMARIA": object, "REVISAO_SECUNDARIA": object, "COMENTARIO": object})
        rid0 = int(rev.iloc[0]["rid"])
        rev.loc[0, "REVISAO_PRIMARIA"] = "Conhece pouco"
        rev.loc[0, "COMENTARIO"] = "teste"
        with pd.ExcelWriter(p, engine="openpyxl") as xw:
            rev.to_excel(xw, sheet_name="revisao", index=False)
        cod = CD.importar_revisao(qid)
        self.assertEqual(cod["_alteracoes"], 1)
        item = next(i for i in cod["itens"] if i["rid"] == rid0)
        self.assertEqual(item["primaria"], 3)
        self.assertEqual(item["origem"], "humano")
        CD.aprovar(qid)
        CD.aplicar_na_base()
        df, reg = load.carregar_base()
        self.assertIn(f"{qid}_COD1", df.columns)
        self.assertEqual(df[f"{qid}_COD1"].notna().sum(), dados["n_respondeu"])

    # ---- 4. cruzamentos ------------------------------------------------------------------
    def test_crosstabs_percentuais(self):
        df, reg = load.carregar_base()
        banners = ["PORTE3", "PUBLICO"]
        t = crosstabs.tabular(df, {"qid": "Q05_PORTE", "var": "Q05_PORTE", "tipo": "unica", "base": "todos"}, banners)
        self.assertEqual(t["base"][0], len(df))
        for j in range(len(t["colunas"])):
            self.assertAlmostEqual(sum(l[j] for l in t["pct"]), 1.0, places=6)
        itens = [(v, e["opcao"]) for v, e in reg.items() if e.get("pergunta") == "Q24_FONTES" and e["tipo"] == "dicotomica"]
        m = crosstabs.tabular(df, {"qid": "Q24_FONTES", "tipo": "multipla", "itens": itens, "base": "todos"}, banners)
        self.assertGreater(sum(l[0] for l in m["pct"]), 1.0)  # múltipla pode passar de 100%
        self.assertTrue(all(0 <= v <= 1 for l in m["pct"] for v in l))
        # base de pergunta filtrada respeita o filtro
        n = crosstabs.tabular(df, {"qid": "Q32_NPS", "var": "Q32_NPS", "tipo": "numerica", "base": "conhece_assertiva"}, banners)
        self.assertEqual(n["base"][0], int(df["Q32_NPS"].notna().sum()))
        p = crosstabs.gerar(verbose=False)
        self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main()
