"""Modo teste (IA simulada): fluxo completo sem rede e pasta de resultados separada.

Rodar:  python -m unittest discover -s tests -v
Não grava no .env real nem nas pastas de resultados reais.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="tabulador_modoteste_")
os.environ["TABULADOR_OUTPUT"] = _TMP
os.environ["TABULADOR_SIMULADO_ATRASO"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import config  # noqa: E402
import llm  # noqa: E402
import load  # noqa: E402
import projetos  # noqa: E402
import simulador  # noqa: E402
import usage  # noqa: E402

VARS = ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_PROVEDOR", "TABULADOR_ANTES_TESTE_PROVEDOR",
        "TABULADOR_ANTES_TESTE_MODELO", "TABULADOR_ANTES_TESTE_URL"] + [f"TABULADOR_CHAVE_{p.upper()}" for p in config.PROVEDORES]


@unittest.skipUnless(projetos.pasta("sesi").joinpath("data", "base_processamento.xlsx").exists(), "planilha SESI não disponível")
class TestModoTeste(unittest.TestCase):
    def setUp(self):
        llm.set_cliente(None)
        self._env = {k: os.environ.get(k) for k in VARS}
        self._cfg = (config.ENV_FILE, config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR)
        config.ENV_FILE = Path(tempfile.mkdtemp()) / ".env"
        for k in VARS:
            os.environ.pop(k, None)
        config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR = "sk-real", "gpt-4.1", None, "openai"
        projetos.ativar("sesi")
        if not (config.BASE_OUT / "base.json").exists():
            load.executar(verbose=False)  # base "real" (na pasta temporária)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config.ENV_FILE, config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR = self._cfg
        projetos.ativar("sesi")

    def test_liga_desliga_e_pasta_separada(self):
        real = config.OUTPUT_DIR
        config.alternar_modo_teste(True)
        projetos.ativar("sesi")
        self.assertTrue(config.modo_teste())
        self.assertEqual(config.OUTPUT_DIR, real.parent / (real.name + "_teste"))
        self.assertTrue((config.BASE_OUT / "base.json").exists())  # base copiada
        config.alternar_modo_teste(False)
        projetos.ativar("sesi")
        self.assertFalse(config.modo_teste())
        self.assertEqual((config.OPENAI_PROVEDOR, config.OPENAI_MODEL, config.OPENAI_API_KEY), ("openai", "gpt-4.1", "sk-real"))
        self.assertEqual(config.OUTPUT_DIR, real)

    def test_fluxo_completo_simulado(self):
        config.alternar_modo_teste(True)
        projetos.ativar("sesi")
        qid = "Q33"
        dados = CF.preparar(qid)
        f = CF.induzir(qid, forcar=True)
        nomes = [c["nome"] for c in f["categorias"] if not c.get("fixa")]
        self.assertGreaterEqual(len(nomes), 3)
        self.assertIn("MODO TESTE", f["raciocinio"])
        # ajuste de categorias: junta as duas primeiras e cria uma nova
        f2 = CF.refinar(qid, f"junte {nomes[0]} e {nomes[1]}; crie 'Transporte escolar'")
        nomes2 = [c["nome"] for c in f2["categorias"]]
        self.assertIn("Transporte escolar", nomes2)
        self.assertEqual(len([c for c in f2["categorias"] if not c.get("fixa")]), len(nomes))  # -1 fundida +1 nova
        CF.aprovar(qid)
        CD.codificar(qid, limite=20)
        res = CD.resumo_revisao(qid)
        self.assertGreater(res["n_codificadas"], 0)
        self.assertGreater(res["n_faltantes"], 0)
        # comentário citando uma categoria é obedecido
        item = next(i for i in CD.codificacao(qid)["itens"] if i["origem"] == "llm")
        alvo = next(c for c in CF.frame(qid)["categorias"] if c["nome"] == "Transporte escolar")
        CD.atualizar_item(qid, item["rid"], comentario="isto é Transporte escolar")
        CD.recodificar(qid)
        novo = next(i for i in CD.codificacao(qid)["itens"] if i["rid"] == item["rid"])
        self.assertEqual((novo["primaria"], novo["origem"]), (alvo["codigo"], "llm+comentario"))
        CD.codificar(qid, somente_faltantes=True)
        self.assertEqual(CD.resumo_revisao(qid)["n_faltantes"], 0)
        CD.aprovar(qid)
        CD.aplicar_na_base(verbose=False)
        df, _ = load.carregar_base()
        self.assertEqual(int(df[f"{qid}_COD1"].notna().sum()), dados["n_respondeu"])
        # consumo registra o modelo 'simulado' com custo zero
        U = usage.consolidar()
        self.assertEqual(U["por_modelo"][0]["modelo"], "simulado")
        self.assertEqual(U["total"]["usd"], 0)
        # resultados reais intocados
        config.alternar_modo_teste(False)
        projetos.ativar("sesi")
        self.assertFalse((config.PERGUNTAS_OUT / qid / "codificacao.json").exists())

    def test_api_toggle(self):
        import app as A
        c = A.app.test_client()
        r = c.post("/api/modo-teste", json={"ativo": True}).get_json()
        self.assertTrue(r["modo_teste"])
        self.assertTrue(r["saida"].endswith("_teste"))
        self.assertEqual(c.post("/api/config/testar").get_json()["ok"], True)
        self.assertEqual(c.post("/api/modo-teste/limpar").status_code, 200)
        r = c.post("/api/modo-teste", json={"ativo": False}).get_json()
        self.assertFalse(r["modo_teste"])
        self.assertEqual(c.post("/api/modo-teste/limpar").status_code, 400)  # fora do modo teste não apaga nada

    def test_simulador_padrao(self):
        self.assertEqual(simulador._padrao({"type": "object", "properties": {"ok": {"type": "boolean"}}}), {"ok": True})


if __name__ == "__main__":
    unittest.main()
