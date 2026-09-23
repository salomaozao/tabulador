"""Rascunho do projeto.json a partir do perfil da planilha, SEM IA (regras fixas, sempre iguais).

Tudo o que dá para tirar dos dados vem preenchido: tipo de cada coluna, opções das fechadas
(copiadas literalmente), coluna de id, dados pessoais, filtro de cada aberta (deduzido de quem
respondeu), perguntas a categorizar (colunas *_CAT com cabeçalho destacado), NPS, planilha final.
Fica "PREENCHER" só no que não está nos dados: contexto da pesquisa e a conferência do pedido.
As deduções que merecem conferência vão para "_notas".
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

import variables as V
from . import perfil as PF

PREENCHER = "PREENCHER"
NOMES_ID = ("respondent_id", "id_respondente", "respondente_id", "id", "resp_id", "response_id")
META_PALAVRAS = ("collector", "coletor", "date", "data", "start", "end", "hora", "timestamp", "duration",
                 "duracao", "custom", "created", "modified")
SUFIXO_SAIDA = re.compile(r"^(?P<base>.+)_CAT2?$")
TAXA_DENTRO = 0.5   # valor entra na regra se >= 50% de quem o escolheu respondeu a aberta
TAXA_FORA = 0.2     # e nenhum valor de fora pode passar de 20%
COBERTURA = 0.9     # a regra precisa explicar >= 90% de quem respondeu a aberta
NPS_FAIXAS = [[0, 6, "Detratores (0-6)"], [7, 8, "Neutros (7-8)"], [9, 10, "Promotores (9-10)"]]


def _id_valido(coluna: str, usados: set) -> str:
    base = coluna if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", coluna) else (V.slug(coluna)[:30] or "V")
    ident, i = base, 2
    while ident in usados:
        ident, i = f"{base}_{i}", i + 1
    usados.add(ident)
    return ident


def _rotulo(c: dict) -> str:
    enun = (c.get("enunciado") or "").strip().split(" — ")[-1]  # em grades, só o item (sem o texto do bloco)
    if not enun:
        return c["coluna"]
    return enun if len(enun) <= 90 else enun[:87].rstrip() + "..."


def _coluna_id(cols: list[dict]) -> dict | None:
    for c in cols:
        if V.norm(c["coluna"]) in NOMES_ID and c["unico"]:
            return c
    for c in cols:
        if c["unico"] and c["numerica"] and c.get("inteira"):
            return c
    return None


def _niveis(c: dict) -> list:
    vals = [v for v, _ in c.get("valores", [])]
    if vals and sum(1 for v in vals if v[:1].isdigit()) >= 0.8 * len(vals):
        return sorted(vals, reverse=True)  # escalas numeradas ("5Muito satisfeito"...): da maior para a menor
    return vals  # demais: da mais para a menos frequente


def classificar(c: dict, tem_saida: bool, eh_id: bool) -> tuple[str, str]:
    """(tipo, motivo). Tipos extras do rascunho: 'vazia', 'pii', 'saida'."""
    n = V.norm(c["coluna"])
    if SUFIXO_SAIDA.match(c["coluna"]):
        return "saida", "coluna de categoria (_CAT) — é preenchida na planilha final"
    if c["n"] == 0:
        return "vazia", "coluna vazia"
    if eh_id:
        return "meta", "identificador do respondente"
    if c["pii"]:
        return "pii", f"dado pessoal ({c['pii']})"
    if c["data"] or set(re.split(r"[^a-z0-9]+", n)) & set(META_PALAVRAS):
        return "meta", "controle da coleta (data, coletor, campo personalizado)"
    if tem_saida:
        return "aberta", "tem coluna _CAT correspondente"
    if c["numerica"]:
        return "numerica", "só números"
    if c["distintos"] <= 30 or (c["distintos"] <= PF.MAX_VALORES and c["distintos"] <= 0.1 * c["n"] and c["len_medio"] < 50):
        return "unica", f"{c['distintos']} valores diferentes que se repetem"
    return "aberta", "texto livre e variado"


def deduzir_filtro(aberta: str, candidatos: list[tuple[str, str, pd.Series]], resp: pd.Series) -> dict | None:
    """Procura, entre as fechadas anteriores (da mais próxima para a mais distante), a pergunta que
    explica quem respondeu a aberta. candidatos = [(id, tipo, valores limpos)]."""
    total = int(resp.sum())
    if total < 5:
        return None
    for qid, tipo, s in candidatos:
        valido = s.notna()
        if (valido & resp).sum() < 0.9 * total:
            continue
        taxas = resp[valido].groupby(s[valido]).mean()
        dentro = [v for v, t in taxas.items() if t >= TAXA_DENTRO]
        fora = [v for v, t in taxas.items() if t < TAXA_DENTRO]
        if not dentro or not fora or max(taxas[v] for v in fora) > TAXA_FORA:
            continue
        if (resp & s.isin(dentro)).sum() < COBERTURA * total:
            continue
        if tipo == "numerica":
            observados = sorted(taxas.index)
            lo, hi = min(dentro), max(dentro)
            if all(v in dentro for v in observados if lo <= v <= hi):  # faixa contínua
                regra = {"pergunta": qid, "entre": [_n(lo), _n(hi)]}
                desc = f"{qid} entre {_n(lo)} e {_n(hi)}"
                abaixo, acima = [v for v in fora if v < lo], [v for v in fora if v > hi]
                if abaixo and acima:  # valores isolados do outro lado da faixa (ex.: nota 0 que não recebeu a pergunta)
                    isolados = min((abaixo, acima), key=lambda vs: int(s.isin(vs).sum()))
                    regra["_alerta"] = (f"quem marcou {', '.join(str(_n(v)) for v in isolados)} em {qid} não respondeu — "
                                        "confira se o questionário pulava esse valor ou se a faixa deveria incluí-lo")
            else:
                regra = {"pergunta": qid, "em": [_n(v) for v in sorted(dentro)]}
                desc = f"{qid} = " + " ou ".join(str(_n(v)) for v in sorted(dentro))
        else:
            regra = {"pergunta": qid, "em": sorted(dentro)}
            desc = f"{qid} = " + " ou ".join(sorted(dentro))
        return {"descricao": desc + f" (ou respondeu {aberta})", **regra, "ou_respondeu": aberta}
    return None


def _n(v):
    return int(v) if float(v).is_integer() else float(v)


def _pasta_relativa(planilha: Path, pasta: Path) -> str:
    try:
        return Path(planilha).resolve().relative_to(Path(pasta).resolve()).as_posix()
    except ValueError:
        return str(Path(planilha).resolve())


def gerar(perfil: dict, pasta, nome: str, cliente: str | None = None) -> dict:
    cols = perfil["colunas"]
    nomes = {c["coluna"] for c in cols}
    maioria = perfil.get("cor_maioria")
    col_id = _coluna_id(cols)
    notas: list[str] = []
    if not col_id:
        notas.append("Não achei coluna de id única e inteira: escolha uma em PLANO.id (a planilha final precisa dela).")

    bruto = PF.ler(perfil["planilha"], perfil["aba"])
    usados: set = set()
    perguntas, pii, anteriores = [], [], []  # anteriores: fechadas já vistas (para deduzir filtros)
    filtros: dict = {}
    saida_colunas: dict = {}
    ignoradas = []
    for c in cols:
        col = c["coluna"]
        saida = next((s for s in (f"{col}_CAT",) if s in nomes), None)
        tipo, motivo = classificar(c, bool(saida), col_id is not None and col == col_id["coluna"])
        if tipo == "vazia":
            ignoradas.append(col)
            continue
        if tipo == "saida":
            continue
        if tipo == "pii":
            pii.append(V.norm(col))
            notas.append(f"{col}: tratada como dado pessoal ({c['pii']}) — fica fora da base e da IA.")
            continue
        qid = "respondent_id" if col_id and col == col_id["coluna"] else _id_valido(col, usados)
        spec = {"id": qid, "tipo": tipo, "rotulo": _rotulo(c)}
        if qid != col:
            spec["coluna"] = col
        if tipo == "unica":
            spec["niveis"] = _niveis(c)
            anteriores.append((qid, tipo, PF.texto(bruto[col])))
        elif tipo == "numerica":
            if c.get("inteira") and c["min"] >= 0 and c["max"] == 10 and c["distintos"] >= 6:
                spec["nps"] = True
                notas.append(f"{qid}: números de 0 a 10 — marcada como NPS (confira).")
            anteriores.append((qid, tipo, PF.numero(bruto[col])))
        elif tipo == "aberta":
            resp = PF.texto(bruto[col]).notna()
            regra = deduzir_filtro(qid, list(reversed(anteriores)), resp)
            if regra:
                alerta = regra.pop("_alerta", None)
                if alerta:
                    notas.append(f"{qid}: {alerta}.")
                nome_f = f"base_{qid}"
                filtros[nome_f] = regra
                spec["base"] = nome_f
                notas.append(f"{qid}: filtro deduzido dos dados — {regra['descricao']}. Confira com o questionário.")
            if saida:
                destacada = maioria is not None and _cor_de(cols, saida) not in (None, maioria)
                algum_destaque = any(_cor_de(cols, s) not in (None, maioria) for s in nomes if SUFIXO_SAIDA.match(s))
                spec["codificar"] = destacada or not algum_destaque
                if not spec["codificar"]:
                    notas.append(f"{qid}: existe {saida}, mas o cabeçalho NÃO está destacado como os outros _CAT — "
                                 "ficou fora da categorização. Confirme com quem pediu.")
            else:
                spec["codificar"] = True
                notas.append(f"{qid}: aberta sem coluna _CAT na planilha — marcada para categorizar (confirme).")
            if spec["codificar"]:
                spec["instrucoes_frame"] = ""
                saida_colunas[qid] = saida or f"{col}_CAT"
        perguntas.append(spec)
    if ignoradas:
        notas.append(f"Colunas vazias ignoradas: {', '.join(ignoradas)}.")

    derivadas, banners = {}, []
    nps = next((p for p in perguntas if p.get("nps")), None)
    if nps:
        derivadas["NPS_GRUPO"] = {"rotulo": "Grupo NPS", "origem": nps["id"], "faixas": NPS_FAIXAS,
                                  "niveis": [NPS_FAIXAS[2][2], NPS_FAIXAS[1][2], NPS_FAIXAS[0][2]]}
        banners.append("NPS_GRUPO")
    planilha = Path(perfil["planilha"])
    return {
        "_notas": notas,
        "NOME": nome,
        "CLIENTE": cliente or nome,
        "FORMATO": "plano",
        "FONTE_XLSX": _pasta_relativa(planilha, pasta),
        "PLANO": {"aba": perfil["aba"], "aba_codebook": perfil.get("aba_codebook"),
                  "id": col_id["coluna"] if col_id else PREENCHER},
        "PII_MATCH": pii,
        "CONTEXTO_PROJETO": PREENCHER,
        "FILTROS": filtros,
        "PERGUNTAS": perguntas,
        "DERIVADAS": derivadas,
        "BANNERS_PADRAO": banners,
        "SAIDA_PLANILHA": {"arquivo": f"{planilha.stem}_categorizada.xlsx", "aba": perfil["aba"],
                           "id": col_id["coluna"] if col_id else PREENCHER, "colunas": saida_colunas},
        "CONFERENCIA": {"responsavel": PREENCHER, "data": PREENCHER, "origem_pedido": PREENCHER,
                        "abertas_pedidas": []},
    }


def _cor_de(cols: list[dict], coluna: str):
    return next((c["cor"] for c in cols if c["coluna"] == coluna), None)
