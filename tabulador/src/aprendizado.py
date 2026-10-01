"""Loop de aprendizado do quadro de categorias: o que a revisão humana ensina a cada categoria.

Cálculo puro (sem IA) sobre frame.json + respostas.json + codificacao.json:

- `dossie(qid)`      : por categoria, volume, confusões (corrigido_de -> primaria), discordâncias do
                       auditor, confiança da IA, âncoras (respostas conferidas por humano) e
                       casos-limite (respostas corrigidas PARA a categoria, vindas de outra);
- `ensino(...)`      : o que entra no prompt da classificação e da auditoria (few-shot dinâmico);
- `bloco_categorias` : as linhas do code frame no prompt, já com keywords, âncoras e casos-limite;
- `keywords_sugeridas`: termos que distinguem a categoria nas respostas conferidas (lift);
- `saude(qid)`       : alertas de categoria ruim (confusão, ampla demais, rara, Outros saturado...);
- `aprender(qid)`    : grava no frame as keywords aprendidas (automático, com registro no histórico).

Regra dura: só ensina o que foi conferido por HUMANO. Item aceito sozinho (supervisor/auto-aceitar)
nunca vira exemplo nem keyword, senão a IA passa a copiar os próprios erros.
Mudança de ESTRUTURA (nome, criar, separar, mesclar) nunca acontece aqui: os alertas só sugerem.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime

import codeframe as CF
import config
import protecao
import variables as V

# palavras que não distinguem categoria nenhuma (genéricas do português; nada de domínio de projeto)
_STOP = set(V.norm("""a o e é de da do das dos em no na nos nas um uma uns umas para pra pro pelo pela pelos pelas por com sem
que se mais menos muito muita muitos muitas mas ou como ao aos à às isso isto essa esse esta este aquilo aquele aquela
eles elas ele ela eu nós nos você voce vocês voces lhe lhes me te meu minha meus minhas seu sua seus suas nosso nossa
não nao sim já ja tem têm ter tenho tinha ser são sao foi era está esta estão estao estar estou fica ficar fosse seja
porque pois quando onde qual quais quem também tambem sobre entre até ate há ha nem só so todo toda todos todas
bem bom boa ainda sempre acho coisa coisas vez vezes forma parte outros outras outro outra alguns algumas mesmo mesma
algo alguma algum cada tão tao tanto tanta então entao assim aqui ali lá la desde depois antes agora hoje muito
faz fazer feito vai vão vao ir pode podem poderia deveria gostaria acredito creio achei sei sabe""").split())


def _limiar(nome: str):
    """Limiar de config.py, sobrescrevível pelo projeto.py do projeto ativo (mesmo nome)."""
    try:
        return getattr(V._p(), nome)
    except Exception:  # noqa: BLE001 - projeto não define (ou nenhum projeto ativo): vale o padrão
        return getattr(config, nome)


conferido_por_humano = protecao.conferido_por_humano  # a mesma regra que a guarda contra perda usa


def keywords_ativas(c: dict) -> list[str]:
    """Keywords da categoria que valem no prompt: as fixadas por humano + as aprendidas, sem as bloqueadas."""
    bloq = {V.norm(k) for k in c.get("keywords_bloqueadas") or []}
    vistas, saida = set(), []
    for k in (c.get("keywords") or []) + (c.get("keywords_auto") or []):
        n = V.norm(k)
        if n and n not in bloq and n not in vistas:
            vistas.add(n)
            saida.append(k)
    return saida


# ----------------------------------------------------------------------------- termos
def _tokens(texto: str) -> list[tuple[str, str]]:
    """(forma normalizada, forma original em minúsculas) de cada palavra com 3+ letras."""
    return [(V.norm(w), w) for w in re.findall(r"[^\W\d_]{3,}", str(texto or "").lower())]


def _termos(texto: str) -> dict[str, str]:
    """Unigramas e bigramas (palavras vizinhas, nenhuma delas vazia de sentido) -> forma original."""
    toks = _tokens(texto)
    saida = {n: o for n, o in toks if n not in _STOP and len(n) >= 4}
    for (n1, o1), (n2, o2) in zip(toks, toks[1:]):
        if n1 not in _STOP and n2 not in _STOP:
            saida[f"{n1} {n2}"] = f"{o1} {o2}"
    return saida


def _parecidas(a: set, b: set) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= 0.6


def _corta(t: str) -> str:
    lim = config.FEWSHOT_MAX_CHARS
    t = " ".join(str(t).split())
    return t if len(t) <= lim else t[:lim].rstrip() + "…"


# ----------------------------------------------------------------------------- dossiê (puro)
def dossie_de(frame: dict, respostas: list[dict], itens: list[dict]) -> dict[int, dict]:
    """Uma entrada por categoria do frame. `respostas` = respostas.json['respostas'];
    `itens` = codificacao.json['itens']. Não lê nem grava arquivo (testável sem base)."""
    resp = {r["rid"]: r for r in respostas}
    cats = {c["codigo"]: c for c in frame["categorias"]}
    validos = [i for i in itens if i.get("primaria") is not None and i.get("origem") != "erro" and i["rid"] in resp]
    total = len(validos)
    d = {k: {"codigo": k, "nome": c["nome"], "fixa": bool(c.get("fixa")), "n": 0, "pct": 0.0, "n_humano": 0,
             "confusoes_saida": Counter(), "confusoes_entrada": Counter(), "conf": [], "n_auditadas": 0,
             "n_auditor_discorda": 0, "sugestoes_auditor": Counter(), "_humanos": [], "_limites": []}
         for k, c in cats.items()}
    for i in validos:
        k = i["primaria"]
        if k not in d:
            continue
        e = d[k]
        e["n"] += 1
        if conferido_por_humano(i):
            e["n_humano"] += 1
            e["_humanos"].append(i)
        de = i.get("corrigido_de")
        if i.get("origem") == "humano" and de is not None and de != k:
            e["confusoes_entrada"][de] += 1
            e["_limites"].append(i)
            if de in d:
                d[de]["confusoes_saida"][k] += 1
        if str(i.get("origem") or "").startswith("llm"):
            e["conf"].append(float(i.get("confianca") or 0))
        aud = i.get("auditoria")
        if aud and not conferido_por_humano(i):
            e["n_auditadas"] += 1
            if aud.get("ok") is False:
                e["n_auditor_discorda"] += 1
                if aud.get("primaria") is not None:
                    e["sugestoes_auditor"][aud["primaria"]] += 1
    for k, e in d.items():
        e["pct"] = round(e["n"] / total, 4) if total else 0.0
        conf = e.pop("conf")
        e["conf_media"] = round(sum(conf) / len(conf), 3) if conf else None
        e["pct_conf_baixa"] = round(sum(1 for x in conf if x < 0.6) / len(conf), 3) if conf else None
        e["ancoras"] = _ancoras(e.pop("_humanos"), resp, config.FEWSHOT_ANCORAS)
        limites = sorted(e.pop("_limites"), key=lambda i: (-resp[i["rid"]]["n"], i["rid"]))
        e["limites"] = [{"texto": _corta(resp[i["rid"]]["texto"]), "de": i["corrigido_de"],
                         "de_nome": cats.get(i["corrigido_de"], {}).get("nome", "?")} for i in limites]
        for campo in ("confusoes_saida", "confusoes_entrada", "sugestoes_auditor"):
            e[campo] = dict(e[campo].most_common())
    return d


def _ancoras(humanos: list[dict], resp: dict, n: int) -> list[str]:
    """As respostas conferidas mais frequentes, sem repetir quase a mesma frase."""
    escolhidas, termos = [], []
    for i in sorted(humanos, key=lambda i: (-resp[i["rid"]]["n"], i["rid"])):
        if len(escolhidas) >= n:
            break
        texto = resp[i["rid"]]["texto"]
        t = set(_termos(texto))
        if any(_parecidas(t, u) for u in termos) or _corta(texto) in escolhidas:
            continue
        escolhidas.append(_corta(texto))
        termos.append(t)
    return escolhidas


def keywords_sugeridas_de(frame: dict, respostas: list[dict], itens: list[dict]) -> dict[int, list[str]]:
    """Por categoria (não fixa), os termos que mais a distinguem nas respostas conferidas por humano:
    frequentes nela (>= KEYWORDS_MIN_FREQ respostas, >= 10% delas) e com lift >= 1,5 contra as demais."""
    resp = {r["rid"]: r for r in respostas}
    fixas = {c["codigo"] for c in frame["categorias"] if c.get("fixa")}
    docs: dict[int, list[dict[str, str]]] = defaultdict(list)
    for i in itens:
        if conferido_por_humano(i) and i["rid"] in resp and i["primaria"] not in fixas:
            docs[i["primaria"]].append(_termos(resp[i["rid"]]["texto"]))
    df_total, forma = Counter(), defaultdict(Counter)
    n_total = sum(len(v) for v in docs.values())
    for lista in docs.values():
        for termos in lista:
            df_total.update(termos.keys())
            for n, o in termos.items():
                forma[n][o] += 1
    saida = {}
    for k, lista in docs.items():
        df = Counter(t for termos in lista for t in termos)
        pontos = []
        for t, c in df.items():
            if c < config.KEYWORDS_MIN_FREQ or c / len(lista) < 0.10:
                continue
            lift = (c / len(lista)) / (df_total[t] / n_total)
            if lift >= 1.5:
                pontos.append((c * math.log(lift), t))
        escolhidos: list[str] = []
        for _, t in sorted(pontos, reverse=True):
            partes = set(t.split())
            if any(partes <= set(e.split()) or set(e.split()) <= partes for e in escolhidos):
                continue  # 'professores' e 'bons professores': fica o mais forte
            escolhidos.append(t)
            if len(escolhidos) >= config.KEYWORDS_MAX:
                break
        saida[k] = [forma[t].most_common(1)[0][0] for t in escolhidos]
    return saida


# ----------------------------------------------------------------------------- prompt
def ensino_de(frame: dict, respostas: list[dict], itens: list[dict]) -> dict[int, dict]:
    """O que vai para o prompt por categoria: âncoras e casos-limite (só com revisão humana)."""
    d = dossie_de(frame, respostas, itens)
    return {k: {"ancoras": e["ancoras"], "limites": e["limites"][: config.FEWSHOT_LIMITE]}
            for k, e in d.items() if e["ancoras"] or e["limites"]}


def _dados(qid: str) -> tuple[dict | None, list[dict], list[dict]]:
    frame = CF.frame(qid)
    respostas = (CF._ler(qid, "respostas.json") or {}).get("respostas", [])
    itens = (CF._ler(qid, "codificacao.json") or {}).get("itens", [])
    return frame, respostas, itens


def ensino(qid: str, frame: dict | None = None) -> dict[int, dict]:
    f, respostas, itens = _dados(qid)
    frame = frame or f
    if not frame or not itens or not (config.FEWSHOT_ANCORAS or config.FEWSHOT_LIMITE):
        return {}
    return ensino_de(frame, respostas, itens)


def bloco_categorias(frame: dict, ensino: dict | None = None) -> str:
    """Linhas do code frame no prompt. A primeira linha de cada categoria mantém o formato
    '  N: Nome - definição (ex.: a; b)' (o modo teste lê esse formato); o resto vai recuado.
    Âncoras conferidas por humano substituem os exemplos da indução quando existem."""
    ensino = ensino or {}
    linhas = []
    for c in frame["categorias"]:
        e = ensino.get(c["codigo"]) or {}
        kws = keywords_ativas(c)
        ex = (e.get("ancoras") or [])[: config.FEWSHOT_ANCORAS] if config.FEWSHOT_ANCORAS else []
        ex = ex or (c.get("exemplos") or [])[:3]
        linha = f"  {c['codigo']}: {c['nome']} - {c['definicao']}"
        if kws:
            linha += f" [termos típicos, só como pista: {', '.join(kws[:8])}]"
        if ex:
            linha += f" (ex.: {'; '.join(ex)})"
        linhas.append(linha)
        if c.get("inclui"):
            linhas.append(f"      inclui: {'; '.join(c['inclui'])}")
        if c.get("nao_inclui"):
            linhas.append(f"      não inclui: {'; '.join(c['nao_inclui'])}")
        for lim in (e.get("limites") or [])[: config.FEWSHOT_LIMITE]:
            linhas.append(f"      caso já corrigido: \"{lim['texto']}\" -> é {c['codigo']}, não {lim['de']} ({lim['de_nome']})")
    return "\n".join(linhas)


# ----------------------------------------------------------------------------- saúde do quadro
def saude_de(frame: dict, dossie: dict[int, dict]) -> list[dict]:
    """Alertas de categoria ruim. Só SUGEREM: separar, mesclar ou criar categoria é decisão humana."""
    total = sum(e["n"] for e in dossie.values())
    if not total:
        return []
    alertas = []
    nome = {k: e["nome"] for k, e in dossie.items()}
    for k, e in dossie.items():
        saida_total = sum(e["confusoes_saida"].values())
        for para, n in e["confusoes_saida"].items():
            if n >= _limiar("SAUDE_CONFUSAO_MIN") or (saida_total >= 3 and n / saida_total >= _limiar("SAUDE_CONFUSAO_PCT")):
                alertas.append({"tipo": "confusao", "codigo": k, "par": para, "n": n,
                                "msg": f"A IA pôs em \"{e['nome']}\" {n} resposta(s) que vocês corrigiram para \"{nome.get(para, para)}\": "
                                       f"a fronteira entre as duas precisa ficar mais clara na definição."})
        if e["fixa"]:
            continue
        ampla_conf = e["pct"] > _limiar("SAUDE_AMPLA_PCT") and e["conf_media"] is not None and e["conf_media"] < _limiar("SAUDE_AMPLA_CONF")
        if ampla_conf or len(e["confusoes_saida"]) >= _limiar("SAUDE_AMPLA_DESTINOS"):
            motivo = (f"tem {e['pct']:.0%} das respostas com confiança média {e['conf_media']:.2f}" if ampla_conf
                      else f"teve correções para {len(e['confusoes_saida'])} categorias diferentes")
            alertas.append({"tipo": "ampla", "codigo": k, "msg": f"\"{e['nome']}\" {motivo}: talvez esteja ampla demais (considere separar)."})
        if total >= _limiar("SAUDE_RARA_MIN_BASE") and e["pct"] < _limiar("SAUDE_RARA_PCT"):
            alertas.append({"tipo": "rara", "codigo": k, "msg": f"\"{e['nome']}\" tem só {e['n']} resposta(s) ({e['pct']:.1%}): considere mesclar em outra."})
        if e["n_auditadas"] >= 10 and e["n_auditor_discorda"] / e["n_auditadas"] > _limiar("SAUDE_AUDITOR_PCT"):
            alertas.append({"tipo": "auditor", "codigo": k,
                            "msg": f"O auditor discordou de {e['n_auditor_discorda']} de {e['n_auditadas']} em \"{e['nome']}\": a definição deve ter um buraco."})
    outros = dossie.get(CF.CODIGO_OUTROS)
    if outros and outros["pct"] > _limiar("SAUDE_OUTROS_PCT"):
        alertas.append({"tipo": "outros", "codigo": CF.CODIGO_OUTROS,
                        "msg": f"Outros tem {outros['pct']:.0%} das respostas ({outros['n']}): deve faltar alguma categoria."})
    donos = defaultdict(list)
    for c in frame["categorias"]:
        if not c.get("fixa"):
            for kw in keywords_ativas(c):
                donos[V.norm(kw)].append(c["codigo"])
    for kw, cods in donos.items():
        if len(cods) > 1:
            alertas.append({"tipo": "keyword_compartilhada", "codigo": cods[0], "par": cods[1],
                            "msg": f"A palavra-chave \"{kw}\" aparece em " + " e ".join(f"\"{nome.get(c, c)}\"" for c in cods)
                                   + ": sinal de que as categorias se sobrepõem."})
    ordem = {"outros": 0, "ampla": 1, "confusao": 2, "auditor": 3, "keyword_compartilhada": 4, "rara": 5}
    return sorted(alertas, key=lambda a: ordem.get(a["tipo"], 9))


def dossie(qid: str) -> dict[int, dict]:
    frame, respostas, itens = _dados(qid)
    return dossie_de(frame, respostas, itens) if frame else {}


def saude(qid: str) -> list[dict]:
    frame, respostas, itens = _dados(qid)
    if not frame or not itens:
        return []
    return saude_de(frame, dossie_de(frame, respostas, itens))


# ----------------------------------------------------------------------------- aprender (grava)
def n_conferidas(itens: list[dict]) -> int:
    return sum(1 for i in itens if conferido_por_humano(i))


def aprender(qid: str, forcar: bool = False) -> dict:
    """Atualiza as keywords aprendidas de cada categoria a partir das respostas conferidas por humano.
    Sem `forcar`, só roda quando entraram APRENDIZADO_A_CADA revisões humanas desde a última vez
    (chamado antes de cada classificação). Grava no histórico do frame o antes e o depois."""
    frame, respostas, itens = _dados(qid)
    if not frame or frame.get("fixo") or not itens:
        return {"rodou": False, "motivo": "sem classificação"}
    n = n_conferidas(itens)
    ultimo = (frame.get("aprendizado") or {}).get("n_conferidas", 0)
    if not forcar and n - ultimo < _limiar("APRENDIZADO_A_CADA"):
        return {"rodou": False, "motivo": f"{n - ultimo} revisão(ões) nova(s) desde a última vez", "n_conferidas": n}
    sugeridas = keywords_sugeridas_de(frame, respostas, itens)
    mudancas = []
    agora = datetime.now().isoformat(timespec="seconds")
    for c in frame["categorias"]:
        if c.get("fixa"):
            continue
        ja = {V.norm(k) for k in (c.get("keywords") or []) + (c.get("keywords_bloqueadas") or [])}
        novas = [k for k in sugeridas.get(c["codigo"], []) if V.norm(k) not in ja]
        antes = list(c.get("keywords_auto") or [])
        if novas != antes:
            c["keywords_auto"] = novas
            c["atualizado_em"], c["atualizado_por"] = agora, "auto"
            mudancas.append({"codigo": c["codigo"], "campo": "keywords_auto", "antes": antes, "depois": novas})
    frame["aprendizado"] = {"em": agora, "n_conferidas": n}
    if mudancas:
        CF._registrar(frame, "aprendizado_auto", categorias=mudancas, n_conferidas=n)
    CF._gravar(qid, "frame.json", frame)
    return {"rodou": True, "mudancas": mudancas, "n_conferidas": n, "versao": frame.get("versao", 1)}


def texto_saude(qid: str) -> str:
    alertas = saude(qid)
    if not alertas:
        return f"{qid}: nenhum alerta no quadro."
    return "\n".join([f"{qid}: {len(alertas)} alerta(s)"] + [f"  [{a['tipo']}] {a['msg']}" for a in alertas])
