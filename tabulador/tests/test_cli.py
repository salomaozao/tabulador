"""IA pelos programas instalados (llm_cli): montagem do comando, leitura da resposta e erros — sem rodar
nenhum programa (subprocess.run é substituído). Custo: zero tokens.

Teste REAL (opcional, gasta tokens): chama cada programa instalado uma vez, com o menor pedido possível
(Claude Code com haiku: ~1,3 mil tokens, ~US$ 0,002; Antigravity: ~27 mil tokens de entrada, 16 mil em
cache, pela assinatura). Só roda com TABULADOR_TESTE_CLI=1:
  set TABULADOR_TESTE_CLI=1 && python -m unittest tests.test_cli -v

Rodar só os sem custo:  python -m unittest tests.test_cli -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="tabulador_cli_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import llm  # noqa: E402
import llm_cli  # noqa: E402

SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
REAL = os.getenv("TABULADOR_TESTE_CLI") == "1"
MODELO_BARATO = {"cli_claude": "haiku", "cli_codex": None, "cli_gemini": "gemini-2.5-flash", "cli_agy": "gemini-3.8-flash-low"}


class _Run:
    """Substitui subprocess.run: guarda o comando e a entrada, devolve a saída combinada."""
    def __init__(self, stdout="", returncode=0, stderr="", erro=None):
        self.stdout, self.returncode, self.stderr, self.erro = stdout, returncode, stderr, erro
        self.cmd = self.entrada = self.pasta = None

    def __call__(self, cmd, input=None, cwd=None, **kw):
        self.cmd, self.entrada, self.pasta = cmd, input, cwd
        if self.erro:
            raise self.erro
        return SimpleNamespace(stdout=self.stdout, stderr=self.stderr, returncode=self.returncode)


def _com(exe: str, run: _Run):
    return mock.patch.multiple(llm_cli, executavel=lambda prog: exe), mock.patch.object(llm_cli.subprocess, "run", run)


class TestComandoClaude(unittest.TestCase):
    RESPOSTA = json.dumps({"is_error": False, "structured_output": {"ok": True}, "total_cost_usd": 0.002,
                           "usage": {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 5}})

    def chamar(self, run, exe=r"C:\x\claude.exe", modelo="haiku"):
        a, b = _com(exe, run)
        with a, b:
            return llm_cli.chamar("cli_claude", "SYS", "USER", SCHEMA, modelo)

    def test_sem_ferramentas_schema_e_modelo(self):
        run = _Run(self.RESPOSTA)
        resp, uso = self.chamar(run)
        self.assertEqual(resp, {"ok": True})
        self.assertEqual((uso["prompt_tokens"], uso["completion_tokens"], uso["custo_usd_cli"]), (1010, 5, 0.002))
        c = run.cmd
        self.assertEqual(c[c.index("--tools") + 1], "")  # nenhuma ferramenta
        for flag in ("-p", "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config"):
            self.assertIn(flag, c)
        self.assertEqual(json.loads(c[c.index("--json-schema") + 1]), SCHEMA)
        self.assertEqual(c[c.index("--model") + 1], "haiku")
        self.assertEqual(run.entrada, "USER")  # prompt pela entrada padrão, não na linha de comando
        self.assertNotIn("USER", " ".join(c))

    def test_modelo_padrao_nao_passa_model(self):
        for modelo in ("padrao", "", None):
            run = _Run(self.RESPOSTA)
            self.chamar(run, modelo=modelo)
            self.assertNotIn("--model", run.cmd)

    def test_atalho_cmd_leva_schema_no_prompt(self):
        run = _Run(json.dumps({"is_error": False, "result": '{"ok": true}'}))
        resp, _ = self.chamar(run, exe=r"C:\x\claude.cmd")
        self.assertNotIn("--json-schema", run.cmd)
        self.assertIn("JSON Schema", run.entrada)
        self.assertEqual(llm.extrair_json(resp), {"ok": True})

    def test_erros_viram_ErroCLI(self):
        casos = {
            "is_error": _Run(json.dumps({"is_error": True, "result": "Not logged in"})),
            "saida invalida": _Run("isto não é json"),
            "codigo de erro": _Run("", returncode=1, stderr="falhou feio"),
            "tempo esgotado": _Run(erro=subprocess.TimeoutExpired("claude", 1)),
        }
        for nome, run in casos.items():
            with self.subTest(nome), self.assertRaises(llm_cli.ErroCLI):
                self.chamar(run)

    def test_programa_ausente(self):
        with mock.patch.object(llm_cli, "executavel", lambda prog: None), self.assertRaises(llm_cli.ErroCLI) as e:
            llm_cli.chamar("cli_claude", "s", "u", SCHEMA)
        self.assertIn("não está instalado", str(e.exception))


class TestComandoOutros(unittest.TestCase):
    def test_codex(self):
        run = _Run("ignorado")
        a, b = _com(r"C:\x\codex.exe", run)
        with a, b:
            resp, uso = llm_cli.chamar("cli_codex", "SYS", "USER", SCHEMA, "gpt-5")
        c = run.cmd
        self.assertEqual(c[:2], [r"C:\x\codex.exe", "exec"])
        self.assertEqual(c[c.index("--sandbox") + 1], "read-only")
        self.assertEqual((c[c.index("-m") + 1], c[-1]), ("gpt-5", "-"))
        self.assertTrue(run.entrada.startswith("SYS") and "USER" in run.entrada)
        self.assertEqual(resp, "ignorado")  # sem arquivo de saída: usa o stdout

    def test_gemini(self):
        run = _Run(json.dumps({"response": '{"ok": true}'}))
        a, b = _com(r"C:\x\gemini.exe", run)
        with a, b:
            resp, _ = llm_cli.chamar("cli_gemini", "SYS", "USER", SCHEMA, "padrao")
        self.assertNotIn("-m", run.cmd)
        self.assertEqual(llm.extrair_json(resp), {"ok": True})


class TestComandoAgy(unittest.TestCase):
    """Antigravity: prompt pela entrada padrão em NDJSON (o -p só aceita a linha de comando)."""
    def chamar(self, run, modelo="gemini-3.8-flash-low"):
        a, b = _com(r"C:\x\agy.exe", run)
        with a, b:
            return llm_cli.chamar("cli_agy", "SYS", "USER", SCHEMA, modelo)

    @staticmethod
    def saida(result: dict) -> str:
        return "\n".join([json.dumps({"event": "init", "init": {}}), "linha que não é json",
                          json.dumps({"event": "result", "result": result})])

    def test_comando_entrada_e_resposta(self):
        run = _Run(self.saida({"status": "SUCCESS", "structured_output": {"ok": True},
                               "usage": {"input_tokens": 25000, "output_tokens": 30, "thinking_tokens": 10, "cache_read_tokens": 16000}}))
        resp, uso = self.chamar(run)
        self.assertEqual(resp, {"ok": True})
        self.assertEqual((uso["prompt_tokens"], uso["completion_tokens"], uso["cache_read_tokens"]), (25000, 40, 16000))
        c = run.cmd
        self.assertEqual(c[1], "--print=")
        self.assertEqual((c[c.index("--input-format") + 1], c[c.index("--output-format") + 1]), ("stream-json", "stream-json"))
        self.assertIn("--sandbox", c)
        self.assertEqual(c[c.index("--model") + 1], "gemini-3.8-flash-low")
        self.assertTrue(c[c.index("--json-schema") + 1].endswith("schema.json"))  # schema em arquivo, fora da linha de comando
        msg = json.loads(run.entrada)
        self.assertEqual((msg["event"], msg["message"]["role"]), ("user", "user"))
        self.assertTrue(msg["message"]["content"].startswith("SYS") and "USER" in msg["message"]["content"])
        self.assertNotIn("USER", " ".join(c))

    def test_modelo_padrao_e_resposta_em_texto(self):
        run = _Run(self.saida({"status": "SUCCESS", "response": '{"ok": true}'}))
        resp, _ = self.chamar(run, modelo="padrao")
        self.assertNotIn("--model", run.cmd)
        self.assertEqual(llm.extrair_json(resp), {"ok": True})

    def test_erros(self):
        casos = {"status ERROR": _Run(self.saida({"status": "ERROR", "error": "not signed in"})),
                 "sem evento result": _Run(json.dumps({"event": "init"}))}
        for nome, run in casos.items():
            with self.subTest(nome), self.assertRaises(llm_cli.ErroCLI):
                self.chamar(run)

    def test_acha_fora_do_path(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "agy.exe"
            exe.write_bytes(b"")
            with mock.patch.object(llm_cli.shutil, "which", lambda prog: None), \
                 mock.patch.dict(llm_cli.LOCAIS_EXTRAS, {"agy": [Path(d) / "nao_existe.exe", exe]}):
                self.assertEqual(llm_cli.executavel("agy"), str(exe))
                self.assertIsNone(llm_cli.executavel("codex"))


class TestBotaoTestar(unittest.TestCase):
    """O botão 'Testar' (/api/config/testar) com um provedor CLI, sem rodar o programa."""
    def setUp(self):
        self._antes = (config.OPENAI_PROVEDOR, config.OPENAI_MODEL)
        config.OPENAI_PROVEDOR, config.OPENAI_MODEL = "cli_claude", "haiku"

    def tearDown(self):
        config.OPENAI_PROVEDOR, config.OPENAI_MODEL = self._antes

    def _post(self, resposta=None, erro=None):
        import app as A

        def falso(prov, s, u, schema, modelo):
            if erro:
                raise erro
            return resposta, {"total_tokens": 1}
        with mock.patch.object(llm_cli, "chamar", falso):
            return A.app.test_client().post("/api/config/testar", json={})

    def test_ok(self):
        r = self._post(resposta={"ok": True})
        d = r.get_json()
        self.assertEqual((r.status_code, d["ok"], d["modelo"], d["provedor"]), (200, True, "haiku", "cli_claude"))
        self.assertIn("segundos", d)

    def test_resposta_errada_nao_confirma(self):
        d = self._post(resposta={"ok": False}).get_json()
        self.assertFalse(d["ok"])
        self.assertTrue(d["explicacao"] and d["solucao"])

    def test_falha_traz_explicacao_e_solucao(self):
        casos = {  # erro do programa -> trecho esperado na explicação
            "claude terminou com erro 1: Not logged in · Please run /login": "não está logado",
            "O programa 'claude' não está instalado neste computador (ou não está no PATH).": "não foi encontrado",
            "claude não respondeu em 600 s (timed out).": "demorou",
            "Claude Code: Claude AI usage limit reached": "limite de uso",
            "Claude Code: There's an issue with the selected model (xyz). It may not exist or you may not have access to it.": "não existe",
            "algo muito estranho": "falhou",
        }
        for erro, trecho in casos.items():
            with self.subTest(erro):
                r = self._post(erro=llm_cli.ErroCLI(erro))
                d = r.get_json()
                self.assertEqual((r.status_code, d["ok"]), (200, False))  # 200: a tela mostra a explicação, não um erro genérico
                self.assertIn(trecho, d["explicacao"])
                self.assertTrue(d["solucao"])
                self.assertIn(erro[:20], d["erro"])

    def test_status_informa_quem_esta_instalado(self):
        import app as A
        with mock.patch.object(llm_cli, "executavel", lambda prog: r"C:\x\claude.exe" if prog == "claude" else None):
            prov = A.app.test_client().get("/api/status").get_json()["ia"]["provedores"]
        self.assertEqual({k: prov[k]["disponivel"] for k in llm_cli.PROGRAMAS},
                         {"cli_claude": True, "cli_codex": False, "cli_gemini": False, "cli_agy": False})


@unittest.skipUnless(REAL, "teste real desligado (gasta tokens): defina TABULADOR_TESTE_CLI=1")
class TestReal(unittest.TestCase):
    """Uma chamada mínima por programa instalado. Não usa o .env: o modelo mais barato é escolhido aqui."""
    def test_programas_instalados(self):
        instalados = [p for p in llm_cli.PROGRAMAS if llm_cli.disponivel(p)]
        if not instalados:
            self.skipTest("nenhum programa de IA instalado")
        for prov in instalados:
            with self.subTest(prov):
                resp, uso = llm_cli.chamar(prov, "Responda em JSON.", 'Devolva {"ok": true}.', SCHEMA, MODELO_BARATO[prov])
                dados = resp if isinstance(resp, dict) else llm.extrair_json(resp)
                self.assertIs(dados.get("ok"), True)
                print(f"\n  {prov}: ok · uso {uso}")


if __name__ == "__main__":
    unittest.main()
