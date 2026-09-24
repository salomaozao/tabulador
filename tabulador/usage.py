"""Consumo da IA (aba 'Consumo' da interface): consolida os logs de output/llm_log/ do projeto ativo.

Tokens e tempo vêm do próprio log de cada chamada. O custo é uma ESTIMATIVA com a tabela PRECOS
abaixo (US$ por 1 milhão de tokens: entrada, saída) — confira os preços atuais no site do provedor e
ajuste aqui se precisar. Modelos gratuitos (ex.: sufixo ':free' do OpenRouter) custam 0. Câmbio:
variável de ambiente TABULADOR_USD_BRL (padrão 5,40).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

import config

PRECOS = {  # US$ / 1M tokens (entrada, saída) — referência, sujeita a mudança pelos provedores
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "gpt-oss-120b": (0.15, 0.60),
    "gpt-oss-20b": (0.05, 0.10),
    "qwen3.8-27b": (0.10, 0.20),
    "deepseek-chat": (0.27, 1.10),
    "simulado": (0.0, 0.0),  # modo teste
}
USD_BRL = float(os.getenv("TABULADOR_USD_BRL", "5.40"))

# chamadas/dia do plano GRATUITO de cada provedor — referência aproximada (varia por modelo e muda
# com frequência; confira no site do provedor e ajuste aqui se precisar). None = sem limite diário
# fixo conhecido (cobrança por uso, como OpenAI/DeepSeek, ou provedor personalizado).
LIMITES_DIARIOS = {
    "gemini": 20,  # plano gratuito do gemini-2.5-flash (429 visto em 24/09)
    "groq": 1000,
    "openrouter": 50,
    "deepseek": None,
    "openai": None,
    "personalizado": None,
    "simulado": None,
}


def limite_diario(provedor: str | None) -> int | None:
    return LIMITES_DIARIOS.get((provedor or "").lower())

_NOME_RE = re.compile(r"^(\d{8}_\d{6})_\d+_(.+)\.json$")


def preco(modelo: str | None) -> tuple[float, float] | None:
    if not modelo:
        return None
    m = modelo.lower()
    if m.endswith(":free"):
        return (0.0, 0.0)
    m = m.split("/")[-1]  # openrouter: 'openai/gpt-4.1-mini' -> 'gpt-4.1-mini'
    if m in PRECOS:
        return PRECOS[m]
    for k in sorted(PRECOS, key=len, reverse=True):  # 'gpt-4.1-2025-04-14' -> 'gpt-4.1'
        if m.startswith(k):
            return PRECOS[k]
    return None


def _operacao(nome: str) -> tuple[str, str]:
    """'code_Q33_2' -> ('classificação', 'Q33'); 'frame_Q4' -> ('categorias', 'Q4'); 'refino_Q4' -> ('ajuste de categorias', 'Q4')."""
    if nome == "teste_conexao":
        return "teste de conexão", "—"
    tipo, _, resto = nome.partition("_")
    rotulo = {"code": "classificação", "frame": "categorias", "refino": "ajuste de categorias",
              "audit": "auditoria"}.get(tipo, tipo)
    if tipo in ("code", "audit"):
        resto = re.sub(r"_\d+$", "", resto)
    return rotulo, resto or "—"


def _conferencia() -> dict:
    """Quem conferiu a classificação, por pergunta: pessoas, aceite automático e sugestões do auditor."""
    import coding as CD
    import supervisao
    import variables as V
    out = {}
    for qid in V.perguntas_codificaveis():
        try:
            cod = CD.codificacao(qid)
        except Exception:  # noqa: BLE001 - uma pergunta ilegível não derruba a aba de consumo
            cod = None
        if cod:
            out[qid] = supervisao.conferencia(cod["itens"])
    return out


def _novo() -> dict:
    return {"chamadas": 0, "ok": 0, "erros": 0, "prompt": 0, "completion": 0, "total": 0, "segundos": 0.0, "usd": 0.0, "sem_preco": 0}


def _somar(acc: dict, c: dict) -> None:
    acc["chamadas"] += 1
    acc["ok" if c["ok"] else "erros"] += 1
    for k in ("prompt", "completion", "total"):
        acc[k] += c[k]
    acc["segundos"] += c["segundos"]
    if c["usd"] is None:
        acc["sem_preco"] += 1 if c["ok"] else 0
    else:
        acc["usd"] += c["usd"]


def consolidar(ultimas: int = 50) -> dict:
    pasta = config.LLM_LOG_OUT
    chamadas = []
    if pasta.exists():
        for p in pasta.glob("*.json"):
            m = _NOME_RE.match(p.name)
            if not m:
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            uso = d.get("uso") or {}
            pt, ct = int(uso.get("prompt_tokens") or 0), int(uso.get("completion_tokens") or 0)
            tt = int(uso.get("total_tokens") or (pt + ct))
            pr = preco(d.get("modelo"))
            usd = (pt * pr[0] + ct * pr[1]) / 1e6 if pr is not None else None
            op, qid = _operacao(m.group(2))
            chamadas.append({
                "quando": datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").strftime("%d/%m/%Y %H:%M:%S"),
                "_ord": m.group(1) + p.name, "_dia": m.group(1)[:8], "_hora": m.group(1)[:11], "arquivo": p.name,
                "modelo": d.get("modelo") or "?", "provedor": d.get("provedor") or "openai",
                "operacao": op, "pergunta": qid, "ok": d.get("ok", True), "erro": d.get("erro"),
                "prompt": pt, "completion": ct, "total": tt, "segundos": float(d.get("segundos") or 0), "usd": usd,
            })
    chamadas.sort(key=lambda c: c["_ord"], reverse=True)
    total, por_modelo, por_pergunta, por_dia, por_hora = _novo(), {}, {}, {}, {}
    for c in chamadas:
        _somar(total, c)
        h = por_hora.setdefault(c["_hora"], {**_novo(), "cls": 0, "aud": 0})
        _somar(h, c)
        if c["operacao"] == "auditoria":
            h["aud"] += c["total"]  # tokens do segundo codificador (auditor), separados da classificação
        if c["operacao"] == "classificação":
            h["cls"] += c["total"]  # tokens gastos classificando (base da eficiência por resposta)
        _somar(por_modelo.setdefault(c["modelo"], _novo()), c)
        _somar(por_pergunta.setdefault((c["pergunta"], c["operacao"]), _novo()), c)
        _somar(por_dia.setdefault(c["_dia"], _novo()), c)
    def _fmt(acc: dict) -> dict:
        return {**acc, "segundos": round(acc["segundos"], 1), "usd": round(acc["usd"], 4), "brl": round(acc["usd"] * USD_BRL, 2)}
    hoje = datetime.now().strftime("%Y%m%d")
    usado_hoje = sum(1 for c in chamadas if c["_dia"] == hoje and c["provedor"] == config.OPENAI_PROVEDOR and c["ok"])
    lim = limite_diario(config.OPENAI_PROVEDOR)
    return {
        "projeto": config.NOME_PROJETO,
        "cambio": USD_BRL,
        "total": {**_fmt(total), "taxa_sucesso": round(total["ok"] / total["chamadas"], 3) if total["chamadas"] else None,
                  "primeira": chamadas[-1]["quando"] if chamadas else None, "ultima": chamadas[0]["quando"] if chamadas else None},
        "por_modelo": [{"modelo": k, **_fmt(v), "preco": preco(k)} for k, v in sorted(por_modelo.items(), key=lambda kv: -kv[1]["total"])],
        "por_pergunta": [{"pergunta": q, "operacao": op, **_fmt(v)} for (q, op), v in sorted(por_pergunta.items(), key=lambda kv: -kv[1]["total"])],
        "por_dia": [{"dia": datetime.strptime(k, "%Y%m%d").strftime("%d/%m/%Y"), **_fmt(v)}
                    for k, v in sorted(por_dia.items(), reverse=True)[:30]],
        "limite_diario": {
            "provedor": config.OPENAI_PROVEDOR,
            "nome_provedor": config.PROVEDORES.get(config.OPENAI_PROVEDOR, {}).get("nome", config.OPENAI_PROVEDOR),
            "limite": lim, "usado_hoje": usado_hoje,
            "pct": round(100 * usado_hoje / lim, 1) if lim else None,
        },
        # série por hora (a interface agrupa por hora/dia conforme o período escolhido)
        "conferencia": _conferencia(),
        "serie_hora": [{"h": datetime.strptime(k, "%Y%m%d_%H").strftime("%Y-%m-%dT%H"), **{c: v[c] for c in
                        ("chamadas", "ok", "erros", "prompt", "completion", "total", "sem_preco", "cls", "aud")},
                        "segundos": round(v["segundos"], 1), "usd": round(v["usd"], 6)} for k, v in sorted(por_hora.items())],
        "ultimas": [{k: v for k, v in c.items() if k not in ("_ord", "_dia", "_hora")} for c in chamadas[:ultimas]],
    }
