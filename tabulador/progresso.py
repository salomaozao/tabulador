"""Andamento da operação longa em curso (lido pela interface em /api/progresso, a cada ~1 s).

Uma operação (gerar categorias, classificar, aprovar...) é aberta em app.py com `operacao(titulo, etapas)`;
os módulos do pipeline avisam em que etapa estão com `etapa(chave, detalhe)` e atualizam contadores
com `atualizar(...)`. Fora de uma operação (linha de comando, testes) todas as funções não fazem nada.

A interface mostra: etapas (feitas / em andamento / a fazer), barra de progresso, tempo decorrido,
estimativa de tempo restante, velocidade e as últimas mensagens (ex.: "lote 3 de 10 concluído").
A estimativa de chamadas únicas (gerar/ajustar categorias) vem do tempo médio das últimas chamadas
do mesmo tipo, registrado em output/llm_log/.
"""
from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime

_lock = threading.Lock()
ESTADO: dict = {"ativo": False, "id": 0}


def _agora() -> float:
    return time.time()


def iniciar(titulo: str, etapas: list, **extra) -> None:
    """etapas: [(chave, nome) | (chave, nome, peso)] — o peso define quanto da barra a etapa ocupa."""
    with _lock:
        ident = ESTADO.get("id", 0) + 1
        ESTADO.clear()
        ESTADO.update(
            ativo=True, id=ident, titulo=titulo, inicio=_agora(), fim=None, erro=None,
            etapas=[{"chave": e[0], "nome": e[1], "peso": e[2] if len(e) > 2 else 1, "estado": "pendente",
                     "detalhe": "", "inicio": None, "fim": None, "estimativa": None} for e in etapas],
            feitos=0, total=0, unidade="respostas", lotes_feitos=0, lotes_total=0, erros=0, limite_atingido=False,
            ia_ativas=0, ia_feitas=0, ia_erros=0, tokens=0, eventos=[], **extra,
        )


def _achar(chave: str) -> dict | None:
    return next((e for e in ESTADO.get("etapas", []) if e["chave"] == chave), None)


def etapa(chave: str, detalhe: str = "", estimativa: float | None = None) -> None:
    """Marca a etapa `chave` como em andamento (e as anteriores como feitas)."""
    with _lock:
        if not ESTADO.get("ativo"):
            return
        alvo = _achar(chave)
        if alvo is None:
            return
        t = _agora()
        for e in ESTADO["etapas"]:
            if e is alvo:
                break
            if e["estado"] != "feito":
                e["estado"], e["fim"] = "feito", t
                e["inicio"] = e["inicio"] or t
        alvo.update(estado="ativo", inicio=alvo["inicio"] or t, detalhe=detalhe or alvo["detalhe"])
        if estimativa:
            alvo["estimativa"] = float(estimativa)


def detalhe(texto: str, chave: str | None = None) -> None:
    with _lock:
        if not ESTADO.get("ativo"):
            return
        e = _achar(chave) if chave else next((x for x in ESTADO["etapas"] if x["estado"] == "ativo"), None)
        if e:
            e["detalhe"] = texto


def atualizar(**kw) -> None:
    with _lock:
        if ESTADO.get("ativo"):
            ESTADO.update(kw)


def evento(msg: str) -> None:
    with _lock:
        if not ESTADO.get("ativo"):
            return
        ESTADO["eventos"].append({"hora": datetime.now().strftime("%H:%M:%S"), "msg": msg})
        del ESTADO["eventos"][:-30]


# ---- chamadas à IA (llm.chamar_json avisa início e fim de cada uma)
def ia_inicio() -> None:
    with _lock:
        if ESTADO.get("ativo"):
            ESTADO["ia_ativas"] += 1


def ia_fim(segundos: float, ok: bool, tokens: int | None) -> None:
    with _lock:
        if not ESTADO.get("ativo"):
            return
        ESTADO["ia_ativas"] = max(0, ESTADO["ia_ativas"] - 1)
        ESTADO["ia_feitas" if ok else "ia_erros"] += 1
        ESTADO["tokens"] += int(tokens or 0)


def concluir() -> None:
    with _lock:
        t = _agora()
        for e in ESTADO.get("etapas", []):
            if e["estado"] != "feito":
                e["estado"], e["fim"] = "feito", t
        ESTADO.update(ativo=False, fim=t)


def falhar(msg: str) -> None:
    with _lock:
        for e in ESTADO.get("etapas", []):
            if e["estado"] == "ativo":
                e["estado"] = "erro"
        ESTADO.update(ativo=False, fim=_agora(), erro=msg)


@contextmanager
def operacao(titulo: str, etapas: list, **extra):
    iniciar(titulo, etapas, **extra)
    try:
        yield
    except Exception as e:
        falhar(str(e))
        raise
    concluir()


# ---- leitura para a interface
def ler() -> dict:
    """Cópia do estado + números calculados: decorrido, % da barra, tempo restante e velocidade."""
    with _lock:
        s = json.loads(json.dumps(ESTADO, default=str))
    if not s.get("etapas"):
        return s
    t = s.get("fim") or _agora()
    s["decorrido"] = round(t - s["inicio"], 1)
    peso_total = sum(e["peso"] for e in s["etapas"]) or 1
    feito = sum(e["peso"] for e in s["etapas"] if e["estado"] == "feito")
    ativa = next((e for e in s["etapas"] if e["estado"] == "ativo"), None)
    restante = None
    s["indeterminado"] = False
    if ativa:
        dec_etapa = t - (ativa["inicio"] or t)
        ativa["decorrido"] = round(dec_etapa, 1)
        frac = 0.0
        if ativa["chave"] == "ia" and s.get("total"):  # classificação em lotes: progresso real
            frac = s["feitos"] / s["total"]
            if s["feitos"]:
                restante = dec_etapa / s["feitos"] * (s["total"] - s["feitos"])
                s["velocidade_min"] = round(s["feitos"] / max(dec_etapa, 0.1) * 60, 1)
            elif ativa.get("estimativa"):
                restante = max(0.0, ativa["estimativa"] - dec_etapa)
        elif ativa.get("estimativa"):  # chamada única: estima pelo histórico (nunca passa de 95%)
            frac = min(0.95, dec_etapa / ativa["estimativa"])
            restante = max(0.0, ativa["estimativa"] - dec_etapa)
        else:
            s["indeterminado"] = ativa["peso"] >= 3  # etapa longa sem como medir: barra animada
        feito += ativa["peso"] * frac
    s["pct"] = round(100 * feito / peso_total, 1)
    s["restante"] = None if restante is None else round(restante, 1)
    return s


def tempo_medio(prefixo: str, ultimas: int = 12) -> float | None:
    """Tempo médio (s) das últimas chamadas bem-sucedidas cujo nome começa com `prefixo` (frame_, refino_,
    code_) no modelo atual. None se não houver histórico."""
    import config
    pasta = config.LLM_LOG_OUT
    if not pasta.exists():
        return None
    arqs = sorted((p for p in pasta.glob(f"*_{prefixo}*.json")), key=lambda p: p.name, reverse=True)[:60]
    tempos = []
    for p in arqs:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("ok", True) and d.get("modelo") in (config.OPENAI_MODEL, "simulado" if config.modo_teste() else None) and d.get("segundos"):
            tempos.append(float(d["segundos"]))
        if len(tempos) >= ultimas:
            break
    return sum(tempos) / len(tempos) if tempos else None
