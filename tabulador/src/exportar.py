"""Planilha final no formato da planilha-fonte (projetos com SAIDA_PLANILHA em projeto.py).

Copia a aba da planilha-fonte e preenche as colunas de categoria (ex.: Q4_CAT) com o nome da
categoria PRINCIPAL de cada respondente; a secundária vai em <coluna>2 (ex.: Q4_CAT2), criada no fim
da aba. Só entram perguntas com classificação APROVADA. Uma aba 'Categorias' lista o frame de cada
pergunta e a situação. A planilha-fonte nunca é alterada.

Saída: <output do projeto>/<SAIDA_PLANILHA['arquivo']>
"""
from __future__ import annotations

import json
import subprocess
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

import codeframe as CF
import coding as CD
import config
import eventos
import variables as V


def disponivel() -> bool:
    return bool(V.SAIDA_PLANILHA)


def _commit() -> dict:
    """Commit do código que gerou a entrega e se havia alteração não commitada (reprodutibilidade)."""
    try:
        raiz = Path(__file__).resolve().parents[1]
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=raiz, capture_output=True, text=True, timeout=10).stdout.strip()
        sujo = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "app.py"], cwd=raiz, capture_output=True, text=True, timeout=10).stdout.strip())
        return {"commit": h or None, "codigo_com_alteracao_nao_commitada": sujo}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "codigo_com_alteracao_nao_commitada": None}


def _quadro_da_entrega(frame: dict, cod: dict, coluna: str, status: str | None, n: int) -> dict:
    itens = cod.get("itens") or []
    return {"coluna": coluna, "status": status, "respondentes": n, "frame_versao": int(frame.get("versao") or 1),
            "n_categorias": len(frame["categorias"]), "n_respostas": len(itens),
            "n_conferidas_por_pessoa": sum(1 for i in itens if i.get("origem") == "humano" or (i.get("validado") and i.get("validado_por") != "auto")),
            "n_aceitas_automaticamente": sum(1 for i in itens if i.get("validado_por") == "auto"),
            "classificado_por": dict(Counter(i.get("classificado_por") or "desconhecido" for i in itens if i.get("origem") in ("llm", "llm+comentario")))}


def _registrar_manifesto(planilha: Path, quadros: dict) -> None:
    """`entrega_manifesto.json` ao lado da planilha: uma entrada por geração. Responde 'com qual quadro saiu a
    entrega de dd/mm?'. O formato da planilha não muda."""
    try:
        arq = planilha.parent / "entrega_manifesto.json"
        historico = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
        historico.append({"gerado_em": datetime.now().isoformat(timespec="seconds"), "projeto": config.PROJETO,
                          "arquivo": planilha.name, **_commit(), "perguntas": quadros})
        arq.write_text(json.dumps(historico, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001 - o manifesto não pode impedir a entrega
        traceback.print_exc()
    eventos.registrar(None, "gerar_planilha", arquivo=planilha.name, perguntas={q: m["frame_versao"] for q, m in quadros.items()})


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
    quadros = {}  # por pergunta: com qual quadro e quais modelos saiu a entrega (manifesto, PEND-26)
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
        quadros[qid] = _quadro_da_entrega(frame, cod, col_cat, status, n)
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
    _registrar_manifesto(p, quadros)
    if verbose:
        for s in situacao:
            print(f"  {s['pergunta']}: {s['situacao']}")
        print(f"  -> {p}")
    return p
