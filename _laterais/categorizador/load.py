"""Leitura da planilha SurveyMonkey (cabeçalho duplo), expurgo de PII, binarização das
múltiplas e construção da base canônica + registro de variáveis.

Saídas (output/base/):
  base.json       - registros (uma linha por respondente) com IDs canônicos
  base.xlsx       - a mesma base para conferência humana
  variables.json  - registro de variáveis (rótulos, tipo, base, colunas de origem por aba)
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict

import numpy as np
import openpyxl
import pandas as pd

import config
import variables as V

# Sufixos que só existem no questionário telefônico e que devem ser removidos das opções
_SUFIXO_RE = re.compile(
    r"\s*\((?:Microempresa|Pequena|M[ée]dia|Grande|Enterprise|[Nn][aã]o ler[^)]*)\)\s*$"
)
_NSNR_RE = re.compile(r"^\s*NS\s*/\s*NR\b.*$", re.IGNORECASE)


def limpar_opcao(valor):
    """Normaliza rótulos de resposta fechada para que as duas abas usem o mesmo vocabulário."""
    if valor is None:
        return None
    s = str(valor).strip()
    if s == "":
        return None
    s = _SUFIXO_RE.sub("", s).strip()
    if _NSNR_RE.match(s):
        return "NS/NR"
    n = V.norm(s)
    if n in ("outro", "outra"):  # telefone traz só 'Outro'; autopreenchido traz 'Outro. Qual?'
        return "Outro. Qual?"
    if n in ("outros", "outras"):
        return "Outros. Quais?"
    return s


def limpar_texto(valor):
    if valor is None:
        return None
    s = re.sub(r"\s+", " ", str(valor)).strip()
    return s or None


def _eh_pii(h1: str) -> bool:
    n = V.norm(h1)
    return any(p in n for p in V.PII_MATCH)


def _encontrar_spec(h1_norm: str, contadores: dict) -> dict | None:
    for spec in V.PERGUNTAS:
        matches = spec["match"] if isinstance(spec["match"], list) else [spec["match"]]
        hit = any((h1_norm == m) if spec.get("exato") else (m in h1_norm) for m in matches)
        if not hit:
            continue
        if "ocorrencia" in spec:
            chave = spec["match"]
            contadores[chave] = contadores.get(chave, 0) + 1
            if contadores[chave] != spec["ocorrencia"]:
                # a ocorrência não bate: outro spec com o mesmo match deve absorver
                contadores[chave] -= 1
                continue
        return spec
    return None


def _classificar_opcao(h2: str) -> str:
    """'principal' (Response/Open-Ended), 'outro' (Outro. Qual? / Sim. Quais? / Por quê?) ou 'item'."""
    n = V.norm(h2)
    if n in ("", "response", "open-ended response"):
        return "principal"
    if n.startswith("outr") or n.startswith("sim. quais") or n.startswith(". por que") or n.startswith("por que"):
        return "outro"
    return "item"


def mapear_colunas(h1: list, h2: list, aba: str) -> tuple[list[dict], list[str]]:
    """Percorre o cabeçalho duplo e devolve, para cada coluna, o destino canônico.

    Retorna (mapa, avisos). Cada entrada do mapa: {col, var, kind, spec, opcao}
    kind: meta | principal | outro | item | pii | ignorar
    """
    mapa, avisos = [], []
    spec_atual = None
    contadores: dict = {}
    for i, (a, b) in enumerate(zip(h1, h2)):
        a = limpar_texto(a)
        b = limpar_texto(b)
        if a:  # início de um novo bloco
            if _eh_pii(a):
                spec_atual = {"id": "__pii__", "tipo": "pii"}
                mapa.append({"col": i, "var": None, "kind": "pii", "spec": spec_atual, "opcao": None, "h1": a, "h2": b})
                continue
            spec_atual = _encontrar_spec(V.norm(a), contadores)
            if spec_atual is None:
                avisos.append(f"[{aba}] coluna {i + 1} sem mapeamento: {a!r} / {b!r}")
                mapa.append({"col": i, "var": None, "kind": "ignorar", "spec": None, "opcao": b, "h1": a, "h2": b})
                continue
            spec_atual = dict(spec_atual, enunciado=a)
        if spec_atual is None or spec_atual.get("tipo") in ("pii",):
            kind = "pii" if spec_atual else "ignorar"
            mapa.append({"col": i, "var": None, "kind": kind, "spec": spec_atual, "opcao": b, "h1": a, "h2": b})
            continue

        tipo = spec_atual["tipo"]
        if tipo == "meta":
            mapa.append({"col": i, "var": spec_atual["id"], "kind": "meta", "spec": spec_atual, "opcao": None, "h1": a, "h2": b})
        elif tipo == "meta_bloco":
            chave = V.norm(b).rstrip(":")
            var = spec_atual["itens"].get(chave)
            mapa.append({"col": i, "var": var, "kind": "meta" if var else "ignorar", "spec": spec_atual, "opcao": b, "h1": a, "h2": b})
        else:
            kind = _classificar_opcao(b)
            if kind == "principal":
                mapa.append({"col": i, "var": spec_atual["id"], "kind": "principal", "spec": spec_atual, "opcao": None, "h1": a, "h2": b})
            elif kind == "outro":
                outro = spec_atual.get("outro")
                if outro is None:
                    avisos.append(f"[{aba}] coluna {i + 1}: campo 'outro' sem spec em {spec_atual['id']} ({b!r})")
                    mapa.append({"col": i, "var": None, "kind": "ignorar", "spec": spec_atual, "opcao": b, "h1": a, "h2": b})
                else:
                    mapa.append({"col": i, "var": outro["id"], "kind": "outro", "spec": spec_atual, "opcao": b, "h1": a, "h2": b})
            else:  # item de múltipla ou de grade
                rotulo_item = limpar_opcao(b)
                var = f"{spec_atual['id']}__{V.slug(rotulo_item)}"
                mapa.append({"col": i, "var": var, "kind": "item", "spec": spec_atual, "opcao": rotulo_item, "h1": a, "h2": b})
    return mapa, avisos


def _ler_aba(nome_aba: str):
    wb = openpyxl.load_workbook(config.FONTE_XLSX, read_only=True, data_only=True)
    ws = wb[nome_aba]
    linhas = list(ws.iter_rows(values_only=True))
    wb.close()
    h1, h2 = list(linhas[0]), list(linhas[1])
    dados = [list(r) for r in linhas[2:] if any(v is not None and str(v).strip() != "" for v in r)]
    return h1, h2, dados


def _to_num(v):
    if v is None:
        return np.nan
    s = str(v).strip()
    if s == "" or _NSNR_RE.match(s):
        return np.nan
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return np.nan


def carregar_aba(fonte: str, registro: "OrderedDict[str, dict]") -> tuple[pd.DataFrame, list[str]]:
    nome_aba = config.ABAS[fonte]
    h1, h2, dados = _ler_aba(nome_aba)
    mapa, avisos = mapear_colunas(h1, h2, nome_aba)

    # colunas não mapeadas que têm dado = erro de mapeamento (evita perda silenciosa)
    for m in mapa:
        if m["kind"] == "ignorar":
            n = sum(1 for r in dados if r[m["col"]] not in (None, ""))
            if n:
                avisos.append(f"[{nome_aba}] coluna {m['col'] + 1} IGNORADA com {n} valores: {m['h1']!r}/{m['h2']!r}")

    registros = []
    for r in dados:
        reg: dict = {"fonte": fonte}
        principal_por_q: dict = {}
        outro_por_q: dict = {}
        for m in mapa:
            if m["kind"] in ("pii", "ignorar"):
                continue
            v = r[m["col"]]
            spec = m["spec"]
            if m["kind"] == "meta":
                reg[m["var"]] = limpar_texto(v) if not isinstance(v, (int, float)) else v
            elif m["kind"] == "principal":
                if spec["tipo"] in ("unica",):
                    reg[m["var"]] = limpar_opcao(v)
                elif spec["tipo"] == "numerica":
                    reg[m["var"]] = _to_num(v)
                else:  # aberta
                    principal_por_q[spec["id"]] = limpar_texto(v)
                    reg[m["var"]] = limpar_texto(v)
            elif m["kind"] == "outro":
                txt = limpar_texto(v)
                reg[m["var"]] = txt
                outro_por_q[spec["id"]] = txt
            elif m["kind"] == "item":
                if spec["tipo"] == "multipla":
                    reg[m["var"]] = 1 if limpar_texto(v) else 0
                else:  # grade_numerica
                    reg[m["var"]] = _to_num(v)
        # aberta apresentada como 'Response + Outra. Qual?' (TOM no telefone): funde num único texto
        for spec in V.PERGUNTAS:
            if spec.get("unica_com_outro") and spec["id"] in outro_por_q:
                principal = principal_por_q.get(spec["id"])
                outro = outro_por_q.get(spec["id"])
                if principal and V.norm(principal).startswith("outr"):
                    reg[spec["id"]] = outro
                elif not principal and outro:
                    reg[spec["id"]] = outro
        registros.append(reg)

    df = pd.DataFrame(registros)

    # registro de variáveis (rótulos, origem)
    for m in mapa:
        if m["kind"] in ("pii", "ignorar") or m["var"] is None:
            continue
        spec = m["spec"]
        var = m["var"]
        ent = registro.setdefault(var, {
            "id": var,
            "pergunta": spec["id"] if spec["tipo"] not in ("meta", "meta_bloco") else None,
            "rotulo": None,
            "enunciado": None,
            "tipo": None,
            "opcao": m["opcao"],
            "base": None,
            "origem": {},
        })
        ent["origem"][nome_aba] = {"coluna": m["col"] + 1, "h1": m["h1"], "h2": m["h2"]}
        if ent["enunciado"] is None:
            ent["enunciado"] = spec.get("enunciado")
        if ent["rotulo"] is None:
            if m["kind"] == "outro":
                ent["rotulo"] = spec["outro"]["rotulo"]
                ent["tipo"] = "aberta"
                ent["base"] = spec["outro"].get("base", spec.get("base", "todos"))
            elif m["kind"] == "item":
                ent["rotulo"] = f"{spec['rotulo']} - {m['opcao']}"
                ent["tipo"] = "dicotomica" if spec["tipo"] == "multipla" else "numerica"
                ent["base"] = spec.get("base", "todos")
            elif m["kind"] == "meta":
                ent["rotulo"] = spec.get("rotulo") if spec["tipo"] == "meta" else m["opcao"]
                ent["tipo"] = "meta"
            else:
                ent["rotulo"] = spec["rotulo"]
                ent["tipo"] = spec["tipo"]
                ent["base"] = spec.get("base", "todos")
                if spec.get("niveis"):
                    ent["niveis"] = spec["niveis"]
    return df, avisos


def unir_fontes(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True, sort=False)
    df = df.drop_duplicates(subset=["respondent_id"], keep="first").reset_index(drop=True)
    return df


def aplicar_bases(df: pd.DataFrame, registro: dict) -> pd.DataFrame:
    """Fora da base da pergunta o valor vira NaN (inclusive dicotômicas), para que qualquer
    tabulação ingênua já use o denominador certo."""
    for var, ent in registro.items():
        base = ent.get("base")
        if not base or base == "todos" or var not in df.columns:
            continue
        mascara = V.FILTROS[base](df)
        df.loc[~mascara, var] = np.nan
    return df


def derivar_banners(df: pd.DataFrame, backcodes: dict | None = None) -> pd.DataFrame:
    """Cria as variáveis derivadas (banners). `backcodes` = {var_outro: {respondent_id: codigo}}."""
    backcodes = backcodes or {}
    for nome, d in V.DERIVADAS.items():
        origem = d["origem"]
        if "faixas" in d:
            def _faixa(v, faixas=d["faixas"]):
                if pd.isna(v):
                    return None
                for lo, hi, rot in faixas:
                    if lo <= v <= hi:
                        return rot
                return None
            df[nome] = df[origem].map(_faixa)
        elif "backcoding" in d:
            bc = V.BACKCODING[d["backcoding"]]
            col = df[origem].map(lambda v: bc["fechados"].get(v, "Outro" if v is not None and V.norm(str(v)).startswith("outr") else None))
            codigos = backcodes.get(d["backcoding"], {})
            if codigos:
                mapa_banner = bc["mapa_banner"]
                reclass = df["respondent_id"].map(lambda rid: mapa_banner.get(codigos.get(int(rid)), None) if pd.notna(rid) else None)
                col = col.where(~reclass.notna(), reclass)
            df[nome] = col
        elif d["mapa"] is None:
            df[nome] = df[origem]
        else:
            faltantes = set(df[origem].dropna().unique()) - set(d["mapa"])
            if faltantes:
                raise ValueError(f"{nome}: valores sem mapeamento em {origem}: {sorted(faltantes)}")
            df[nome] = df[origem].map(d["mapa"])
    return df


def registro_derivadas(registro: OrderedDict) -> None:
    for nome, d in V.DERIVADAS.items():
        registro[nome] = {
            "id": nome, "pergunta": None, "rotulo": d["rotulo"], "enunciado": None,
            "tipo": "derivada", "opcao": None, "base": "todos", "origem": {"derivada_de": d["origem"]},
            "niveis": d["niveis"],
        }


def salvar_base(df: pd.DataFrame, registro: dict) -> None:
    config.garantir_pastas()
    df2 = df.copy()
    for c in df2.columns:
        if pd.api.types.is_datetime64_any_dtype(df2[c]):
            df2[c] = df2[c].astype(str)
    df2 = df2.astype(object).where(pd.notna(df2), None)
    (config.BASE_OUT / "base.json").write_text(
        json.dumps(df2.to_dict(orient="records"), ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    (config.BASE_OUT / "variables.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    with pd.ExcelWriter(config.BASE_OUT / "base.xlsx", engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="base", index=False)
        pd.DataFrame([
            {"id": k, "pergunta": v.get("pergunta"), "rotulo": v.get("rotulo"), "tipo": v.get("tipo"),
             "base": v.get("base"), "enunciado": v.get("enunciado"), "opcao": v.get("opcao"),
             "origem": json.dumps(v.get("origem"), ensure_ascii=False)}
            for k, v in registro.items()
        ]).to_excel(xw, sheet_name="variaveis", index=False)


def carregar_base() -> tuple[pd.DataFrame, dict]:
    """Lê a base já processada (usada pelos demais módulos)."""
    p = config.BASE_OUT / "base.json"
    if not p.exists():
        raise FileNotFoundError("Base não encontrada. Rode: python run.py load")
    df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
    registro = json.loads((config.BASE_OUT / "variables.json").read_text(encoding="utf-8"))
    # tipos numéricos
    for var, ent in registro.items():
        if ent.get("tipo") in ("numerica", "dicotomica") and var in df.columns:
            df[var] = pd.to_numeric(df[var], errors="coerce")
    return df, registro


def _enunciados_codebook(aba: str | None) -> dict[str, str]:
    """{coluna: enunciado} a partir de uma aba 'Codebook' (Questão | Pergunta). Linhas sem pergunta
    são títulos de bloco (ex.: 'Os itens abaixo tratam da estrutura...') e viram prefixo dos itens
    seguintes, até a próxima pergunta propriamente dita (texto terminado em '?')."""
    if not aba:
        return {}
    try:
        cb = pd.read_excel(config.FONTE_XLSX, sheet_name=aba)
    except ValueError:
        return {}
    saida, bloco = {}, None
    c_q, c_p = cb.columns[0], cb.columns[1]
    for q, p in zip(cb[c_q], cb[c_p]):
        q = limpar_texto(q) if pd.notna(q) else None
        p = limpar_texto(p) if pd.notna(p) else None
        if q and not p:
            bloco = q if len(q) > 20 else bloco  # títulos de bloco são textos longos
            continue
        if q and p:
            if p.rstrip().endswith("?"):
                bloco = None
            saida[q] = f"{bloco} — {p}" if bloco else p
    return saida


def executar_plano(backcodes: dict | None = None, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    """Planilha 'plana': uma linha de cabeçalho, uma coluna por pergunta (V.PLANO / spec['coluna']).
    Só as colunas declaradas em V.PERGUNTAS entram na base (PII e colunas vazias ficam de fora)."""
    P = V.PLANO
    aba = P.get("aba", 0)
    bruto = pd.read_excel(config.FONTE_XLSX, sheet_name=aba)
    enunciados = _enunciados_codebook(P.get("aba_codebook"))
    registro: OrderedDict[str, dict] = OrderedDict()
    registro["fonte"] = {"id": "fonte", "pergunta": None, "rotulo": "Fonte", "enunciado": None,
                         "tipo": "meta", "opcao": None, "base": None, "origem": {}}
    cols: dict = {"fonte": pd.Series("planilha", index=bruto.index)}
    avisos, usadas = [], set()
    for spec in V.PERGUNTAS:
        col = spec.get("coluna", spec["id"])
        if col not in bruto.columns:
            avisos.append(f"coluna {col!r} ({spec['id']}) não existe na aba {aba!r}")
            continue
        usadas.add(col)
        s = bruto[col]
        tipo = spec["tipo"]
        if tipo == "numerica":
            s = s.map(_to_num)
        elif tipo in ("unica", "aberta"):
            s = s.map(lambda v: None if pd.isna(v) else limpar_texto(v))
        elif tipo == "meta":
            s = s.map(lambda v: None if pd.isna(v) else (v if isinstance(v, (int, float, np.integer, np.floating)) else str(v)))
        cols[spec["id"]] = s
        registro[spec["id"]] = {
            "id": spec["id"], "pergunta": spec["id"] if tipo != "meta" else None, "rotulo": spec.get("rotulo"),
            "enunciado": enunciados.get(col) or spec.get("rotulo"), "tipo": tipo, "opcao": None,
            "base": spec.get("base", "todos") if tipo != "meta" else None,
            "origem": {str(aba): {"coluna": list(bruto.columns).index(col) + 1, "h1": col, "h2": None}},
        }
        if spec.get("niveis"):
            registro[spec["id"]]["niveis"] = spec["niveis"]
    saidas = set((V.SAIDA_PLANILHA or {}).get("colunas", {}).values())
    for col in bruto.columns:
        if col in usadas or col in saidas or _eh_pii(str(col)):
            continue
        n = int(bruto[col].notna().sum())
        if n:
            avisos.append(f"coluna {col!r} ignorada ({n} valores) — declare em projeto.py se for necessária")
    df = pd.DataFrame(cols)
    ident = P.get("id", "respondent_id")
    if ident != "respondent_id":
        df["respondent_id"] = bruto[ident]
    if df["respondent_id"].duplicated().any():
        raise ValueError("respondent_id repetido na planilha-fonte")
    df = aplicar_bases(df, registro)
    df = derivar_banners(df, backcodes)
    registro_derivadas(registro)
    salvar_base(df, registro)
    if verbose:
        print(f"  base: {len(df)} respondentes x {df.shape[1]} variáveis -> {config.BASE_OUT}")
        for a in avisos:
            print("  AVISO:", a)
    return df, registro


def executar(incluir_telefone: bool = True, backcodes: dict | None = None, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    if V.FORMATO == "plano":
        return executar_plano(backcodes=backcodes, verbose=verbose)
    registro: OrderedDict[str, dict] = OrderedDict()
    fontes = ["autopreenchido"] + (["telefone"] if incluir_telefone else [])
    frames, avisos = [], []
    for f in fontes:
        df, av = carregar_aba(f, registro)
        frames.append(df)
        avisos += av
        if verbose:
            print(f"  aba {config.ABAS[f]!r}: {len(df)} respondentes, {df.shape[1]} colunas")
    df = unir_fontes(frames)
    # ordena as colunas conforme o registro (ordem do questionário) + fonte
    cols = ["fonte"] + [c for c in registro if c in df.columns]
    df = df.reindex(columns=cols)
    registro["fonte"] = {"id": "fonte", "pergunta": None, "rotulo": "Fonte (autopreenchido/telefone)", "enunciado": None,
                         "tipo": "meta", "opcao": None, "base": None, "origem": {}}
    registro.move_to_end("fonte", last=False)
    # remove colunas 'outro' totalmente vazias (ex.: '. Por quê? ____' do SurveyMonkey)
    for var in [v for v, e in registro.items() if e.get("tipo") == "aberta"]:
        if var in df.columns and df[var].isna().all():
            df = df.drop(columns=[var])
            registro.pop(var)
            avisos.append(f"coluna {var} removida: sem nenhum valor")
    # campos 'outro' que foram fundidos na pergunta principal (ex.: TOM por telefone)
    for spec in V.PERGUNTAS:
        o = spec.get("outro") or {}
        if o.get("fundir") and o["id"] in df.columns:
            df = df.drop(columns=[o["id"]])
            registro.pop(o["id"], None)
    df = aplicar_bases(df, registro)
    df = derivar_banners(df, backcodes)
    registro_derivadas(registro)
    salvar_base(df, registro)
    if verbose:
        print(f"  base consolidada: {len(df)} respondentes x {df.shape[1]} variáveis -> {config.BASE_OUT}")
        for a in avisos:
            print("  AVISO:", a)
    return df, registro


if __name__ == "__main__":
    executar()
