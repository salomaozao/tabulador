"""Perfil de quem citou cada categoria (janela de aprovação por categoria).

Compara quem citou a categoria com TODOS que responderam a mesma pergunta (a base da pergunta, não
o total da pesquisa: na Q4, por exemplo, só respondeu quem deu nota até 7). Usa as perguntas
numéricas/de escala do projeto, sem mapear categoria a atributo à mão:
  - NPS (nota 0-10): média, % promotores (9-10), % detratores (0-6);
  - satisfação geral (escala): média de 1 a 5;
  - retenção: % no nível de risco (ex.: "Pode trocar");
  - grupo (ex.: escola): os que aparecem acima do esperado;
  - atributos (escalas de satisfação por tema): os que quem citou avalia PIOR que a base.

Configuração opcional no projeto.py:
  PERFIL = {"nps": "Q3", "satisfacao": "Q34", "retencao": ("RETENCAO2", "Pode trocar"),
            "grupo": "ESCOLA", "atributos": ["Q6", ..., "Q26"]}
Sem ela, usa a numérica marcada com "nps": True e não mostra os demais blocos.
"""
from __future__ import annotations

import re

import pandas as pd

import codeframe as CF
import coding as CD
import load
import variables as V

MIN_N = 10          # abaixo disso o perfil é mostrado com aviso de base pequena
MIN_N_GRUPO = 5     # escola precisa de pelo menos 5 menções na categoria para aparecer
_NAO_SABE = re.compile(r"n[ãa]o (sei|sabe|se aplica|tenho base)", re.I)


def _config() -> dict:
    cfg = dict(getattr(V._p(), "PERFIL", {}) or {})
    if not cfg.get("nps"):
        nps = next((p["id"] for p in V._p().PERGUNTAS if p.get("nps")), None)
        if nps:
            cfg["nps"] = nps
    return cfg


def _nota_escala(qid: str, serie: pd.Series) -> pd.Series:
    """Converte uma escala (lista de níveis, do melhor para o pior) em nota: melhor = nº de níveis."""
    niveis = [n for n in (V.por_id(qid).get("niveis") or []) if not _NAO_SABE.search(n)]
    nota = {n: len(niveis) - k for k, n in enumerate(niveis)}
    return serie.map(nota).astype(float)


def _media(s: pd.Series) -> float | None:
    s = s.dropna()
    return round(float(s.mean()), 2) if len(s) else None


def _pct(mask: pd.Series) -> float | None:
    return round(100 * float(mask.mean()), 1) if len(mask) else None


def _bloco(df: pd.DataFrame, cfg: dict) -> dict:
    """Indicadores de um grupo de respondentes (df já filtrado)."""
    out: dict = {"n": int(len(df))}
    if cfg.get("nps") and cfg["nps"] in df:
        nota = pd.to_numeric(df[cfg["nps"]], errors="coerce").dropna()
        if len(nota):
            prom, detr = _pct(nota >= 9), _pct(nota <= 6)
            out["nps"] = {"media": _media(nota), "promotores": prom, "detratores": detr, "nps": round(prom - detr, 1)}
    if cfg.get("satisfacao") and cfg["satisfacao"] in df:
        out["satisfacao"] = _media(_nota_escala(cfg["satisfacao"], df[cfg["satisfacao"]]))
    ret = cfg.get("retencao")
    if ret and ret[0] in df:
        validos = df[ret[0]].dropna()
        out["retencao_risco"] = _pct(validos == ret[1]) if len(validos) else None
    return out


