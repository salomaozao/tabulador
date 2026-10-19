"""IA pelos programas de linha de comando instalados no computador (Claude Code, Codex, Gemini CLI, Antigravity),
usando a assinatura/login de quem usa o computador, sem chave de API.

Cada chamada abre o programa em modo não interativo, SEM ferramentas (não lê nem grava arquivos),
numa pasta temporária vazia, com o prompt pela entrada padrão (o Windows limita a linha de comando a
~32 mil caracteres). A resposta passa por llm.extrair_json como as demais.

Situação: Claude Code e Antigravity (agy) testados (saída estruturada por --json-schema). Codex e Gemini CLI seguem a
documentação desses programas e NÃO foram testados aqui (não estavam instalados).

Antigravity: o -p só aceita o prompt na linha de comando; por isso usamos --input-format stream-json
(uma mensagem NDJSON {"event": "user", ...} pela entrada padrão). Não há opção para desligar as
ferramentas: no modo não interativo as que pedem permissão são negadas, e --sandbox restringe o terminal.
Cada chamada carrega o prompt de agente do programa (~25 mil tokens de entrada, boa parte em cache).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TEMPO_LIMITE = int(os.getenv("TABULADOR_CLI_TEMPO", "600"))  # segundos por chamada

PROGRAMAS = {"cli_claude": "claude", "cli_codex": "codex", "cli_gemini": "gemini", "cli_agy": "agy"}
# instaladores que não põem o programa no PATH
LOCAIS_EXTRAS = {"agy": [Path.home() / ".gemini" / "bin" / "agy.exe", Path.home() / ".gemini" / "bin" / "agy"]}


class ErroCLI(RuntimeError):
    pass


def executavel(programa: str) -> str | None:
    """Caminho do programa. Os atalhos .cmd do npm são trocados pelo .exe que eles chamam, para os
    argumentos (JSON) não passarem pelo interpretador de lotes do Windows."""
    p = shutil.which(programa)
    if not p:
        return next((str(x) for x in LOCAIS_EXTRAS.get(programa, []) if x.is_file()), None)
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


def _uso_agy(r: dict) -> dict | None:
    u = r.get("usage") or {}
    pt = int(u.get("input_tokens") or 0)
    ct = int(u.get("output_tokens") or 0) + int(u.get("thinking_tokens") or 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct, "cache_read_tokens": u.get("cache_read_tokens")}


def _agy(exe: str, prompt: str, schema: dict, modelo: str | None, pasta: str) -> tuple[dict | str, dict | None]:
    arq_schema = Path(pasta) / "schema.json"
    arq_schema.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    cmd = [exe, "--print=", "--input-format", "stream-json", "--output-format", "stream-json",
           "--json-schema", str(arq_schema), "--sandbox", "--disable-slash-commands"]
    if modelo:
        cmd += ["--model", modelo]
    entrada = json.dumps({"event": "user", "message": {"role": "user", "content": prompt}}, ensure_ascii=False) + "\n"
    saida = _rodar(cmd, entrada, pasta)
    resultado = None
    for linha in saida.splitlines():  # um evento JSON por linha; o último "result" traz a resposta
        try:
            ev = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict) and ev.get("event") == "result":
            resultado = ev.get("result") or {}
    if resultado is None:
        raise ErroCLI(f"Resposta inesperada do Antigravity: {saida[-300:]!r}")
    if resultado.get("status") != "SUCCESS":
        raise ErroCLI(f"Antigravity: {str(resultado.get('error') or resultado.get('status'))[:500]}")
    return (resultado.get("structured_output") or resultado.get("response") or ""), _uso_agy(resultado)


def chamar(provedor: str, system: str, user: str, schema: dict, modelo: str | None = None) -> tuple[dict | str, dict | None]:
    """(resposta, uso). A resposta é o dict já estruturado (Claude) ou o texto a passar por extrair_json."""
    programa = PROGRAMAS[provedor]
    exe = executavel(programa)
    if not exe:
        raise ErroCLI(f"O programa '{programa}' não está instalado neste computador (ou não está no PATH).")
    modelo = None if not modelo or modelo == "padrao" else modelo
    with tempfile.TemporaryDirectory(prefix="tabulador_cli_") as pasta:
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
        if provedor == "cli_agy":
            return _agy(exe, prompt, schema, modelo, pasta)
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
