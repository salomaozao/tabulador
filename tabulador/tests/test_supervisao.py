"""Supervisão (PEND-05): auditoria por outra IA, aceite automático, desfazer, quem conferiu,
perfil de quem citou cada categoria e o rótulo 'auditoria' no consumo. Sem IA de verdade.

Rodar:  python -m unittest tests.test_supervisao -v
Escreve numa pasta temporária (TABULADOR_OUTPUT), nunca em SESI_cat/output.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="tabulador_supervisao_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import config  # noqa: E402
import llm  # noqa: E402
import load  # noqa: E402
import perfil  # noqa: E402
import projetos  # noqa: E402
import supervisao as SUP  # noqa: E402
import usage  # noqa: E402

from tests.test_sesi import _llm_fake  # noqa: E402

QID = "Q33"


def _fake(system: str, user: str, schema: dict) -> dict:
    """Auditor falso: concorda com rid par, discorda (sugere Mudança=2) do ímpar."""
    if "auditoria" in schema["properties"]:
        saida = []
        for m in re.finditer(r"rid (\d+): .*?-> primária (\d+)", user):
            rid, prim = int(m.group(1)), int(m.group(2))
            if rid % 2 == 0 or prim == 2:
                saida.append({"rid": rid, "ok": True, "primaria": None, "secundaria": None, "nota": ""})
            else:
                saida.append({"rid": rid, "ok": False, "primaria": 2, "secundaria": None, "nota": "fala de mudança"})
        return {"auditoria": saida}
    return _llm_fake(system, user, schema)


@unittest.skipUnless(projetos.pasta("sesi").joinpath("data", "base_processamento.xlsx").exists(), "planilha SESI não disponível")
class TestSupervisao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env_antes = os.environ.get("TABULADOR_OUTPUT")
        os.environ["TABULADOR_OUTPUT"] = _TMP
        projetos.ativar("sesi")
        llm.set_cliente(_fake)
        load.executar(verbose=False)
        CF.preparar(QID)
        CF.induzir(QID, forcar=True)
        CF.aprovar(QID)
        CD.codificar(QID)

    @classmethod
    def tearDownClass(cls):
        llm.set_cliente(None)
        if cls._env_antes is None:
            os.environ.pop("TABULADOR_OUTPUT", None)
        else:
            os.environ["TABULADOR_OUTPUT"] = cls._env_antes

    def setUp(self):
        os.environ["TABULADOR_OUTPUT"] = _TMP
        projetos.ativar("sesi")
        llm.set_cliente(_fake)

    def test_1_sem_auditoria_nada_e_aceito(self):
        SUP.desfazer_auto(QID)
        r = SUP.auto_aceitar(QID, 0.85)
        self.assertEqual(r["aceitas"], 0)
        self.assertGreater(r["ficaram"].get("ainda sem auditoria", 0), 0)

    def test_2_auditar_e_aceitar(self):
        a = SUP.auditar(QID)
        self.assertGreater(a["auditadas"], 0)
        self.assertEqual(a["auditadas"], a["concorda"] + a["discorda"])
        itens = CD.codificacao(QID)["itens"]
        disc = [i for i in itens if (i.get("auditoria") or {}).get("ok") is False]
        self.assertTrue(all(i["auditoria"]["primaria"] == 2 and i["auditoria"]["nota"] for i in disc))
        # aceite: confiança >= limiar, não é Outros e o auditor concordou
        esperadas = [i for i in itens if not i.get("validado") and i.get("origem") != "humano" and i["primaria"] != CF.CODIGO_OUTROS
                     and (i.get("confianca") or 0) >= 0.85 and (i.get("auditoria") or {}).get("ok") is True]
        r = SUP.auto_aceitar(QID, 0.85)
        self.assertEqual(r["aceitas"], len(esperadas))
        res = CD.resumo_revisao(QID)
        self.assertEqual(res["n_confirmadas_auto"], len(esperadas))
        conf = SUP.conferencia(CD.codificacao(QID)["itens"])
        self.assertEqual(conf.get("confirmadas_auto", 0), len(esperadas))
        # auditar de novo não repete quem já foi auditado
        self.assertEqual(SUP.auditar(QID)["auditadas"], 0)
        # desfazer volta tudo, mas mantém a auditoria
        self.assertEqual(SUP.desfazer_auto(QID), len(esperadas))
        itens = CD.codificacao(QID)["itens"]
        self.assertFalse(any(i.get("validado_por") == SUP.AUTO for i in itens))
        self.assertTrue(any(i.get("auditoria") for i in itens))

    def test_3_confirmacao_humana_marca_quem(self):
        item = next(i for i in CD.codificacao(QID)["itens"] if not i.get("validado") and i.get("origem") == "llm")
        CD.atualizar_item(QID, item["rid"], validado=True)
        it = next(i for i in CD.codificacao(QID)["itens"] if i["rid"] == item["rid"])
        self.assertEqual(it["validado_por"], "humano")
        CD.atualizar_item(QID, item["rid"], validado=False)
        it = next(i for i in CD.codificacao(QID)["itens"] if i["rid"] == item["rid"])
        self.assertNotIn("validado_por", it)
        outro = [i["rid"] for i in CD.codificacao(QID)["itens"] if not i.get("validado") and i.get("origem") == "llm"][:2]
        CD.validar(QID, outro)
        self.assertTrue(all(i.get("validado_por") == "humano" for i in CD.codificacao(QID)["itens"] if i["rid"] in outro))

    def test_4_sugestao_adotada_conta(self):
        SUP.auditar(QID, escopo="todas")
        alvo = next((i for i in CD.codificacao(QID)["itens"] if (i.get("auditoria") or {}).get("ok") is False
                     and not i.get("validado") and i.get("origem") != "humano"), None)
        if alvo is None:
            self.skipTest("nenhuma discordância nesta base")
        antes = SUP.conferencia(CD.codificacao(QID)["itens"]).get("sugestoes_adotadas", 0)
        CD.atualizar_item(QID, alvo["rid"], primaria=alvo["auditoria"]["primaria"])
        depois = SUP.conferencia(CD.codificacao(QID)["itens"])
        self.assertEqual(depois["sugestoes_adotadas"], antes + 1)

    def test_5_perfil_bate_com_a_base(self):
        P = perfil.perfil(QID)
        self.assertTrue(P["classificada"])
        df, _ = load.carregar_base()
        resp = CF.respostas(QID)["respostas"]
        ids_base = [i for r in resp for i in r["respondent_ids"]]
        nota = pd.to_numeric(df.set_index("respondent_id").loc[ids_base, "Q3"], errors="coerce").dropna()
        self.assertEqual(P["base"]["n"], len(ids_base))
        self.assertAlmostEqual(P["base"]["nps"]["media"], round(float(nota.mean()), 2))
        # uma categoria: conta à mão quem citou (primária ou secundária)
        c = max(P["categorias"], key=lambda c: c.get("n", 0))
        por_rid = {r["rid"]: r for r in resp}
        ids = {rid for i in CD.codificacao(QID)["itens"] if c["codigo"] in (i.get("primaria"), i.get("secundaria"))
               for rid in por_rid[i["rid"]]["respondent_ids"]}
        self.assertEqual(c["n"], len(ids))
        nota_c = pd.to_numeric(df.set_index("respondent_id").loc[sorted(ids), "Q3"], errors="coerce").dropna()
        self.assertAlmostEqual(c["perfil"]["nps"]["media"], round(float(nota_c.mean()), 2))
        # pendentes da confirmação em bloco nunca incluem discordâncias do auditor
        itens = {i["rid"]: i for i in CD.codificacao(QID)["itens"]}
        for cat in P["categorias"]:
            self.assertFalse(any((itens[r].get("auditoria") or {}).get("ok") is False for r in cat["pendentes"]))

    def test_6_consumo_e_troca_de_provedor(self):
        self.assertEqual(usage._operacao("audit_Q4_3"), ("auditoria", "Q4"))
        antes = (config.OPENAI_PROVEDOR, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_API_KEY)
        with llm.usando("simulado", "simulado"):
            self.assertEqual(config.OPENAI_PROVEDOR, "simulado")
        self.assertEqual((config.OPENAI_PROVEDOR, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_API_KEY), antes)
        with self.assertRaises(ValueError):
            with llm.usando("nao_existe"):
                pass


if __name__ == "__main__":
    unittest.main()
