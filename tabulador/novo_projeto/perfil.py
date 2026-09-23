"""Perfil da planilha-fonte: o que existe em cada coluna, lido com a MESMA limpeza do pipeline
(load.limpar_texto / load._to_num), para que o rascunho e o validador vejam exatamente os valores
que o tabulador vai ver.

É a fonte de verdade para quem monta o projeto (pessoa ou IA): valores das fechadas copiados
literalmente, contagens, cor de fundo do cabeçalho (o cliente costuma destacar as colunas a
categorizar) e suspeita de dado pessoal. Colunas com dado pessoal não têm amostra de valores; as
abertas têm só 3 exemplos curtos.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import openpyxl
import pandas as pd

import load
import variables as V

MAX_VALORES = 60  # fechadas: lista completa de valores até este limite
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
RE_IP = re.compile(r"\d{1,3}(\.\d{1,3}){3}")
RE_FONE = re.compile(r"\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}")
# nomes de coluna que indicam dado pessoal (comparados por palavra, sem acento)
PII_PALAVRAS = {"email", "mail", "nome", "name", "telefone", "celular", "whatsapp", "whatsap", "fone",
                "phone", "cpf", "rg", "endereco", "address", "ip"}
PII_NOMES = {"ip_address", "email_address", "first_name", "last_name", "e-mail", "nome completo"}


def ler(planilha, aba=0) -> pd.DataFrame:
    return pd.read_excel(planilha, sheet_name=aba)


def texto(s: pd.Series) -> pd.Series:
    """Como o pipeline guarda abertas e fechadas (limpar_texto; vazio -> None)."""
    return s.map(lambda v: None if pd.isna(v) else load.limpar_texto(v))


def numero(s: pd.Series) -> pd.Series:
    """Como o pipeline guarda numéricas (_to_num; NS/NR e texto -> NaN)."""
    return s.map(lambda v: float("nan") if pd.isna(v) else load._to_num(v))


def _cor(celula) -> str | None:
    f = getattr(celula, "fill", None)
    if not f or not f.fill_type:
        return None
    c = f.fgColor
    if c is None:
        return None
    if c.type == "rgb" and isinstance(c.rgb, str):
        return c.rgb.upper()
    if c.type == "theme":
        return f"tema{c.theme}{c.tint:+.2f}"
    if c.type == "indexed":
        return f"indice{c.indexed}"
    return None


def cores_cabecalho(planilha, aba) -> list[str | None]:
    """Cor de fundo de cada célula do cabeçalho (linha 1), na ordem das colunas."""
    try:
        wb = openpyxl.load_workbook(planilha, read_only=True)
        ws = wb[aba] if isinstance(aba, str) else wb.worksheets[aba]
        linha = next(ws.iter_rows(min_row=1, max_row=1))
        cores = [_cor(c) for c in linha]
        wb.close()
        return cores
    except Exception:  # cor é só uma pista; sem ela o perfil continua
        return []


def cor_maioria(cores: list[str | None]) -> str | None:
    cont = Counter(cores)
    return cont.most_common(1)[0][0] if cont else None


def pii_por_nome(coluna: str) -> bool:
    n = V.norm(coluna)
    if n in PII_NOMES:
        return True
    return bool(set(re.split(r"[^a-z0-9]+", n)) & PII_PALAVRAS)


def pii_por_conteudo(valores: list[str]) -> str | None:
    """Motivo, se >= 30% dos valores têm cara de e-mail, CPF, IP ou telefone."""
    if not valores:
        return None
    amostra = valores[:500]
    for nome, rx in (("e-mail", RE_EMAIL), ("CPF", RE_CPF), ("IP", RE_IP), ("telefone", RE_FONE)):
        if sum(1 for v in amostra if rx.fullmatch(v.strip())) >= 0.3 * len(amostra):
            return nome
    return None


def dados_pessoais_no_texto(valores: list[str]) -> int:
    """Quantas respostas abertas trazem e-mail ou telefone no meio do texto."""
    return sum(1 for v in valores if RE_EMAIL.search(v) or RE_FONE.search(v))


def abas(planilha) -> list[str]:
    return list(pd.ExcelFile(planilha).sheet_names)


def aba_codebook(nomes: list[str]) -> str | None:
    for a in nomes:
        n = V.norm(a)
        if any(k in n for k in ("codebook", "dicionario", "questionario", "enunciado")):
            return a
    return None


def perfilar(planilha, aba=None) -> dict:
    planilha = Path(planilha)
    todas = abas(planilha)
    aba = aba if aba is not None else todas[0]
    cb = aba_codebook([a for a in todas if a != aba])
    bruto = ler(planilha, aba)
    enunciados = load._enunciados_codebook(cb, fonte=planilha) if cb else {}
    cores = cores_cabecalho(planilha, aba)
    colunas = []
    for i, col in enumerate(bruto.columns):
        s = bruto[col]
        t = texto(s)
        vals = [v for v in t if isinstance(v, str)]  # map pode devolver NaN no lugar de None
        num = numero(s)
        n = len(vals)
        eh_data = pd.api.types.is_datetime64_any_dtype(s) or (n > 0 and all(isinstance(v, (datetime, date)) for v in s.dropna().head(50)))
        nsnr = sum(1 for v in vals if load._NSNR_RE.match(v))  # NS/NR vira vazio nas numéricas (de propósito)
        numerica = n > nsnr and not eh_data and int(num.notna().sum()) == n - nsnr
        info = {
            "pos": i, "coluna": str(col), "cor": cores[i] if i < len(cores) else None,
            "enunciado": enunciados.get(str(col)), "n": n, "distintos": len(set(vals)),
            "numerica": numerica, "data": bool(eh_data),
            "len_medio": round(sum(len(v) for v in vals) / n, 1) if n else 0,
            "pii": ("nome da coluna" if pii_por_nome(str(col)) else None) or (None if numerica else pii_por_conteudo(vals)),
            "unico": n == len(bruto) and len(set(vals)) == n,
        }
        if numerica:
            nn = num.dropna()
            info.update({"min": float(nn.min()), "max": float(nn.max()), "inteira": bool((nn % 1 == 0).all())})
        if info["pii"]:
            pass  # sem amostra de dado pessoal
        elif info["distintos"] <= MAX_VALORES:
            info["valores"] = [[v, c] for v, c in Counter(vals).most_common()]
        else:
            info["exemplos"] = [v[:80] for v in vals[:3]]
            info["dados_pessoais_no_texto"] = dados_pessoais_no_texto(vals)
        colunas.append(info)
    return {
        "planilha": str(planilha), "aba": aba, "abas": todas, "aba_codebook": cb, "n_linhas": len(bruto),
        "cor_maioria": cor_maioria(cores), "colunas": colunas,
    }


def resumo(perfil: dict) -> str:
    """Texto curto para mostrar à pessoa (ou ler na skill)."""
    linhas = [f"Planilha: {perfil['planilha']} · aba {perfil['aba']!r} · {perfil['n_linhas']} linhas"
              + (f" · enunciados na aba {perfil['aba_codebook']!r}" if perfil["aba_codebook"] else "")]
    for c in perfil["colunas"]:
        if c["n"] == 0:
            continue
        marca = "🔒 dado pessoal" if c["pii"] else ("número" if c["numerica"] else "data" if c["data"] else "texto")
        destaque = " · cabeçalho destacado" if c["cor"] and c["cor"] != perfil["cor_maioria"] else ""
        linhas.append(f"  {c['coluna']}: {marca} · {c['n']} preenchidas · {c['distintos']} distintos{destaque}")
    return "\n".join(linhas)
