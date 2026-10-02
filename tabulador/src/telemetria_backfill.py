"""Preenche `classificado_por`/`classificado_em` nas respostas classificadas ANTES da telemetria (PEND-26).

A fonte é o log das chamadas de IA (`output/llm_log/*_code_<QID>_<n>.json`), que guarda modelo, provedor
e a resposta de cada lote. Uma resposta só recebe o carimbo quando o log traz o MESMO rid com a MESMA
categoria, confiança e justificativa (evidência forte; rid sozinho não basta, pois já mudou com a base nova).
O carimbo vai com `classificado_por_estimado: true`. O que não casa fica sem carimbo ("desconhecido").

Não mexe em nada além desses campos. Por padrão só mostra o que faria (simulação).

Uso:  python src/telemetria_backfill.py -p sesi [Q4 Q5 ...] [--aplicar]
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime

import codeframe as CF
import coding as CD
import config

_NOME = re.compile(r"^(\d{8}_\d{6})_\d+_code_(.+)_\d+\.json$")


def _logs(qid: str) -> dict[int, dict]:
    """{rid: {por, em, chave}} do carimbo mais recente de cada resposta, lendo os logs do mais velho ao mais novo."""
    achados: dict[int, dict] = {}
    if not config.LLM_LOG_OUT.exists():
        return achados
    for p in sorted(config.LLM_LOG_OUT.glob("*_code_*.json")):
        m = _NOME.match(p.name)
        if not m or m.group(2) != qid:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not d.get("ok", True) or not isinstance(d.get("resposta"), dict) or not d.get("modelo"):
            continue
        por = f"{d.get('provedor') or 'openai'}:{d['modelo']}"
        em = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").isoformat(timespec="seconds")
        for c in d["resposta"].get("codificacoes", []):
            achados[int(c["rid"])] = {"por": por, "em": em, "primaria": c.get("primaria"), "secundaria": c.get("secundaria"),
                                      "confianca": round(float(c.get("confianca") or 0), 2), "justificativa": c.get("justificativa", "")}
    return achados


def estimar(qid: str, aplicar: bool = False) -> dict:
    logs = _logs(qid)  # a parte lenta vem ANTES de ler a codificação: encurta a janela entre ler e gravar (PEND-31)
    cod = CD.codificacao(qid)
    if not cod:
        return {"qid": qid, "itens": 0, "casaram": 0, "sem_carimbo": 0, "por_modelo": {}}
    n_pendentes, casou = 0, Counter()
    for i in cod["itens"]:
        if i.get("classificado_por") or i.get("origem") not in ("llm", "llm+comentario"):
            continue
        n_pendentes += 1
        a = logs.get(i["rid"])
        if a and (a["primaria"], a["secundaria"], a["confianca"], a["justificativa"]) == (
                i.get("primaria"), i.get("secundaria"), i.get("confianca"), i.get("justificativa", "")):
            casou[a["por"]] += 1
            if aplicar:
                i["classificado_por"], i["classificado_em"], i["classificado_por_estimado"] = a["por"], a["em"], True
    if aplicar and casou:
        CF.snapshot_antes(qid, "telemetria: carimbo estimado do modelo")
        CF._gravar(qid, "codificacao.json", cod)
    return {"qid": qid, "itens": len(cod["itens"]), "sem_carimbo_antes": n_pendentes, "casaram": sum(casou.values()),
            "sem_carimbo": n_pendentes - sum(casou.values()), "por_modelo": dict(casou), "aplicado": aplicar}


def _main() -> None:
    import argparse

    import projetos
    import variables as V
    ap = argparse.ArgumentParser(description="Carimba o modelo nas classificações antigas, a partir do llm_log")
    ap.add_argument("-p", "--projeto", required=True)
    ap.add_argument("qids", nargs="*")
    ap.add_argument("--aplicar", action="store_true", help="grava (sem isto só simula)")
    a = ap.parse_args()
    projetos.ativar(a.projeto)
    for qid in a.qids or V.perguntas_codificaveis():
        print(estimar(qid, aplicar=a.aplicar))


if __name__ == "__main__":
    _main()
