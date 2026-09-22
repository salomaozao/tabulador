"""Modo teste: responde no lugar da IA com valores SIMULADOS (sem internet, sem chave, sem custo).

Serve para validar o funcionamento do app (fluxo, telas, loop de revisão, resultados) sem gastar
cota. Lê o mesmo prompt que iria para a IA e devolve JSON no formato pedido (`schema`):

- propor categorias : as palavras mais frequentes das respostas viram categorias (com exemplos reais);
- ajustar categorias: entende "junte/mescle X e Y" e "crie 'Z'" citando nomes de categorias;
- classificar       : categoria com mais palavras em comum com a resposta (nome, definição, exemplos);
                      sem nada em comum -> Outros (97). Comentário do pesquisador que cita uma
                      categoria é obedecido. Confiança varia de propósito para gerar alertas.

Tudo é determinístico (mesma entrada -> mesma saída). Atraso por chamada: CATEGORIZADOR_SIMULADO_ATRASO
(segundos, padrão 0.4) para dar para ver a barra de progresso.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
import unicodedata
from collections import Counter

ATRASO = float(os.getenv("CATEGORIZADOR_SIMULADO_ATRASO", "0.4"))

_STOP = set("""a o e é de da do das dos em no na nos nas um uma uns umas para pra pelo pela pelos pelas por com sem
que se mais muito muita muitos muitas mas ou como ao aos à às isso essa esse esta este eles elas ele ela eu
nao não sim já ja tem ter ser são sao foi está esta estão estao meu minha meus minhas seu sua seus suas
porque pois quando onde qual quais também tambem sobre entre até ate há ha nem só so todo toda todos todas
bem bom boa melhor melhorar precisa poderia deveria escola sesi aluno alunos filho filha filhos minha nossa
nada tudo ainda sempre acho coisa coisas vez forma parte outros outras outro outra alguns algumas mesmo""".split())


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _palavras(t: str) -> list[str]:
    stop = {_norm(s) for s in _STOP}
    return [w for w in re.findall(r"[a-z]{4,}", _norm(t)) if w not in stop]


def _radical(w: str) -> str:
    return w[:6]  # 'professores'/'professor' -> 'profes'


def _hash01(*partes) -> float:
    h = hashlib.md5("|".join(map(str, partes)).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


# ----------------------------------------------------------------------------- leitura do prompt
def _respostas_inducao(user: str) -> list[tuple[int, str]]:
    return [(int(n), t.strip()) for n, t in re.findall(r"^- \((\d+)x\) (.+)$", user, re.M)]


def _frame_prompt(user: str) -> list[dict]:
    """Linhas '  N: Nome - definição (ex.: a; b)' do bloco de categorias do prompt."""
    cats = []
    for cod, resto in re.findall(r"^\s{2}(\d+): (.+)$", user, re.M):
        nome, _, defi = resto.partition(" - ")
        ex = re.search(r"\(ex\.: (.*)\)\s*$", defi)
        cats.append({"codigo": int(cod), "nome": nome.strip(), "definicao": re.sub(r"\s*\(ex\.: .*\)\s*$", "", defi).strip(),
                     "exemplos": [e.strip() for e in ex.group(1).split(";")] if ex else []})
    return cats


# ----------------------------------------------------------------------------- respostas simuladas
def _propor(user: str) -> dict:
    resp = _respostas_inducao(user)
    m = re.search(r"com (\d+) a (\d+) categorias", user)
    mn, mx = (int(m.group(1)), int(m.group(2))) if m else (6, 12)
    alvo = max(3, min(mx, max(mn, 8)))
    cont, forma, exemplos = Counter(), {}, {}
    stop = {_norm(s) for s in _STOP}
    for n, t in resp:
        originais = {w for w in re.findall(r"[^\W\d_]{4,}", t.lower()) if _norm(w) not in stop}  # mantém acentos
        for w in originais:
            r = _radical(_norm(w))
            cont[r] += n
            forma.setdefault(r, Counter())[w] += n
            exemplos.setdefault(r, [])
            if len(exemplos[r]) < 3 and t not in exemplos[r]:
                exemplos[r].append(t[:120])
    escolhidos = [r for r, _ in cont.most_common(alvo)]
    cats = []
    for r in escolhidos:
        palavra = forma[r].most_common(1)[0][0]
        cats.append({"nome": palavra.capitalize(), "definicao": f"[SIMULADO] Respostas que mencionam '{palavra}'.",
                     "exemplos": exemplos[r]})
    if not cats:
        cats = [{"nome": "Tema geral", "definicao": "[SIMULADO] Categoria única.", "exemplos": []}]
    return {"raciocinio": f"[MODO TESTE — categorias simuladas] Palavras mais frequentes em {len(resp)} respostas únicas.",
            "categorias": cats}


def _refinar(user: str) -> dict:
    atuais = [c for c in _frame_prompt(user.split("PEDIDO DO PESQUISADOR")[0]) if c["codigo"] not in (97, 98)]
    pedido = (re.search(r"PEDIDO DO PESQUISADOR.*?:\n(.+?)\n\n", user, re.S) or [None, ""])[1]
    p = _norm(pedido)
    citadas = [c for c in atuais if _norm(c["nome"]) in p]
    saida = [{"codigo_anterior": c["codigo"], "incorpora": [], "nome": c["nome"], "definicao": c["definicao"], "exemplos": c["exemplos"]} for c in atuais]
    feito = []
    if re.search(r"\b(junt|mescl|fund|una|unir|agrup)", p) and len(citadas) >= 2:
        destino, *origens = citadas
        saida = [s for s in saida if s["codigo_anterior"] not in {o["codigo"] for o in origens}]
        d = next(s for s in saida if s["codigo_anterior"] == destino["codigo"])
        d["incorpora"] = [o["codigo"] for o in origens]
        d["nome"] = " / ".join([destino["nome"]] + [o["nome"] for o in origens])[:60]
        feito.append(f"juntei {', '.join(c['nome'] for c in citadas)}")
    for novo in re.findall(r"['\"“‘]([^'\"”’]{2,60})['\"”’]", pedido):
        if re.search(r"\b(cri|nova|adicion|inclu|acrescent)", p) and not any(_norm(novo) == _norm(s["nome"]) for s in saida):
            saida.append({"codigo_anterior": None, "incorpora": [], "nome": novo.strip(), "definicao": f"[SIMULADO] Criada a pedido: {novo.strip()}.", "exemplos": []})
            feito.append(f"criei '{novo.strip()}'")
    if re.search(r"\b(remov|exclu|apag|tir)", p) and citadas and not feito:
        saida = [s for s in saida if s["codigo_anterior"] != citadas[0]["codigo"]]
        feito.append(f"removi {citadas[0]['nome']}")
    return {"raciocinio": "[MODO TESTE] " + ("; ".join(feito) if feito else
            "não identifiquei o pedido — cite nomes de categorias e use 'junte X e Y', 'crie \"Z\"' ou 'remova X'."),
            "categorias": saida}


def _classificar(user: str) -> dict:
    bloco = user.split("CODE FRAME APROVADO")[1].split("REGRAS")[0] if "CODE FRAME APROVADO" in user else user
    cats = _frame_prompt(bloco)
    validas = [c for c in cats if c["codigo"] not in (97, 98)]
    perfil = {c["codigo"]: {_radical(w) for w in _palavras(" ".join([c["nome"], c["definicao"], *c["exemplos"]]).replace("[SIMULADO]", ""))} for c in validas}
    saida = []
    for rid, texto, obs in re.findall(r'^\s+rid (\d+): "(.*)"(?:\s+\[OBSERVAÇÃO DO PESQUISADOR - siga obrigatoriamente: (.*)\])?$', user, re.M):
        rid = int(rid)
        palavras = {_radical(w) for w in _palavras(texto)}
        pontos = sorted(((len(palavras & perfil[c["codigo"]]), c["codigo"]) for c in validas), reverse=True)
        mandada = next((c["codigo"] for c in cats if obs and _norm(c["nome"]) in _norm(obs)), None)
        if mandada is not None:
            prim, sec, conf, just = mandada, None, 1.0, f"[SIMULADO] segui o comentário: {obs[:60]}"
        elif pontos and pontos[0][0] > 0:
            prim = pontos[0][1]
            sec = pontos[1][1] if len(pontos) > 1 and pontos[1][0] > 0 else None
            conf = round(min(0.99, 0.55 + 0.15 * pontos[0][0] + 0.3 * _hash01(rid, texto)), 2)
            just = f"[SIMULADO] {pontos[0][0]} palavra(s) em comum com a categoria"
        else:
            prim, sec, conf, just = 97, None, round(0.25 + 0.3 * _hash01(rid, texto), 2), "[SIMULADO] nenhuma palavra em comum"
        saida.append({"rid": rid, "primaria": prim, "secundaria": sec, "confianca": conf, "justificativa": just})
    return {"codificacoes": saida}


def _padrao(schema: dict):
    """Valor mínimo válido para qualquer schema (ex.: teste de conexão)."""
    t = schema.get("type")
    t = t[0] if isinstance(t, list) else t
    if t == "object":
        return {k: _padrao(v) for k, v in (schema.get("properties") or {}).items()}
    return {"array": [], "string": "[SIMULADO]", "integer": 0, "number": 0.0, "boolean": True, "null": None}.get(t)


def responder(system: str, user: str, schema: dict) -> dict:
    if ATRASO:
        time.sleep(ATRASO)
    props = schema.get("properties") or {}
    if "codificacoes" in props:
        return _classificar(user)
    if "categorias" in props:
        itens = props["categorias"].get("items", {}).get("properties", {})
        return _refinar(user) if "codigo_anterior" in itens else _propor(user)
    return _padrao(schema)
