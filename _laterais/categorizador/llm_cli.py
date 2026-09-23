"""IA pelos programas de linha de comando instalados no computador (Claude Code, Codex, Gemini CLI),
usando a assinatura/login de quem usa o computador, sem chave de API.

Cada chamada abre o programa em modo não interativo, SEM ferramentas (não lê nem grava arquivos),
numa pasta temporária vazia, com o prompt pela entrada padrão (o Windows limita a linha de comando a
~32 mil caracteres). A resposta passa por llm.extrair_json como as demais.

Situação: Claude Code testado (saída estruturada por --json-schema). Codex e Gemini CLI seguem a
documentação desses programas e NÃO foram testados aqui (não estavam instalados).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TEMPO_LIMITE = int(os.getenv("CATEGORIZADOR_CLI_TEMPO", "600"))  # segundos por chamada

PROGRAMAS = {"cli_claude": "claude", "cli_codex": "codex", "cli_gemini": "gemini"}


class ErroCLI(RuntimeError):
    pass


def executavel(programa: str) -> str | None:
    """Caminho do programa. Os atalhos .cmd do npm são trocados pelo .exe que eles chamam, para os
    argumentos (JSON) não passarem pelo interpretador de lotes do Windows."""
    p = shutil.which(programa)
    if not p:
        return None
    if p.lower().endswith((".cmd", ".bat")):
        try:
            texto = Path(p).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return p
        m = re.search(r'"%dp0%\\([^"]+?\.exe)"', texto, re.IGNORECASE)
        if m:
            exe = Path(p).parent / m.group(1)
            if exe.exists():
                return str(exe)
    return p


def disponivel(provedor: str) -> bool:
    return provedor in PROGRAMAS and executavel(PROGRAMAS[provedor]) is not None


def _instr_schema(schema: dict) -> str:
    return ("\n\nResponda SOMENTE com um objeto JSON válido, sem texto fora dele, seguindo este JSON Schema: "
            + json.dumps(schema, ensure_ascii=False))


def _rodar(cmd: list[str], entrada: str, pasta: str) -> str:
    try:
        r = subprocess.run(cmd, input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=pasta, timeout=TEMPO_LIMITE,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as e:
        raise ErroCLI(f"{Path(cmd[0]).name} não respondeu em {TEMPO_LIMITE} s (timed out).") from e
    if r.returncode != 0 and not r.stdout.strip():
        raise ErroCLI(f"{Path(cmd[0]).name} terminou com erro {r.returncode}: {(r.stderr or r.stdout).strip()[:500]}")
    return r.stdout


def _uso_claude(d: dict) -> dict | None:
    u = d.get("usage") or {}
    pt = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    ct = int(u.get("output_tokens") or 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct, "custo_usd_cli": d.get("total_cost_usd")}


def chamar(provedor: str, system: str, user: str, schema: dict, modelo: str | None = None) -> tuple[dict | str, dict | None]:
    """(resposta, uso). A resposta é o dict já estruturado (Claude) ou o texto a passar por extrair_json."""
    programa = PROGRAMAS[provedor]
    exe = executavel(programa)
    if not exe:
        raise ErroCLI(f"O programa '{programa}' não está instalado neste computador (ou não está no PATH).")
    modelo = None if not modelo or modelo == "padrao" else modelo
    with tempfile.TemporaryDirectory(prefix="categorizador_cli_") as pasta:
        if provedor == "cli_claude":
            arq_sys = Path(pasta) / "system.txt"
            arq_sys.write_text(system, encoding="utf-8")
            cmd = [exe, "-p", "--output-format", "json", "--system-prompt-file", str(arq_sys),
                   "--tools", "", "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config"]
            if exe.lower().endswith((".cmd", ".bat")):  # sem .exe: schema vai no prompt (evita JSON na linha de comando)
                entrada = user + _instr_schema(schema)
            else:
                cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
                entrada = user
            if modelo:
                cmd += ["--model", modelo]
            saida = _rodar(cmd, entrada, pasta)
            try:
                d = json.loads(saida)
            except json.JSONDecodeError as e:
                raise ErroCLI(f"Resposta inesperada do Claude Code: {saida[:300]!r}") from e
            if d.get("is_error"):
                raise ErroCLI(f"Claude Code: {str(d.get('result') or d.get('api_error_status'))[:500]}")
            return (d.get("structured_output") or d.get("result") or ""), _uso_claude(d)
        prompt = f"{system}\n\n---\n\n{user}{_instr_schema(schema)}"
        if provedor == "cli_codex":
            arq_schema, arq_saida = Path(pasta) / "schema.json", Path(pasta) / "resposta.txt"
            arq_schema.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
            cmd = [exe, "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--output-schema", str(arq_schema),
                   "--output-last-message", str(arq_saida)]
            if modelo:
                cmd += ["-m", modelo]
            cmd.append("-")  # prompt pela entrada padrão
            saida = _rodar(cmd, prompt, pasta)
            return (arq_saida.read_text(encoding="utf-8") if arq_saida.exists() else saida), None
        # cli_gemini: a entrada padrão é somada ao -p
        cmd = [exe, "--output-format", "json", "-p", "Siga as instruções recebidas."]
        if modelo:
            cmd += ["-m", modelo]
        saida = _rodar(cmd, prompt, pasta)
        try:
            d = json.loads(saida)
            return d.get("response") or saida, None
        except json.JSONDecodeError:
            return saida, None
