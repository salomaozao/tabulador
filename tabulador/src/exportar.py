"""Planilha final no formato da planilha-fonte (projetos com SAIDA_PLANILHA em projeto.py).

Copia a aba da planilha-fonte e preenche as colunas de categoria (ex.: Q4_CAT) com o nome da
categoria PRINCIPAL de cada respondente; a secundária vai em <coluna>2 (ex.: Q4_CAT2), criada no fim
da aba. Só entram perguntas com classificação APROVADA. Uma aba 'Categorias' lista o frame de cada
pergunta e a situação. A planilha-fonte nunca é alterada.

Saída: <output do projeto>/<SAIDA_PLANILHA['arquivo']>
"""
from __future__ import annotations

from datetime import datetime

import openpyxl
from openpyxl.styles import Font

import codeframe as CF
import coding as CD
import config
import variables as V


def disponivel() -> bool:
    return bool(V.SAIDA_PLANILHA)


def gerar(incluir_rascunho: bool = False, verbose: bool = True):
    S = V.SAIDA_PLANILHA
    if not S:
        raise RuntimeError("Este projeto não define SAIDA_PLANILHA em projeto.py")
    wb = openpyxl.load_workbook(config.FONTE_XLSX)
    ws = wb[S.get("aba", wb.sheetnames[0])]
    cab = {str(c.value): c.column for c in ws[1] if c.value is not None}
    col_id = cab.get(S.get("id", "respondent_id"))
    if not col_id:
        raise KeyError(f"coluna {S.get('id')} não encontrada na aba {ws.title}")
    linha_de = {}
    for r in range(2, ws.max_row + 1):
        v = ws.cell(row=r, column=col_id).value
        if v is not None:
            try:
                linha_de[int(v)] = r
            except (TypeError, ValueError):
                continue
    situacao = []
    prox_col = ws.max_column + 1
    for qid, col_cat in S["colunas"].items():
        frame = CF.frame(qid)
        cod = CD.codificacao(qid)
        status = (cod or {}).get("status")
        if not frame or not cod or (status != "aprovado" and not incluir_rascunho):
            situacao.append({"pergunta": qid, "coluna": col_cat, "situacao": "não incluída (classificação não aprovada)" if cod else "não incluída (não classificada)"})
            continue
        nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
        c1 = cab.get(col_cat)
        if not c1:
            c1 = prox_col
            ws.cell(row=1, column=c1, value=col_cat).font = Font(bold=True)
            prox_col += 1
        col_cod1 = f"{col_cat}_COD"
        c_cod1 = cab.get(col_cod1)
        if not c_cod1:
            c_cod1 = prox_col
            ws.cell(row=1, column=c_cod1, value=col_cod1).font = Font(bold=True)
            cab[col_cod1] = c_cod1
            prox_col += 1
        col2 = f"{col_cat}2"
        c2 = cab.get(col2)
        if not c2:
            c2 = prox_col
            ws.cell(row=1, column=c2, value=col2).font = Font(bold=True)
            cab[col2] = c2
            prox_col += 1
        col_cod2 = f"{col_cat}2_COD"
        c_cod2 = cab.get(col_cod2)
        if not c_cod2:
            c_cod2 = prox_col
            ws.cell(row=1, column=c_cod2, value=col_cod2).font = Font(bold=True)
            cab[col_cod2] = c_cod2
            prox_col += 1
        n = 0
        for rid, v in CD.mapa_respondentes(qid).items():
            r = linha_de.get(int(rid))
            if not r:
                continue
            ws.cell(row=r, column=c1, value=nomes.get(v["primaria"]))
            ws.cell(row=r, column=c_cod1, value=v["primaria"])
            ws.cell(row=r, column=c2, value=nomes.get(v["secundaria"]) if v["secundaria"] is not None else None)
            ws.cell(row=r, column=c_cod2, value=v["secundaria"] if v["secundaria"] is not None else None)
            n += 1
        situacao.append({"pergunta": qid, "coluna": col_cat, "situacao": f"incluída ({status}) · {n} respondentes"})
    # aba de legenda
    if "Categorias" in wb.sheetnames:
        del wb["Categorias"]
    wl = wb.create_sheet("Categorias")
    wl.append([f"Categorização — {config.NOME_PROJETO} — gerado em {datetime.now():%d/%m/%Y %H:%M}"])
    wl.append([])
    wl.append(["pergunta", "coluna", "situação", "código", "categoria", "definição"])
    for c in wl[3]:
        c.font = Font(bold=True)
    for s in situacao:
        frame = CF.frame(s["pergunta"])
        wl.append([s["pergunta"], s["coluna"], s["situacao"]])
        if frame and s["situacao"].startswith("incluída"):
            for c in frame["categorias"]:
                wl.append(["", "", "", c["codigo"], c["nome"], c["definicao"]])
    for letra, larg in {"A": 12, "B": 12, "C": 44, "D": 8, "E": 34, "F": 90}.items():
        wl.column_dimensions[letra].width = larg
    config.garantir_pastas()
    p = config.OUTPUT_DIR / S.get("arquivo", "planilha_categorizada.xlsx")
    wb.save(p)
    if verbose:
        for s in situacao:
            print(f"  {s['pergunta']}: {s['situacao']}")
        print(f"  -> {p}")
    return p
