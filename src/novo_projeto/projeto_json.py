"""Projeto declarativo (`projeto.json`): o mesmo conteúdo de um `projeto.py`, sem código.

Diferenças em relação ao projeto.py:
  - FONTE_XLSX (e OUTPUT_DIR) podem ser relativos à pasta do projeto;
  - FILTROS são regras, não funções:
        {"descricao": "Deram nota 0 a 7 (Q3)", "pergunta": "Q3", "entre": [0, 7], "ou_respondeu": "Q4"}
        {"descricao": "...", "pergunta": "Q28", "em": ["Superiores", "Muito superiores."]}
        {"descricao": "Todos os respondentes", "todos": true}
    "ou_respondeu" (id ou lista de ids) mantém na base quem respondeu a pergunta mesmo fora da regra,
    para nenhuma resposta ser descartada. O filtro "todos" é criado se não existir;
  - só chaves em MAIÚSCULAS viram configuração (as demais, como "_notas", são ignoradas).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

TODOS = {"descricao": "Todos os respondentes", "todos": True}


def compilar_filtro(regra: dict):
    """Regra declarativa -> função df -> máscara booleana (sobre os ids das perguntas)."""
    ou = regra.get("ou_respondeu") or []
    ou = [ou] if isinstance(ou, str) else list(ou)

    def filtro(df: pd.DataFrame) -> pd.Series:
        if regra.get("todos"):
            m = df["respondent_id"].notna()
        else:
            s = df[regra["pergunta"]]
            if "entre" in regra:
                lo, hi = regra["entre"]
                m = pd.to_numeric(s, errors="coerce").between(lo, hi)
            elif "em" in regra:
                m = s.isin(regra["em"])
            else:
                raise ValueError(f"regra de filtro sem 'entre', 'em' ou 'todos': {regra}")
        for q in ou:
            m = m | df[q].notna()
        return m

    return filtro


def descrever(regra: dict) -> str:
    if regra.get("descricao"):
        return regra["descricao"]
    if regra.get("todos"):
        return TODOS["descricao"]
    if "entre" in regra:
        return f"{regra['pergunta']} entre {regra['entre'][0]} e {regra['entre'][1]}"
    return f"{regra['pergunta']} = " + " ou ".join(map(str, regra.get("em", [])))


def ler(arq: Path) -> dict:
    return json.loads(Path(arq).read_text(encoding="utf-8"))


def carregar(arq: Path) -> SimpleNamespace:
    """Lê o projeto.json e devolve um objeto com os mesmos nomes de um projeto.py."""
    arq = Path(arq).resolve()
    d = ler(arq)
    pasta = arq.parent
    ns = SimpleNamespace(**{k: v for k, v in d.items() if k.isupper()})
    ns.__file__ = str(arq)
    for chave in ("FONTE_XLSX", "OUTPUT_DIR", "ENV_EXTRA"):
        if getattr(ns, chave, None):
            p = Path(getattr(ns, chave))
            setattr(ns, chave, p if p.is_absolute() else (pasta / p).resolve())
    regras = {"todos": TODOS, **d.get("FILTROS", {})}
    ns.FILTROS_REGRAS = regras
    ns.FILTROS = {k: compilar_filtro(r) for k, r in regras.items()}
    ns.FILTROS_DESCRICAO = {k: descrever(r) for k, r in regras.items()}
    for der in getattr(ns, "DERIVADAS", {}).values():
        if "faixas" in der:
            der["faixas"] = [tuple(f) for f in der["faixas"]]
    return ns
