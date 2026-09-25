"""Validação de um projeto (projeto.json ou projeto.py, formato "plano") contra a planilha real.

Roda a leitura do pipeline de verdade (load.executar) numa pasta temporária e compara com a planilha
lida pela mesma limpeza. ERROS bloqueiam o registro do projeto; AVISOS pedem só ciência.

Principais erros: campo "PREENCHER" restante; coluna declarada inexistente; id vazio, repetido ou não
inteiro (a planilha final usa o id como número); valor da planilha fora das opções declaradas;
resposta aberta perdida (por filtro ou conversão); número perdido na conversão; dado pessoal
declarado como pergunta; derivada ou banner inconsistente; conferência do pedido ausente ou com
lista de abertas diferente da marcada para categorizar.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import threading
from pathlib import Path

import pandas as pd

import load
from . import perfil as PF
from . import projeto_json

PREENCHER = "PREENCHER"
TIPOS_PLANO = {"meta", "unica", "aberta", "numerica"}
SLUG_VALIDACAO = "__validacao__"
_trava = threading.Lock()


def arquivo_projeto(pasta: Path) -> Path | None:
    for sub in ("", "src", "codigo"):
        for nome in ("projeto.py", "projeto.json"):
            alvo = pasta / sub / nome if sub else pasta / nome
            if alvo.exists():
                return alvo
    return None


def carregar_modulo(arq: Path):
    if arq.is_dir():
        p = arquivo_projeto(arq)
        if not p:
            raise FileNotFoundError(f"Nenhum arquivo de projeto encontrado em {arq}")
        arq = p
    elif not arq.exists():
        for sub in ("src", "codigo"):
            alt = arq.parent / sub / arq.name
            if alt.exists():
                arq = alt
                break
    if arq.suffix == ".json":
        return projeto_json.carregar(arq)
    spec = importlib.util.spec_from_file_location("projeto_em_validacao", arq)
    mod = importlib.util.module_from_spec(spec)
    antes, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = antes
    return mod


def _preencher_restantes(obj, caminho="") -> list[str]:
    if isinstance(obj, dict):
        return [c for k, v in obj.items() if not str(k).startswith("_") for c in _preencher_restantes(v, f"{caminho}.{k}" if caminho else str(k))]
    if isinstance(obj, list):
        if obj == [] and caminho.endswith("abertas_pedidas"):
            return []
        return [c for i, v in enumerate(obj) for c in _preencher_restantes(v, f"{caminho}[{i}]")]
    return [caminho] if isinstance(obj, str) and PREENCHER in obj else []


def _estrutura(mod, erros: list, avisos: list) -> None:
    if getattr(mod, "FORMATO", "surveymonkey") != "plano":
        erros.append("FORMATO precisa ser \"plano\" (o formato SurveyMonkey é configurado à mão em projeto.py).")
    for campo in ("NOME", "FONTE_XLSX", "PERGUNTAS", "PLANO"):
        if not getattr(mod, campo, None):
            erros.append(f"{campo} não definido.")
    if not str(getattr(mod, "CONTEXTO_PROJETO", "") or "").strip():
        erros.append("CONTEXTO_PROJETO vazio: descreva a pesquisa para a IA (quem respondeu, temas).")
    perguntas = getattr(mod, "PERGUNTAS", []) or []
    filtros = getattr(mod, "FILTROS", {}) or {}
    ids = [p.get("id") for p in perguntas]
    for q in {q for q in ids if ids.count(q) > 1}:
        erros.append(f"id repetido em PERGUNTAS: {q}.")
    for p in perguntas:
        q, tipo = p.get("id"), p.get("tipo")
        if tipo not in TIPOS_PLANO:
            erros.append(f"{q}: tipo {tipo!r} inválido (use meta, unica, aberta ou numerica).")
        if p.get("codificar") and tipo != "aberta":
            erros.append(f"{q}: só perguntas abertas podem ter codificar=true.")
        base = p.get("base", "todos")
        if tipo != "meta" and base != "todos" and base not in filtros:
            erros.append(f"{q}: filtro {base!r} não existe em FILTROS.")
        if tipo == "unica" and not p.get("niveis"):
            avisos.append(f"{q}: fechada sem lista de opções (niveis) — os valores não serão conferidos.")
    for nome, regra in (getattr(mod, "FILTROS_REGRAS", {}) or {}).items():
        refs = ([regra["pergunta"]] if regra.get("pergunta") else []) + (
            [regra["ou_respondeu"]] if isinstance(regra.get("ou_respondeu"), str) else list(regra.get("ou_respondeu") or []))
        for r in refs:
            if r not in ids and r != "respondent_id":
                erros.append(f"filtro {nome}: pergunta {r!r} não existe.")
    derivadas = getattr(mod, "DERIVADAS", {}) or {}
    for nome, d in derivadas.items():
        if d.get("origem") not in ids:
            erros.append(f"derivada {nome}: origem {d.get('origem')!r} não existe.")
        rotulos = set(d.get("mapa").values()) if d.get("mapa") else {f[2] for f in d.get("faixas", [])}
        if rotulos and set(d.get("niveis", [])) != rotulos:
            erros.append(f"derivada {nome}: 'niveis' deve ter exatamente os grupos do mapa/faixas ({sorted(rotulos)}).")
    for b in getattr(mod, "BANNERS_PADRAO", []) or []:
        if b not in derivadas and b not in ids:
            erros.append(f"banner {b!r} não é derivada nem pergunta.")
    codificar = {p["id"] for p in perguntas if p.get("codificar")}
    saida = (getattr(mod, "SAIDA_PLANILHA", None) or {}).get("colunas", {})
    for q in codificar - set(saida):
        avisos.append(f"{q}: marcada para categorizar, mas não vai para a planilha final (SAIDA_PLANILHA.colunas).")
    for q in set(saida) - codificar:
        erros.append(f"SAIDA_PLANILHA.colunas tem {q}, que não está marcada para categorizar.")


def _conferencia(mod, erros: list) -> None:
    c = getattr(mod, "CONFERENCIA", None) or {}
    faltam = [k for k in ("responsavel", "data", "origem_pedido") if not str(c.get(k, "")).strip()]
    if not c or faltam:
        erros.append("CONFERENCIA incompleta: registre quem confirmou o pedido, quando e de onde veio a lista de abertas"
                     + (f" (faltam: {', '.join(faltam)})." if c else "."))
        return
    pedidas = set(c.get("abertas_pedidas") or [])
    marcadas = {p["id"] for p in mod.PERGUNTAS if p.get("codificar")}
    if not pedidas:
        erros.append("CONFERENCIA.abertas_pedidas vazia: liste as abertas que o cliente pediu para categorizar.")
    elif pedidas != marcadas:
        if marcadas - pedidas:
            erros.append(f"Marcadas para categorizar, mas NÃO pedidas: {', '.join(sorted(marcadas - pedidas))}.")
        if pedidas - marcadas:
            erros.append(f"Pedidas, mas NÃO marcadas para categorizar: {', '.join(sorted(pedidas - marcadas))}.")


def _rodar_pipeline(mod, pasta: Path):
    """Ativa o projeto num slug temporário, com saída em pasta temporária, e roda load.executar."""
    import config
    import projetos

    anterior, env_antes = getattr(config, "PROJETO", None), os.environ.get("TABULADOR_OUTPUT")
    registro_original = projetos._registro
    tmp = tempfile.mkdtemp(prefix="tabulador_validacao_")
    with _trava:
        try:
            os.environ["TABULADOR_OUTPUT"] = tmp
            reg = registro_original()
            projetos._registro = lambda: {**reg, "projetos": {**reg["projetos"], SLUG_VALIDACAO: str(pasta)}}
            projetos._modulos[SLUG_VALIDACAO] = mod
            projetos.ativar(SLUG_VALIDACAO)
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                df, _ = load.executar(verbose=True)
            return df, [l.split("AVISO:", 1)[1].strip() for l in saida.getvalue().splitlines() if "AVISO:" in l]
        finally:
            projetos._registro = registro_original
            projetos._modulos.pop(SLUG_VALIDACAO, None)
            shutil.rmtree(tmp, ignore_errors=True)
            if env_antes is None:
                os.environ.pop("TABULADOR_OUTPUT", None)
            else:
                os.environ["TABULADOR_OUTPUT"] = env_antes
            if anterior and anterior != SLUG_VALIDACAO:
                try:
                    projetos.ativar(anterior)
                except Exception:
                    pass


def validar(pasta, exigir_conferencia: bool = True) -> dict:
    pasta = Path(pasta).resolve()
    erros: list[str] = []
    avisos: list[str] = []
    ok: list[str] = []
    res = {"erros": erros, "avisos": avisos, "ok": ok}
    arq = arquivo_projeto(pasta)
    if not arq:
        erros.append(f"Não há projeto.json nem projeto.py em {pasta}.")
        return {**res, "valido": False}
    if arq.suffix == ".json":
        for c in _preencher_restantes(projeto_json.ler(arq)):
            erros.append(f"Falta preencher: {c}.")
    elif PREENCHER in arq.read_text(encoding="utf-8"):
        erros.append("Ainda há PREENCHER no projeto.py.")
    try:
        mod = carregar_modulo(arq)
    except Exception as e:
        erros.append(f"O projeto não carrega: {e}")
        return {**res, "valido": False}
    _estrutura(mod, erros, avisos)
    if exigir_conferencia:
        _conferencia(mod, erros)
    fonte = Path(getattr(mod, "FONTE_XLSX", ""))
    if not fonte.exists():
        erros.append(f"Planilha-fonte não encontrada: {fonte}")
        return {**res, "valido": False}
    P = getattr(mod, "PLANO", {}) or {}
    aba = P.get("aba", 0)
    try:
        bruto = PF.ler(fonte, aba)
    except Exception as e:
        erros.append(f"Não consegui ler a aba {aba!r}: {e}")
        return {**res, "valido": False}

    # colunas, id e dados pessoais
    perguntas = mod.PERGUNTAS
    faltando = [p.get("coluna", p["id"]) for p in perguntas if p.get("coluna", p["id"]) not in bruto.columns]
    for col in faltando:
        erros.append(f"Coluna {col!r} não existe na aba {aba!r}.")
    ident = P.get("id", "respondent_id")
    if ident not in bruto.columns:
        erros.append(f"Coluna de id {ident!r} não existe.")
    else:
        ids = bruto[ident]
        if ids.isna().any():
            erros.append(f"Id vazio em {int(ids.isna().sum())} linha(s).")
        if ids.dropna().duplicated().any():
            erros.append(f"Id repetido: {', '.join(map(str, ids[ids.duplicated()].head(5)))}.")
        nao_inteiros = [v for v in ids.dropna() if not re.fullmatch(r"\d+(\.0+)?", str(v).strip())]
        if nao_inteiros:
            erros.append(f"Id não numérico (a planilha final não acharia essas linhas): {', '.join(map(str, nao_inteiros[:5]))}.")
    for p in perguntas:
        col = p.get("coluna", p["id"])
        if col in faltando or col == ident:
            continue
        vals = [v for v in PF.texto(bruto[col]) if isinstance(v, str)]
        motivo = ("nome da coluna" if PF.pii_por_nome(col) else None) or (None if p.get("tipo") == "numerica" else PF.pii_por_conteudo(vals))
        if motivo:
            erros.append(f"{p['id']}: parece dado pessoal ({motivo}) — tire de PERGUNTAS (e ponha em PII_MATCH).")
        elif p.get("tipo") == "aberta":
            n = PF.dados_pessoais_no_texto(vals)
            if n:
                avisos.append(f"{p['id']}: {n} resposta(s) com e-mail ou telefone no texto (vão para a IA).")
    if erros and any(e.startswith(("Coluna", "Id", "O projeto")) for e in erros):
        return {**res, "valido": False}

    # pipeline real
    try:
        df, avisos_load = _rodar_pipeline(mod, pasta)
    except Exception as e:
        erros.append(f"A leitura pelo tabulador falhou: {type(e).__name__}: {e}")
        return {**res, "valido": False}
    avisos.extend(f"Leitura: {a}" for a in avisos_load)

    # conservação e opções
    for p in perguntas:
        q, tipo, col = p["id"], p.get("tipo"), p.get("coluna", p["id"])
        if q not in df.columns:
            continue
        antes = PF.texto(bruto[col]).map(lambda v: isinstance(v, str))
        if tipo == "numerica":
            num = PF.numero(bruto[col]).notna()
            nsnr = PF.texto(bruto[col]).map(lambda v: isinstance(v, str) and bool(load._NSNR_RE.match(v)))
            conv = antes & ~num & ~nsnr
            if conv.any():
                exemplos = ", ".join(map(str, bruto.loc[conv, col].head(3)))
                erros.append(f"{q}: {int(conv.sum())} valor(es) não numérico(s) seriam perdidos ({exemplos}).")
            antes = num
            if p.get("nps"):
                fora = df[q].dropna()
                fora = fora[(fora < 0) | (fora > 10)]
                if len(fora):
                    erros.append(f"{q}: NPS com valores fora de 0–10 ({', '.join(map(str, fora.head(3)))}).")
        perdidos = antes & ~df[q].notna()
        if perdidos.any():
            msg = f"{q}: {int(perdidos.sum())} resposta(s) fora do filtro {p.get('base')!r} seriam apagadas da base."
            (erros if tipo == "aberta" else avisos).append(msg)
        if tipo == "unica" and p.get("niveis"):
            fora = sorted(set(df[q].dropna()) - set(p["niveis"]))
            if fora:
                erros.append(f"{q}: valores da planilha fora das opções declaradas: {fora[:5]} — copie do perfil, sem redigitar.")
        if tipo == "aberta" and p.get("codificar"):
            ok.append(f"{q}: {int(df[q].notna().sum())} respostas para categorizar (base: {getattr(mod, 'FILTROS_DESCRICAO', {}).get(p.get('base', 'todos'), p.get('base', 'todos'))}).")

    # destaques de cor nas colunas _CAT (pista do que o cliente pediu)
    cores = dict(zip(map(str, bruto.columns), PF.cores_cabecalho(fonte, aba)))
    maioria = PF.cor_maioria(list(cores.values()))
    cats = {c: cor for c, cor in cores.items() if re.match(r".+_CAT$", c)}
    destacadas = {c for c, cor in cats.items() if cor not in (None, maioria)}
    if destacadas:
        saida = (getattr(mod, "SAIDA_PLANILHA", None) or {}).get("colunas", {})
        for p in perguntas:
            if p.get("codificar"):
                cat = saida.get(p["id"], f"{p.get('coluna', p['id'])}_CAT")
                if cat in cats and cat not in destacadas:
                    avisos.append(f"{p['id']}: marcada para categorizar, mas {cat} não está destacada como {', '.join(sorted(destacadas)[:3])}…")
        marcadas_cols = {p.get("coluna", p["id"]) for p in perguntas if p.get("codificar")}
        for cat in sorted(destacadas):
            if cat[:-4] not in marcadas_cols:
                avisos.append(f"{cat} está destacada na planilha, mas {cat[:-4]} não está marcada para categorizar.")
    ok.insert(0, f"{len(df)} respondentes lidos · {len(perguntas)} colunas declaradas.")
    return {**res, "valido": not erros}


def relatorio(res: dict) -> str:
    linhas = [("✅ Projeto válido." if res["valido"] else f"❌ {len(res['erros'])} erro(s) — corrija antes de registrar.")]
    linhas += [f"  ❌ {e}" for e in res["erros"]]
    linhas += [f"  ⚠ {a}" for a in res["avisos"]]
    linhas += [f"  ✓ {o}" for o in res["ok"]]
    return "\n".join(linhas)
