"""Chamada ao LLM com saída JSON validada por schema. Cada chamada (inclusive as que falham) é
registrada em output/llm_log/ (prompt, resposta, tokens, tempo) para auditoria e para a aba Consumo.

Funciona com a OpenAI e com qualquer provedor compatível com a API dela (Gemini, Groq, OpenRouter,
DeepSeek...): muda só `config.OPENAI_BASE_URL`. Se o provedor não aceitar JSON Schema estrito, cai
para `json_object` e, em último caso, para texto livre com extração do JSON (inclusive ```json```).

Para testes, `set_cliente(func)` injeta uma função `func(system, user, schema) -> dict`.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Callable

import config
import progresso

_cliente_fake: Callable | None = None
_client = None
OPENAI_URL_PADRAO = "https://api.openai.com/v1"


def set_cliente(func: Callable | None) -> None:
    global _cliente_fake
    _cliente_fake = func


def resetar() -> None:
    """Descarta o cliente em cache (depois de trocar chave/provedor pela interface)."""
    global _client
    _client = None


def _openai():
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("Chave da IA não configurada. Clique em '⚙ Configurar IA' no topo da página e cole a chave.")
        from openai import OpenAI

        # base_url explícita: um OPENAI_BASE_URL vazio no ambiente quebraria o padrão do SDK
        _client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL or OPENAI_URL_PADRAO,
                         max_retries=3, timeout=180)
    return _client


def _log(nome: str, payload: dict) -> None:
    uso = payload.get("uso") or {}
    progresso.ia_fim(payload.get("segundos") or 0, payload.get("ok", True), uso.get("total_tokens"))
    config.garantir_pastas()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    (config.LLM_LOG_OUT / f"{ts}_{nome}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def extrair_json(texto: str) -> dict:
    """JSON da resposta, mesmo se vier dentro de ```json ... ``` ou com texto em volta."""
    if texto is None:
        raise ValueError("resposta vazia do modelo")
    t = texto.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j > i:
        return json.loads(t[i:j + 1])
    raise ValueError(f"o modelo não devolveu JSON válido: {t[:200]!r}")


def e_limite_ou_cota(e: Exception) -> bool:
    """True se o erro indica cota/limite de uso esgotado no provedor (não vale insistir nos lotes
    restantes de uma classificação em massa — melhor parar e deixar o resto pendente)."""
    msg, cod = str(e).lower(), getattr(e, "status_code", None)
    return bool(
        cod in (429, 413) or "rate limit" in msg or "rate_limit_exceeded" in msg or "resource_exhausted" in msg
        or "insufficient_quota" in msg or ("credit" in msg and "exhaust" in msg) or "no credits" in msg
        or "quota" in msg or "tokens per minute" in msg or "request too large" in msg or "reduce your message size" in msg
    )


def mensagem_amigavel(e: Exception) -> str | None:
    """Erros comuns dos provedores em linguagem simples (None = mantém o erro original)."""
    msg, cod = str(e).lower(), getattr(e, "status_code", None)
    prov = config.PROVEDORES.get(config.OPENAI_PROVEDOR, {}).get("nome", config.OPENAI_PROVEDOR)
    if "insufficient_quota" in msg or "credit" in msg and "exhaust" in msg or "no credits" in msg:
        return (f"A conta do provedor {prov} está sem créditos. Adicione créditos na conta ou, em '⚙ Configurar IA', "
                "troque para um provedor com plano gratuito (Google Gemini ou Groq).")
    if cod == 401 or "invalid api key" in msg or "incorrect api key" in msg or "api key not valid" in msg:
        return f"A chave do provedor {prov} foi recusada (inválida ou revogada). Cole uma chave válida em '⚙ Configurar IA'."
    if cod == 413 or "tokens per minute" in msg or "request too large" in msg or "reduce your message size" in msg:
        return (f"O lote enviado ao provedor {prov} tem tokens demais para o limite por minuto do plano gratuito "
                f"do modelo '{config.OPENAI_MODEL}'. Diminua o tamanho do lote (variável ASSERTIVA_LOTE no .env; "
                "hoje agrupa várias respostas por chamada) ou troque para um modelo/provedor com limite maior.")
    if cod == 429 or "rate limit" in msg or "rate_limit_exceeded" in msg or "resource_exhausted" in msg:
        return (f"Limite de uso do provedor {prov} atingido (muitas chamadas por minuto ou cota diária do plano gratuito). "
                "Espere um pouco e tente de novo, ou classifique em amostras menores.")
    if cod == 404 or "model_not_found" in msg or ("model" in msg and "not found" in msg):
        return f"O modelo '{config.OPENAI_MODEL}' não existe ou não está disponível no provedor {prov}. Escolha outro em '⚙ Configurar IA'."
    if "connection" in msg or "timed out" in msg or "timeout" in msg:
        return f"Não foi possível conectar ao provedor {prov}. Verifique a internet (e o endereço da API, se for personalizado)."
    return None


def _uso(resp) -> dict | None:
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    try:
        return u.model_dump()
    except Exception:  # noqa: BLE001
        return {k: getattr(u, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}


def _chamar_cli(system: str, user: str, schema: dict, nome: str, base: dict, t0: float) -> dict:
    """IA pelo programa instalado no computador (ver llm_cli.py)."""
    import llm_cli
    try:
        resposta, uso = llm_cli.chamar(config.OPENAI_PROVEDOR, system, user, schema, config.OPENAI_MODEL)
        dados = resposta if isinstance(resposta, dict) else extrair_json(resposta)
    except Exception as e:
        _log(nome, {**base, "segundos": round(time.time() - t0, 1), "uso": None, "ok": False,
                    "erro": f"{type(e).__name__}: {str(e)[:500]}", "system": system, "user": user})
        amigavel = mensagem_amigavel(e)
        if amigavel:
            raise RuntimeError(amigavel) from e
        raise
    _log(nome, {**base, "segundos": round(time.time() - t0, 1), "uso": uso, "ok": True, "modo": "cli",
                "system": system, "user": user, "resposta": dados})
    return dados


def chamar_json(system: str, user: str, schema: dict, nome: str = "chamada") -> dict:
    """Retorna o JSON da resposta. `schema` é um JSON Schema (modo estrito quando o provedor aceita)."""
    if _cliente_fake is not None:
        return _cliente_fake(system, user, schema)

    progresso.ia_inicio()
    t0 = time.time()
    base = {"modelo": config.OPENAI_MODEL, "provedor": config.OPENAI_PROVEDOR}
    if config.modo_teste():  # modo teste: valores simulados, sem rede nem custo (ver simulador.py)
        import simulador
        dados = simulador.responder(system, user, schema)
        pt, ct = (len(system) + len(user)) // 4, len(json.dumps(dados, ensure_ascii=False)) // 4  # tokens aproximados
        _log(nome, {**base, "modelo": "simulado", "segundos": round(time.time() - t0, 1), "ok": True, "modo": "simulado",
                    "uso": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
                    "system": system, "user": user, "resposta": dados})
        return dados
    if config.usa_cli():
        return _chamar_cli(system, user, schema, nome, base, t0)
    try:
        client = _openai()
        instr_schema = "\nResponda SOMENTE com um objeto JSON válido, sem texto fora dele, seguindo este JSON Schema: " + json.dumps(schema, ensure_ascii=False)
        # tentativas, da mais rígida para a mais tolerante
        tentativas = [
            ("json_schema", {"type": "json_schema", "json_schema": {"name": re.sub(r"[^A-Za-z0-9_-]", "_", nome)[:64], "strict": True, "schema": schema}}, system),
            ("json_object", {"type": "json_object"}, system + instr_schema),
            ("texto", None, system + instr_schema),
        ]
        temperatura = config.LLM_TEMPERATURA
        ultimo_erro = None
        resp = modo = None
        for modo, fmt, sys_msg in tentativas:
            kwargs = dict(model=config.OPENAI_MODEL, messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user}])
            if fmt:
                kwargs["response_format"] = fmt
            if temperatura is not None:
                kwargs["temperature"] = temperatura
            try:
                resp = client.chat.completions.create(**kwargs)
            except Exception as e:  # noqa: BLE001
                msg = str(e).lower()
                if "temperature" in msg and temperatura is not None:  # modelos que não aceitam temperature
                    temperatura = None
                    kwargs.pop("temperature", None)
                    try:
                        resp = client.chat.completions.create(**kwargs)
                    except Exception as e2:  # noqa: BLE001
                        ultimo_erro = e2
                        continue
                elif getattr(e, "status_code", None) in (400, 404, 422) or any(k in msg for k in ("response_format", "json_schema", "schema", "not supported", "unsupported")):
                    ultimo_erro = e
                    continue  # formato não suportado: tenta o próximo modo
                else:
                    raise  # chave inválida, limite de uso, rede...
            try:
                dados = extrair_json(resp.choices[0].message.content)
                break
            except ValueError as e:
                ultimo_erro = e
                resp = None
        if resp is None:
            raise ultimo_erro or RuntimeError("falha ao chamar o modelo")
    except Exception as e:
        _log(nome, {**base, "segundos": round(time.time() - t0, 1), "uso": None, "ok": False,
                    "erro": f"{type(e).__name__}: {str(e)[:500]}", "system": system, "user": user})
        amigavel = mensagem_amigavel(e)
        if amigavel:
            raise RuntimeError(amigavel) from e
        raise
    _log(nome, {**base, "segundos": round(time.time() - t0, 1), "uso": _uso(resp), "ok": True, "modo": modo,
                "system": system, "user": user, "resposta": dados})
    return dados
