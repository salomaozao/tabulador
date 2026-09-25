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
from contextlib import contextmanager
from typing import Callable

import config
import progresso

_cliente_fake: Callable | None = None
_client = None
OPENAI_URL_PADRAO = "https://api.openai.com/v1"


def set_cliente(func: Callable | None) -> None:
    global _cliente_fake
    _cliente_fake = func


@contextmanager
def usando(provedor: str | None = None, modelo: str | None = None):
    """Troca provedor/modelo só durante o bloco (ex.: o auditor, segundo codificador, usa outra IA).
    Não grava nada no .env; ao sair, volta exatamente ao que estava."""
    if not provedor or (provedor == config.OPENAI_PROVEDOR and (not modelo or modelo == config.OPENAI_MODEL)):
        yield
        return
    P = config.PROVEDORES.get(provedor)
    if P is None:
        raise ValueError(f"Provedor desconhecido: {provedor}")
    antes = (config.OPENAI_PROVEDOR, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_API_KEY)
    sem_chave = bool(P.get("sem_chave") or P.get("cli"))
    chave = None if sem_chave else config._chave_guardada(provedor)
    if not sem_chave and not chave:
        raise RuntimeError(f"Não há chave guardada para {P['nome']}. Cole a chave em '⚙ Configurar IA' (uma vez) e tente de novo.")
    config.OPENAI_PROVEDOR, config.OPENAI_MODEL = provedor, modelo or P.get("modelo") or antes[1]
    config.OPENAI_BASE_URL, config.OPENAI_API_KEY = P.get("base_url") or None, chave or antes[3]
    resetar()
    try:
        yield
    finally:
        config.OPENAI_PROVEDOR, config.OPENAI_MODEL, config.OPENAI_BASE_URL, config.OPENAI_API_KEY = antes
        resetar()


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


def diagnosticar(e: Exception) -> dict:
    """Erro de uma chamada à IA -> {explicacao, solucao} em linguagem simples (usado no botão 'Testar conexão')."""
    raiz = e.__cause__ or e
    msg = f"{e} {raiz}".lower()
    prov_id = config.OPENAI_PROVEDOR
    P = config.PROVEDORES.get(prov_id, {})
    prov, modelo = P.get("nome", prov_id), config.OPENAI_MODEL
    if P.get("cli"):
        import llm_cli
        prog = llm_cli.PROGRAMAS.get(prov_id, prov_id)
        if "não está instalado" in msg:
            return {"explicacao": f"O programa '{prog}' não foi encontrado neste computador (ou não está no PATH).",
                    "solucao": f"Instale o programa ({P.get('link', '')}), faça login nele e abra o Tabulador de novo pelo atalho."}
        if any(k in msg for k in ("not logged in", "/login", "please login", "log in", "unauthenticated", "authentication", "oauth", "credentials")):
            return {"explicacao": f"O programa '{prog}' está instalado, mas não está logado (ou o login expirou).",
                    "solucao": f"Abra um terminal, rode '{prog}' e faça login (no Claude Code: comando /login). Depois clique em 'Testar conexão' de novo."}
        if "não respondeu em" in msg or "timed out" in msg:
            return {"explicacao": f"O programa '{prog}' demorou mais que {llm_cli.TEMPO_LIMITE} s para responder.",
                    "solucao": "Tente de novo. Se continuar, escolha um modelo mais rápido (ex.: haiku) ou aumente TABULADOR_CLI_TEMPO no .env."}
        if any(k in msg for k in ("usage limit", "limit reached", "rate limit", "quota", "credit", "overloaded")):
            return {"explicacao": f"O programa '{prog}' recusou a chamada por limite de uso da assinatura (ou o serviço está sobrecarregado).",
                    "solucao": "Espere o limite renovar e tente de novo, ou troque de modelo/provedor em '⚙ Configurar IA'."}
        if "model" in msg and any(k in msg for k in ("not found", "invalid", "unknown", "not available", "not exist", "issue with the selected model", "not have access")):
            return {"explicacao": f"O modelo '{modelo}' não existe (ou não está liberado) no programa '{prog}'.",
                    "solucao": "Escolha outro modelo da lista, ou 'padrao' para usar o padrão do programa."}
        if "resposta inesperada" in msg or "json" in msg:
            return {"explicacao": f"O programa '{prog}' respondeu, mas fora do formato esperado (JSON).",
                    "solucao": f"Tente de novo. Se repetir, atualize o programa (ex.: '{prog} update') ou escolha outro modelo."}
        return {"explicacao": f"O programa '{prog}' falhou: {str(raiz)[:300]}",
                "solucao": f"Abra um terminal e rode '{prog}' para ver se ele funciona e está logado; depois teste de novo."}
    if config.modo_teste():
        return {"explicacao": "O modo teste está ligado: não há IA real para testar.", "solucao": "Desligue o modo teste no topo da página."}
    cod = getattr(raiz, "status_code", None)
    if not config.OPENAI_API_KEY:
        return {"explicacao": f"Não há chave guardada para o provedor {prov}.", "solucao": "Cole a chave do provedor em '⚙ Configurar IA' e teste de novo."}
    if "insufficient_quota" in msg or "no credits" in msg or ("credit" in msg and "exhaust" in msg):
        return {"explicacao": f"A conta do provedor {prov} está sem créditos.",
                "solucao": "Adicione créditos na conta, ou troque para um provedor com plano gratuito (Google Gemini ou Groq)."}
    if cod == 401 or any(k in msg for k in ("invalid api key", "incorrect api key", "api key not valid", "unauthorized")):
        return {"explicacao": f"A chave do provedor {prov} foi recusada (inválida ou revogada).",
                "solucao": f"Gere uma chave nova ({P.get('link', 'site do provedor')}) e cole em '⚙ Configurar IA'."}
    if cod == 429 or any(k in msg for k in ("rate limit", "rate_limit_exceeded", "resource_exhausted")):
        return {"explicacao": f"Limite de uso do provedor {prov} atingido (chamadas por minuto ou cota diária).",
                "solucao": "Espere alguns minutos e teste de novo, ou troque de provedor/modelo."}
    if cod == 404 or "model_not_found" in msg or ("model" in msg and "not found" in msg):
        return {"explicacao": f"O modelo '{modelo}' não existe ou não está disponível no provedor {prov}.",
                "solucao": "Escolha um modelo da lista em '⚙ Configurar IA'."}
    if any(k in msg for k in ("connection", "timed out", "timeout", "getaddrinfo", "name resolution")):
        return {"explicacao": f"Não foi possível conectar ao provedor {prov}.",
                "solucao": "Verifique a internet (e o endereço da API, se for personalizado) e teste de novo."}
    return {"explicacao": f"O provedor {prov} devolveu um erro: {str(raiz)[:300]}",
            "solucao": "Confira a chave, o modelo e o endereço em '⚙ Configurar IA'. Se persistir, veja a mensagem original abaixo."}


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