def perfil(qid: str) -> dict:
    """Uma entrada por categoria: contagens, exemplos, pendentes e o perfil vs. a base da pergunta."""
    frame = CF._exigir_frame(qid)
    cod = CD.codificacao(qid)
    cfg = _config()
    cats = [c for c in frame["categorias"]]
    if not cod:  # antes de classificar: só definição e exemplos da IA
        return {"qid": qid, "classificada": False, "config": _rotulos(cfg),
                "categorias": [{"codigo": c["codigo"], "nome": c["nome"], "definicao": c.get("definicao", ""),
                                "fixa": bool(c.get("fixa")), "exemplos": (c.get("exemplos") or [])[:5]} for c in cats]}
    df, _ = load.carregar_base()
    df = df.set_index("respondent_id", drop=False)
    resp = {r["rid"]: r for r in CF.respostas(qid)["respostas"]}
    itens = [i for i in cod["itens"] if i.get("primaria") is not None and i["rid"] in resp]
    ids_base = [i for r in resp.values() for i in r["respondent_ids"] if i in df.index]
    base = df.loc[ids_base]
    atributos = [a for a in cfg.get("atributos", []) if a in df]
    notas_base = {a: _nota_escala(a, base[a]) for a in atributos}
    grupo = cfg.get("grupo") if cfg.get("grupo") in df else None
    dist_grupo = base[grupo].value_counts(normalize=True) if grupo else None
    saida = {"qid": qid, "classificada": True, "config": _rotulos(cfg), "base": _bloco(base, cfg), "categorias": []}
    total_classificados = sum(resp[i["rid"]]["n"] for i in itens)
    for c in cats:
        k = c["codigo"]
        seus = [i for i in itens if k in (i.get("primaria"), i.get("secundaria"))]
        ids = [rid for i in seus for rid in resp[i["rid"]]["respondent_ids"] if rid in df.index]
        a_conferir = [i for i in seus if i.get("primaria") == k and not i.get("validado") and i.get("origem") != "humano"]
        # confirmação em bloco nunca passa por cima de uma discordância do auditor: essas ficam para olhar uma a uma
        pend = [i for i in a_conferir if (i.get("auditoria") or {}).get("ok") is not False]
        exemplos = sorted((i for i in seus if i.get("primaria") == k), key=lambda i: -resp[i["rid"]]["n"])[:5]
        cat = {"codigo": k, "nome": c["nome"], "definicao": c.get("definicao", ""), "fixa": bool(c.get("fixa")),
               "n": len(set(ids)), "pct": round(100 * len(set(ids)) / total_classificados, 1) if total_classificados else None,
               "exemplos": [{"texto": resp[i["rid"]]["texto"], "n": resp[i["rid"]]["n"]} for i in exemplos],
               "pendentes": [i["rid"] for i in pend],
               "com_sugestao": len(a_conferir) - len(pend),
               "menor_confianca": [{"rid": i["rid"], "texto": resp[i["rid"]]["texto"], "confianca": i.get("confianca")}
                                   for i in sorted(pend, key=lambda i: i.get("confianca") or 0)[:3]]}
        if ids:
            sub = df.loc[ids]
            cat["perfil"] = _bloco(sub, cfg)
            if grupo and len(sub) >= MIN_N_GRUPO:
                dist = sub[grupo].value_counts()
                acima = [(g, int(n), n / len(sub), dist_grupo.get(g, 0)) for g, n in dist.items() if n >= MIN_N_GRUPO]
                acima = sorted((a for a in acima if a[2] > a[3]), key=lambda a: -(a[2] / a[3] if a[3] else 99))[:3]
                cat["grupos_acima"] = [{"nome": g, "n": n, "pct": round(100 * p, 1), "pct_base": round(100 * pb, 1)} for g, n, p, pb in acima]
            if atributos and len(sub) >= MIN_N:
                difs = []
                for a in atributos:
                    m, mb = _media(_nota_escala(a, sub[a])), _media(notas_base[a])
                    if m is not None and mb is not None:
                        difs.append({"id": a, "rotulo": V.por_id(a).get("rotulo", a), "media": m, "media_base": mb, "dif": round(m - mb, 2)})
                cat["atributos_piores"] = sorted((d for d in difs if d["dif"] < 0), key=lambda d: d["dif"])[:3]
        saida["categorias"].append(cat)
    return saida


def _rotulos(cfg: dict) -> dict:
    def rot(q):
        return V.por_id(q).get("rotulo", q) if q else None
    ret = cfg.get("retencao")
    return {"nps": rot(cfg.get("nps")), "satisfacao": rot(cfg.get("satisfacao")),
            "retencao": f"{ret[1]}" if ret else None, "grupo": rot(cfg.get("grupo")) if cfg.get("grupo") else None,
            "atributos": bool(cfg.get("atributos"))}
