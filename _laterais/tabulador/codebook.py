"""Codebook executivo gerado a partir do mapa canônico + base processada.

Saídas (output/codebook/):
  codebook.xlsx - abas: Perguntas (uma linha por variável/pergunta), Valores (distribuição de cada
                  categoria/item), Derivadas (definição dos banners), Code frames (abertas codificadas)
  codebook.html - a mesma informação em página única para leitura rápida
"""
from __future__ import annotations

import html
import json
from datetime import datetime

import pandas as pd

import codeframe as CF
import config
import load
import variables as V

TIPO_DESC = {
    "meta": "Identificação / controle",
    "unica": "Resposta única (RU)",
    "aberta": "Aberta (texto)",
    "dicotomica": "Múltipla escolha - item (0/1)",
    "numerica": "Numérica",
    "codificada": "Aberta codificada (código)",
    "codificada_nome": "Aberta codificada (rótulo)",
    "derivada": "Derivada (banner)",
}


def _origem(ent: dict) -> str:
    o = ent.get("origem") or {}
    partes = []
    for aba, d in o.items():
        if isinstance(d, dict) and "coluna" in d:
            rot = "auto" if "autopre" in aba else "tel" if "pesquisador" in aba else aba
            partes.append(f"{rot}: col {d['coluna']}")
        else:
            partes.append(f"{aba}: {d}")
    return " | ".join(partes)


def montar(df: pd.DataFrame, registro: dict) -> dict[str, pd.DataFrame]:
    perguntas, valores, frames = [], [], []
    for var, ent in registro.items():
        tipo = ent.get("tipo")
        if tipo in ("codificada_nome",):
            continue
        s = df[var] if var in df.columns else pd.Series(dtype=object)
        base = ent.get("base") or "todos"
        n_base = int(V.FILTROS[base](df).sum()) if base in V.FILTROS else len(df)
        n_valid = int(s.notna().sum())
        perguntas.append({
            "variavel": var,
            "pergunta": ent.get("pergunta") or "",
            "tipo": TIPO_DESC.get(tipo, tipo),
            "rotulo": ent.get("rotulo"),
            "enunciado": ent.get("enunciado") or "",
            "item/opcao": ent.get("opcao") or "",
            "base": V.FILTROS_DESCRICAO.get(base, base),
            "n base": n_base,
            "n validos": n_valid,
            "origem (coluna na planilha)": _origem(ent),
        })
        if tipo in ("unica", "derivada"):
            vc = s.value_counts(dropna=False)
            niveis = ent.get("niveis") or [v for v in vc.index if pd.notna(v)]
            niveis = list(niveis) + [v for v in vc.index if pd.notna(v) and v not in niveis]
            for niv in niveis:
                n = int(vc.get(niv, 0))
                valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": niv, "n": n, "%": n / n_valid if n_valid else None})
            n_na = int(s.isna().sum())
            if n_na:
                valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": "(sem resposta / fora da base)", "n": n_na, "%": None})
        elif tipo == "dicotomica":
            n = int(s.eq(1).sum())
            valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": f"1 = marcou '{ent.get('opcao')}'", "n": n, "%": n / n_valid if n_valid else None})
        elif tipo == "numerica":
            sn = pd.to_numeric(s, errors="coerce")
            valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": f"min {sn.min():g} · máx {sn.max():g} · média {sn.mean():.2f}" if n_valid else "sem dados", "n": n_valid, "%": None})
        elif tipo == "codificada":
            for c in ent.get("frame") or []:
                n = int(s.eq(c["codigo"]).sum())
                valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": f"{c['codigo']} = {c['nome']}", "n": n, "%": n / n_valid if n_valid else None})
        elif tipo == "aberta":
            valores.append({"variavel": var, "rotulo": ent.get("rotulo"), "valor": "texto livre", "n": n_valid, "%": None})

    derivadas = []
    for nome, d in V.DERIVADAS.items():
        if "mapa" in d and d["mapa"]:
            regra = "; ".join(f"{k} → {v}" for k, v in d["mapa"].items())
        elif "faixas" in d:
            regra = "; ".join(f"{lo}-{hi} → {rot}" for lo, hi, rot in d["faixas"])
        elif "backcoding" in d:
            bc = V.BACKCODING[d["backcoding"]]
            regra = "; ".join(f"{k} → {v}" for k, v in bc["fechados"].items()) + f" | 'Outro. Qual?' back-codificado via {d['backcoding']} (" + \
                    "; ".join(f"{c['codigo']} {c['nome']} → {bc['mapa_banner'][c['codigo']]}" for c in bc["frame"]) + ")"
        else:
            regra = "cópia da variável de origem"
        derivadas.append({"banner": nome, "rotulo": d["rotulo"], "origem": d["origem"], "niveis": " | ".join(d["niveis"]), "regra": regra})

    for qid in V.perguntas_codificaveis():
        f = CF.frame(qid)
        if not f:
            continue
        for c in f["categorias"]:
            frames.append({"pergunta": qid, "rotulo": V.por_id(qid)["rotulo"], "status frame": f["status"], "codigo": c["codigo"],
                           "categoria": c["nome"], "definicao": c["definicao"], "exemplos": "; ".join(c.get("exemplos") or [])})

    return {
        "Perguntas": pd.DataFrame(perguntas),
        "Valores": pd.DataFrame(valores),
        "Derivadas": pd.DataFrame(derivadas),
        "Code frames": pd.DataFrame(frames),
    }


def _html(abas: dict[str, pd.DataFrame], n: int) -> str:
    css = ("body{font:13px/1.4 system-ui,sans-serif;margin:24px;color:#111;background:#fff}h1{font-size:20px}h2{font-size:16px;margin-top:32px}"
           "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f1f0ee;position:sticky;top:0}"
           "td.num{text-align:right}@media(prefers-color-scheme:dark){body{background:#1a1a19;color:#eee}th{background:#2a2a29}th,td{border-color:#444}}")
    partes = [f"<h1>Codebook — {html.escape(config.NOME_PROJETO)} (N={n})</h1><p>Gerado em {datetime.now():%d/%m/%Y %H:%M}</p>"]
    for nome, dfx in abas.items():
        partes.append(f"<h2>{html.escape(nome)}</h2>")
        d2 = dfx.copy()
        if "%" in d2.columns:
            d2["%"] = d2["%"].map(lambda v: "" if v is None or pd.isna(v) else f"{100 * v:.0f}%")
        partes.append(d2.to_html(index=False, escape=True, na_rep="", border=0))
    return f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Codebook {html.escape(config.NOME_PROJETO)}</title><style>{css}</style></head><body>{''.join(partes)}</body></html>"


def gerar(verbose: bool = True):
    df, registro = load.carregar_base()
    abas = montar(df, registro)
    config.garantir_pastas()
    p = config.CODEBOOK_OUT / "codebook.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        for nome, dfx in abas.items():
            dfx.to_excel(xw, sheet_name=nome, index=False)
            ws = xw.sheets[nome]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                letra = col[0].column_letter
                largura = max(10, min(70, max((len(str(c.value)) for c in col if c.value is not None), default=10) + 2))
                ws.column_dimensions[letra].width = largura
            if "%" in dfx.columns:
                idx = list(dfx.columns).index("%") + 1
                for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                    row[0].number_format = "0%"
    (config.CODEBOOK_OUT / "codebook.html").write_text(_html(abas, len(df)), encoding="utf-8")
    if verbose:
        print(f"  codebook: {len(abas['Perguntas'])} variáveis, {len(abas['Valores'])} valores -> {p}")
    return p


if __name__ == "__main__":
    gerar()
