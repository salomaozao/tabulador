"""Provedores de IA (base_url, chaves por provedor, fallback de JSON) e aba Consumo — sem rede.

Rodar:  python -m unittest discover -s tests -v
Nunca grava no .env real nem em output/ (usa pastas temporárias).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_TMP = tempfile.mkdtemp(prefix="tabulador_ia_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import config  # noqa: E402
import llm  # noqa: E402
import projetos  # noqa: E402
import usage  # noqa: E402

VARS = (["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_PROVEDOR"] + [f"TABULADOR_CHAVE_{p.upper()}" for p in config.PROVEDORES]
        + [v for vs in config.CHAVES_PADRAO.values() for v in vs])


class _Erro400(Exception):
    status_code = 400


class _ClienteFake:
    """json_schema -> 400; json_object -> texto com ```json```."""
    def __init__(self):
        self.modos = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        modo = (kw.get("response_format") or {}).get("type", "texto")
        self.modos.append(modo)
        if modo == "json_schema":
            raise _Erro400("response_format json_schema is not supported by this model")
        conteudo = 'Claro! Aqui está:\n```json\n{"ok": true}\n```'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=conteudo))],
                               usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}))


class TestProvedores(unittest.TestCase):
    def setUp(self):
        projetos.ativar("sesi")
        self._env = {k: os.environ.get(k) for k in VARS}
        self._cfg = (config.ENV_FILE, config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR)
        config.ENV_FILE = Path(tempfile.mkdtemp()) / ".env"
        for k in VARS:
            os.environ.pop(k, None)
        config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR = "sk-antiga", "gpt-4.1", None, "openai"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config.ENV_FILE, config.OPENAI_API_KEY, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_PROVEDOR = self._cfg
        llm.resetar()

    def test_trocar_provedor_guarda_chaves(self):
        config.salvar_llm(provedor="gemini", chave="AIza-teste")
        self.assertEqual(config.OPENAI_PROVEDOR, "gemini")
        self.assertEqual(config.OPENAI_BASE_URL, config.PROVEDORES["gemini"]["base_url"])
        self.assertEqual(config.OPENAI_MODEL, config.PROVEDORES["gemini"]["modelo"])
        self.assertEqual(config.OPENAI_API_KEY, "AIza-teste")
        # volta para a OpenAI sem colar chave: recupera a chave antiga
        config.salvar_llm(provedor="openai")
        self.assertEqual(config.OPENAI_API_KEY, "sk-antiga")
        self.assertIsNone(config.OPENAI_BASE_URL)
        self.assertTrue(config.chave_salva("gemini"))
        with self.assertRaises(ValueError):
            config.salvar_llm(provedor="groq")  # nunca teve chave
        os.environ["GROQ_API_KEY"] = "gsk_do_ambiente"  # variável padrão do provedor é usada sozinha
        config.salvar_llm(provedor="groq")
        self.assertEqual(config.OPENAI_API_KEY, "gsk_do_ambiente")
        config.salvar_llm(provedor="openai")
        txt = config.ENV_FILE.read_text(encoding="utf-8")
        self.assertIn("OPENAI_PROVEDOR=openai", txt)
        self.assertIn("TABULADOR_CHAVE_GEMINI=AIza-teste", txt)

    def test_personalizado_e_base_url_no_cliente(self):
        config.salvar_llm(provedor="personalizado", chave="x-123", modelo="meu-modelo", base_url="http://localhost:11434/v1")
        llm.resetar()
        c = llm._openai()
        self.assertTrue(str(c.base_url).startswith("http://localhost:11434/v1"))
        config.salvar_llm(provedor="openai")
        llm.resetar()
        self.assertTrue(str(llm._openai().base_url).startswith("https://api.openai.com/v1"))

    def test_fallback_json_object_e_markdown(self):
        fake = _ClienteFake()
        llm._client = fake
        r = llm.chamar_json("sys", "user", {"type": "object", "properties": {"ok": {"type": "boolean"}}}, nome="code_Q4_1")
        self.assertEqual(r, {"ok": True})
        self.assertEqual(fake.modos, ["json_schema", "json_object"])
        log = sorted(config.LLM_LOG_OUT.glob("*code_Q4_1.json"))[-1]
        d = json.loads(log.read_text(encoding="utf-8"))
        self.assertEqual((d["ok"], d["modo"], d["uso"]["total_tokens"]), (True, "json_object", 1500))

    def test_extrair_json(self):
        self.assertEqual(llm.extrair_json('{"a": 1}'), {"a": 1})
        self.assertEqual(llm.extrair_json("```json\n{\"a\": 2}\n```"), {"a": 2})
        self.assertEqual(llm.extrair_json('Resposta: {"a": 3} fim'), {"a": 3})
        with self.assertRaises(ValueError):
            llm.extrair_json("sem json aqui")


class TestUsage(unittest.TestCase):
    def setUp(self):
        projetos.ativar("sesi")
        config.garantir_pastas()
        for p in config.LLM_LOG_OUT.glob("*.json"):
            p.unlink()
        def grava(nome, **d):
            (config.LLM_LOG_OUT / nome).write_text(json.dumps(d), encoding="utf-8")
        grava("20260922_100000_000001_frame_Q4.json", modelo="gpt-4.1", segundos=10.0, uso={"prompt_tokens": 1_000_000, "completion_tokens": 0, "total_tokens": 1_000_000}, ok=True)
        grava("20260922_100100_000001_code_Q4_1.json", modelo="gpt-4.1", segundos=5.0, uso={"prompt_tokens": 0, "completion_tokens": 1_000_000, "total_tokens": 1_000_000})
        grava("20260922_100200_000001_code_Q4_2.json", modelo="meta-llama/llama-3.3-70b-instruct:free", provedor="openrouter", segundos=2.5, uso={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, ok=True)
        grava("20260922_100300_000001_code_Q5_1.json", modelo="modelo-desconhecido", segundos=1.0, uso=None, ok=False, erro="RateLimitError: 429")
        (config.LLM_LOG_OUT / "lixo.txt").write_text("x")

    def test_consolidar(self):
        U = usage.consolidar()
        T = U["total"]
        self.assertEqual((T["chamadas"], T["ok"], T["erros"]), (4, 3, 1))
        self.assertEqual(T["prompt"], 1_000_010)
        self.assertAlmostEqual(T["usd"], 2.00 + 8.00, places=4)  # gpt-4.1: US$2 entrada + US$8 saída por 1M
        self.assertAlmostEqual(T["brl"], round(10 * usage.USD_BRL, 2))
        self.assertEqual(T["segundos"], 18.5)
        ops = {(r["pergunta"], r["operacao"]): r for r in U["por_pergunta"]}
        self.assertEqual(ops[("Q4", "classificação")]["chamadas"], 2)
        self.assertEqual(ops[("Q4", "categorias")]["chamadas"], 1)
        self.assertEqual(U["ultimas"][0]["pergunta"], "Q5")  # mais recente primeiro
        self.assertFalse(U["ultimas"][0]["ok"])
        self.assertEqual(usage.preco("openai/gpt-4.1-mini"), usage.PRECOS["gpt-4.1-mini"])
        self.assertEqual(usage.preco("gpt-4.1-2025-04-14"), usage.PRECOS["gpt-4.1"])
        self.assertIsNone(usage.preco("modelo-desconhecido"))

    def test_api(self):
        import app as A
        c = A.app.test_client()
        u = c.get("/api/usage").get_json()
        self.assertEqual(u["total"]["chamadas"], 4)
        ia = c.get("/api/status").get_json()["ia"]
        self.assertIn("gemini", ia["provedores"])
        self.assertNotIn("chave", json.dumps(ia).replace("tem_chave", "").replace("chave_prefixo", "").replace("sem_chave", ""))


if __name__ == "__main__":
    unittest.main()
