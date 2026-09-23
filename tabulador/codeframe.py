"""Fase 1 - Code frame por pergunta.

1. `preparar(qid)`  : extrai as respostas da base (com filtro de base), deduplica, marca NS/NR
                      -> output/perguntas/<QID>/respostas.json
2. `induzir(qid)`   : LLM propõe um frame fechado (categorias com definição e exemplos)
                      -> frame_proposto.json e frame.json (status 'rascunho')
3. edição humana    : `renomear`, `fundir`, `adicionar`, `remover`, `mostrar` (ou editar frame.json)
4. `aprovar(qid)`   : trava o frame (status 'aprovado'); só então a codificação roda.

Perguntas de back-coding (variables.BACKCODING) recebem frame FIXO já aprovado.
"""
from __future__ import annotations

import json
import random
import re
from datetime import datetime

import config
import llm
import load
import progresso
import variables as V

CODIGO_OUTROS = 97
CODIGO_NSNR = 98
FIXAS = [
    {"codigo": CODIGO_OUTROS, "nome": "Outros", "definicao": "Resposta válida que não se encaixa em nenhuma categoria do frame.", "exemplos": [], "fixa": True},
    {"codigo": CODIGO_NSNR, "nome": "NS/NR", "definicao": "Não sabe / não respondeu / não conhece o suficiente / resposta vazia ou sem sentido.", "exemplos": [], "fixa": True},
]

# Detecção determinística de NS/NR (texto normalizado). Conservadora de propósito:
# 'nenhum', 'nada' etc. podem ser respostas válidas (ex.: 'nenhum ponto negativo').
_NSNR_RE = re.compile(
    r"^(?:"
    r"n[a]?o sei(?: (?:responder|dizer|informar|avaliar|opinar))?\.?|"
    r"n[a]?o (?:conheco|conhece|sabe|lembro|lemra|tenho conhecimento|tenho base.*)|"
    r"nao tem conhecimento|desconheco|"
    r"ns|nr|ns/nr|n/a|na|nao se aplica|sem resposta|sem opiniao|"
    r"[-.?]+"
    r")$"
)


def pasta(qid: str):
    p = config.PERGUNTAS_OUT / qid
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ler(qid: str, nome: str) -> dict | None:
    p = pasta(qid) / nome
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _gravar(qid: str, nome: str, dados: dict) -> None:
    (pasta(qid) / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def eh_nsnr(texto: str) -> bool:
    return bool(_NSNR_RE.match(V.norm(texto)))


# ----------------------------------------------------------------------------- instruções humanas
def instrucoes(qid: str) -> str:
    """Instruções livres do pesquisador para esta pergunta (entram na indução e na codificação)."""
    d = _ler(qid, "instrucoes.json")
    return (d or {}).get("texto", "")


def salvar_instrucoes(qid: str, texto: str) -> None:
    _gravar(qid, "instrucoes.json", {"texto": (texto or "").strip(), "atualizado_em": datetime.now().isoformat(timespec="seconds")})


def instrucoes_completas(qid: str) -> str:
    spec = V.por_id(qid)
    partes = [t for t in (spec.get("instrucoes_frame", ""), instrucoes(qid)) if t]
    return "\n".join(partes)


# ----------------------------------------------------------------------------- respostas
def preparar(qid: str) -> dict:
    df, registro = load.carregar_base()
    spec = V.por_id(qid)
    base = spec.get("base", "todos")
    if qid in V.BACKCODING:
        base = V.por_id(qid)["base"]
    mascara = V.FILTROS[base](df)
    sub = df.loc[mascara, ["respondent_id", qid]]
    grupos: dict[str, dict] = {}
    for rid_resp, texto in zip(sub["respondent_id"], sub[qid]):
        if texto is None or (isinstance(texto, float)) or str(texto).strip() == "":
            continue
        texto = str(texto).strip()
        chave = re.sub(r"[\s.!,;:]+$", "", V.norm(texto))
        g = grupos.setdefault(chave, {"texto": texto, "n": 0, "respondent_ids": []})
        g["n"] += 1
        g["respondent_ids"].append(int(rid_resp))
    respostas = []
    for i, g in enumerate(sorted(grupos.values(), key=lambda g: (-g["n"], V.norm(g["texto"]))), start=1):
        respostas.append({"rid": i, "texto": g["texto"], "n": g["n"], "respondent_ids": g["respondent_ids"], "nsnr": eh_nsnr(g["texto"])})
    dados = {
        "pergunta": qid,
        "rotulo": spec.get("rotulo"),
        "enunciado": registro.get(qid, {}).get("enunciado"),
        "base": base,
        "base_descricao": V.FILTROS_DESCRICAO.get(base, base),
        "n_base": int(mascara.sum()),
        "n_respondeu": int(sum(g["n"] for g in grupos.values())),
        "n_unicas": len(respostas),
        "n_nsnr_auto": sum(1 for r in respostas if r["nsnr"]),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "respostas": respostas,
    }
    _gravar(qid, "respostas.json", dados)
    return dados


def respostas(qid: str) -> dict:
    d = _ler(qid, "respostas.json")
    return d if d else preparar(qid)


# ----------------------------------------------------------------------------- frame
SCHEMA_FRAME = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "raciocinio": {"type": "string", "description": "Breve análise dos temas presentes nas respostas."},
        "categorias": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "nome": {"type": "string"},
                    "definicao": {"type": "string"},
                    "exemplos": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["nome", "definicao", "exemplos"],
            },
        },
    },
    "required": ["raciocinio", "categorias"],
}


def _linhas_inducao(dados: dict) -> tuple[list[str], str]:
    """Respostas que a IA lê para propor/refinar o frame. Acima de config.MAX_RESPOSTAS_INDUCAO
    respostas únicas, usa todas as repetidas (n>1) + amostra aleatória fixa das demais."""
    validas = [r for r in dados["respostas"] if not r["nsnr"]]
    limite = config.MAX_RESPOSTAS_INDUCAO
    nota = ""
    if len(validas) > limite:
        repetidas = [r for r in validas if r["n"] > 1][:limite]
        resto = [r for r in validas if r["n"] == 1]
        amostra = random.Random(0).sample(resto, max(0, min(len(resto), limite - len(repetidas))))
        validas = sorted(repetidas + amostra, key=lambda r: r["rid"])
        nota = f" (AMOSTRA de {len(validas)} das {dados['n_unicas']} respostas únicas)"
    corta = lambda t: t if len(t) <= 400 else t[:400] + "…"
    return [f"- ({r['n']}x) {corta(r['texto'])}" for r in validas], nota


def _prompt_inducao(qid: str, dados: dict, spec: dict, min_cat: int, max_cat: int) -> tuple[str, str]:
    system = (
        "Você é um pesquisador sênior de pesquisa de mercado quantitativa, especialista em construir "
        "CODE FRAMES (livros de códigos) para perguntas abertas. Responda em português do Brasil."
    )
    linhas, nota = _linhas_inducao(dados)
    instr = instrucoes_completas(qid)
    user = f"""CONTEXTO DO PROJETO
{config.CONTEXTO_PROJETO}

PERGUNTA ({qid}): {dados.get('enunciado') or spec.get('rotulo')}
Base: {dados['base_descricao']} (n={dados['n_base']}; {dados['n_respondeu']} responderam; {dados['n_unicas']} respostas únicas)

TAREFA
Proponha um code frame FECHADO com {min_cat} a {max_cat} categorias para codificar TODAS as respostas abaixo.
Regras:
1. Categorias mutuamente exclusivas, com nome curto (1 a 4 palavras) e definição objetiva de 1 frase.
2. Cada categoria deve representar UMA ideia; não funda conceitos distintos no mesmo nome ("Preço e Atendimento" é proibido).
3. Priorize categorias com capacidade analítica para o cliente ({config.CLIENTE}); agrupe ideias raras em categorias mais amplas em vez de criar categorias com 1 menção, salvo quando a ideia for estrategicamente relevante.
4. NÃO crie categorias 'Outros' nem 'Não sabe / não respondeu': elas serão adicionadas automaticamente.
5. Liste 2 a 4 exemplos LITERAIS (copiados das respostas) por categoria.
6. Ordene as categorias da mais frequente para a menos frequente.
{('Instruções específicas desta pergunta: ' + instr) if instr else ''}

RESPOSTAS (frequência x texto){nota}:
{chr(10).join(linhas)}
"""
    return system, user


def _resumo_pedido(dados: dict, texto: str) -> str:
    linhas, nota = _linhas_inducao(dados)
    return f"{len(linhas)} respostas enviadas à IA{' (amostra)' if nota else ''} · ~{max(1, round(len(texto) / 4 / 1000))} mil tokens"


def induzir(qid: str, min_cat: int = 6, max_cat: int = 15, forcar: bool = False) -> dict:
    """Gera frame_proposto.json e frame.json (rascunho). Se frame.json já estiver aprovado, exige forcar."""
    atual = _ler(qid, "frame.json")
    if atual and atual.get("status") == "aprovado" and not forcar:
        raise RuntimeError(f"{qid}: frame já aprovado. Use --forcar para reinduzir (o frame aprovado será substituído).")
    if qid in V.BACKCODING:
        return frame_fixo(qid)
    spec = V.por_id(qid)
    progresso.etapa("ler", "lendo a base de respondentes")
    dados = preparar(qid)
    progresso.etapa("pedido", f"{dados['n_respondeu']} pessoas responderam · {dados['n_unicas']} respostas diferentes · {dados['n_nsnr_auto']} NS/NR separadas por regra")
    system, user = _prompt_inducao(qid, dados, spec, min_cat, max_cat)
    progresso.evento(f"Pedido montado: {_resumo_pedido(dados, system + user)}")
    progresso.etapa("ia", f"{_resumo_pedido(dados, system + user)} · modelo {config.OPENAI_MODEL}", estimativa=progresso.tempo_medio("frame_"))
    saida = llm.chamar_json(system, user, SCHEMA_FRAME, nome=f"frame_{qid}")
    progresso.evento(f"A IA propôs {len(saida['categorias'])} categorias")
    progresso.etapa("gravar", f"{len(saida['categorias'])} categorias + Outros e NS/NR")
    categorias = []
    for i, c in enumerate(saida["categorias"], start=1):
        categorias.append({"codigo": i, "nome": c["nome"].strip(), "definicao": c["definicao"].strip(), "exemplos": c.get("exemplos", []), "fixa": False})
    frame = {
        "pergunta": qid,
        "enunciado": dados.get("enunciado"),
        "status": "rascunho",
        "fixo": False,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "modelo": config.OPENAI_MODEL,
        "raciocinio": saida.get("raciocinio", ""),
        "categorias": categorias + [dict(f) for f in FIXAS],
        "historico": [],
    }
    _gravar(qid, "frame_proposto.json", frame)
    _gravar(qid, "frame.json", frame)
    (pasta(qid) / "frame_anterior.json").unlink(missing_ok=True)
    return frame


SCHEMA_REFINO = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "raciocinio": {"type": "string", "description": "O que foi alterado e por quê, em 1 a 3 frases."},
        "categorias": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "codigo_anterior": {"type": ["integer", "null"], "description": "Código da categoria atual que esta continua (null se nova)."},
                    "incorpora": {"type": "array", "items": {"type": "integer"}, "description": "Códigos de categorias atuais fundidas nesta."},
                    "nome": {"type": "string"},
                    "definicao": {"type": "string"},
                    "exemplos": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["codigo_anterior", "incorpora", "nome", "definicao", "exemplos"],
            },
        },
    },
    "required": ["raciocinio", "categorias"],
}


def refinar(qid: str, feedback: str) -> dict:
    """Loop de feedback do frame: a IA recebe o frame atual + o pedido do pesquisador
    ("junte X e Y", "separe Z", "falta categoria para W") e devolve o frame revisado.
    Categorias que continuam mantêm o código; fundidas/removidas são remapeadas na codificação."""
    feedback = (feedback or "").strip()
    if not feedback:
        raise ValueError("Escreva o que deve mudar nas categorias.")
    atual = _exigir_frame(qid)
    if atual.get("fixo"):
        raise ValueError("Este frame é fixo (back-coding) e não pode ser refinado pela IA.")
    spec = V.por_id(qid)
    dados = respostas(qid)
    linhas, nota = _linhas_inducao(dados)
    cats = "\n".join(f"  {c['codigo']}: {c['nome']} - {c['definicao']}" for c in atual["categorias"] if not c.get("fixa"))
    instr = instrucoes_completas(qid)
    system = (
        "Você é um pesquisador sênior de pesquisa de mercado, especialista em CODE FRAMES para perguntas "
        "abertas. Revisa um code frame seguindo o pedido do pesquisador. Responda em português do Brasil."
    )
    user = f"""CONTEXTO DO PROJETO
{config.CONTEXTO_PROJETO}

PERGUNTA ({qid}): {dados.get('enunciado') or spec.get('rotulo')}

CODE FRAME ATUAL:
{cats}

PEDIDO DO PESQUISADOR (siga obrigatoriamente):
{feedback}

TAREFA
Devolva o code frame COMPLETO revisado (todas as categorias que devem existir, não só as alteradas).
Regras:
1. Altere apenas o necessário para atender ao pedido; mantenha as demais categorias como estão.
2. `codigo_anterior` = código da categoria atual que a nova continua (mesmo que renomeada); null se for nova.
3. `incorpora` = códigos de categorias atuais que foram FUNDIDAS nesta (lista vazia se nenhuma).
4. Nome curto (1 a 4 palavras), definição de 1 frase, 2 a 4 exemplos LITERAIS das respostas.
5. NÃO inclua 'Outros' nem 'NS/NR': são fixas.
{('Instruções gerais desta pergunta: ' + instr) if instr else ''}

RESPOSTAS (frequência x texto){nota}:
{chr(10).join(linhas)}
"""
    progresso.etapa("ia", f"{len(atual['categorias']) - 2} categorias atuais + seu pedido · {_resumo_pedido(dados, system + user)} · modelo {config.OPENAI_MODEL}",
                    estimativa=progresso.tempo_medio("refino_") or progresso.tempo_medio("frame_"))
    saida = llm.chamar_json(system, user, SCHEMA_REFINO, nome=f"refino_{qid}")
    progresso.evento(f"A IA devolveu a lista revisada com {len(saida['categorias'])} categorias")
    progresso.etapa("gravar", "mantendo os códigos das categorias que continuam e remapeando as fundidas")
    antigos = {c["codigo"]: c for c in atual["categorias"] if not c.get("fixa")}
    usados: set = set()
    novas, pendentes = [], []
    for c in saida["categorias"]:
        cod = c.get("codigo_anterior")
        if cod in antigos and cod not in usados:
            usados.add(cod)
            novas.append({"codigo": cod, "nome": c["nome"].strip(), "definicao": c["definicao"].strip(), "exemplos": c.get("exemplos", []), "fixa": False, "_inc": c.get("incorpora") or []})
        else:
            pendentes.append(c)
    prox = max(list(antigos) + [0]) + 1
    for c in pendentes:
        novas.append({"codigo": prox, "nome": c["nome"].strip(), "definicao": c["definicao"].strip(), "exemplos": c.get("exemplos", []), "fixa": False, "_inc": c.get("incorpora") or []})
        prox += 1
    remap = {}
    for c in novas:
        for o in c.pop("_inc"):
            if o in antigos and o not in usados and o != c["codigo"]:
                remap[o] = c["codigo"]
    for o in antigos:
        if o not in usados and o not in remap:
            remap[o] = CODIGO_OUTROS  # categoria removida sem destino
    _gravar(qid, "frame_anterior.json", atual)
    f = dict(atual)
    f["categorias"] = novas + [c for c in atual["categorias"] if c.get("fixa")]
    f["raciocinio"] = saida.get("raciocinio", "")
    f["modelo"] = config.OPENAI_MODEL
    _registrar(f, "refinar_ia", pedido=feedback, remapeados={str(k): v for k, v in remap.items()})
    f["status"] = _status_apos_edicao(qid)
    _gravar(qid, "frame.json", f)
    _remapear_codificacao(qid, remap)
    return f


def desfazer_refino(qid: str) -> dict:
    """Volta o frame para a versão anterior ao último refino pela IA. A classificação não volta:
    respostas em categorias que deixaram de existir vão para Outros (reclassifique depois)."""
    anterior = _ler(qid, "frame_anterior.json")
    if not anterior:
        raise RuntimeError("Não há refino para desfazer.")
    anterior["status"] = _status_apos_edicao(qid)
    _registrar(anterior, "desfazer_refino")
    _gravar(qid, "frame.json", anterior)
    (pasta(qid) / "frame_anterior.json").unlink()
    validos = {c["codigo"] for c in anterior["categorias"]}
    cod = _ler(qid, "codificacao.json")
    if cod:
        orfaos = {i.get(k) for i in cod["itens"] for k in ("primaria", "secundaria")} - validos - {None}
        _remapear_codificacao(qid, {o: CODIGO_OUTROS for o in orfaos})
    return anterior


def frame_fixo(qid: str) -> dict:
    bc = V.BACKCODING[qid]
    dados = preparar(qid)
    frame = {
        "pergunta": qid,
        "enunciado": dados.get("enunciado"),
        "status": "aprovado",
        "fixo": True,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "aprovado_em": datetime.now().isoformat(timespec="seconds"),
        "modelo": None,
        "raciocinio": "Frame fixo de back-coding definido em variables.BACKCODING.",
        "categorias": [dict(c, exemplos=[], fixa=False) for c in bc["frame"]] + [dict(f) for f in FIXAS],
        "historico": [],
    }
    _gravar(qid, "frame.json", frame)
    return frame


def frame(qid: str) -> dict | None:
    f = _ler(qid, "frame.json")
    # antes, qualquer edição depois de classificar voltava o frame para rascunho e travava a
    # classificação; frames que já foram aprovados e têm classificação voltam a valer
    if f and f.get("status") == "rascunho" and classificacao_iniciada(qid) and any(h.get("acao") == "aprovar" for h in f.get("historico") or []):
        f["status"] = "aprovado"
        _gravar(qid, "frame.json", f)
    return f


def _exigir_frame(qid: str) -> dict:
    f = frame(qid)
    if not f:
        raise FileNotFoundError(f"{qid}: frame.json não existe. Rode: python run.py frame {qid} induzir")
    return f


def _cat(f: dict, ref) -> dict:
    """Localiza categoria por código (int/str numérica) ou por nome (case-insensitive)."""
    for c in f["categorias"]:
        if str(c["codigo"]) == str(ref) or V.norm(c["nome"]) == V.norm(ref):
            return c
    raise KeyError(f"categoria não encontrada: {ref!r}")


def classificacao_iniciada(qid: str) -> bool:
    return (pasta(qid) / "codificacao.json").exists()


def _status_apos_edicao(qid: str) -> str:
    """Aprovar as categorias é uma etapa só, antes da PRIMEIRA classificação. Depois disso, editar
    (renomear, mesclar, excluir, ajustar com a IA) vale na hora e não trava a classificação: as
    respostas já são remapeadas, e as próximas chamadas à IA usam a lista nova."""
    return "aprovado" if classificacao_iniciada(qid) else "rascunho"


def _registrar(f: dict, acao: str, **kw) -> None:
    f.setdefault("historico", []).append({"quando": datetime.now().isoformat(timespec="seconds"), "acao": acao, **kw})
    if f.get("status") == "aprovado":
        f["status"] = _status_apos_edicao(f["pergunta"]) if f.get("pergunta") else "rascunho"


def renomear(qid: str, ref, novo_nome: str, nova_definicao: str | None = None) -> dict:
    f = _exigir_frame(qid)
    c = _cat(f, ref)
    antigo = c["nome"]
    c["nome"] = novo_nome.strip()
    if nova_definicao:
        c["definicao"] = nova_definicao.strip()
    _registrar(f, "renomear", codigo=c["codigo"], de=antigo, para=c["nome"])
    _gravar(qid, "frame.json", f)
    return f


def fundir(qid: str, destino, *origens) -> dict:
    """Funde as categorias `origens` em `destino` (exemplos são somados; códigos das origens somem).
    Se já houver codificação, os códigos fundidos são remapeados em codificacao.json."""
    f = _exigir_frame(qid)
    d = _cat(f, destino)
    remap = {}
    for o in origens:
        c = _cat(f, o)
        if c is d:
            continue
        if c.get("fixa"):
            raise ValueError("categorias fixas (Outros, NS/NR) não podem ser fundidas")
        d["exemplos"] = (d.get("exemplos") or []) + (c.get("exemplos") or [])
        remap[c["codigo"]] = d["codigo"]
        f["categorias"].remove(c)
    _registrar(f, "fundir", destino=d["codigo"], origens=list(remap))
    _gravar(qid, "frame.json", f)
    _remapear_codificacao(qid, remap)
    return f


def adicionar(qid: str, nome: str, definicao: str = "") -> dict:
    f = _exigir_frame(qid)
    usados = [c["codigo"] for c in f["categorias"] if not c.get("fixa")]
    codigo = (max(usados) + 1) if usados else 1
    f["categorias"].insert(len(usados), {"codigo": codigo, "nome": nome.strip(), "definicao": definicao.strip(), "exemplos": [], "fixa": False})
    _registrar(f, "adicionar", codigo=codigo, nome=nome)
    _gravar(qid, "frame.json", f)
    return f


def remover(qid: str, ref) -> dict:
    """Remove a categoria; respostas já codificadas nela caem em 'Outros'."""
    f = _exigir_frame(qid)
    c = _cat(f, ref)
    if c.get("fixa"):
        raise ValueError("categorias fixas não podem ser removidas")
    f["categorias"].remove(c)
    _registrar(f, "remover", codigo=c["codigo"], nome=c["nome"])
    _gravar(qid, "frame.json", f)
    _remapear_codificacao(qid, {c["codigo"]: CODIGO_OUTROS})
    return f


def aprovar(qid: str) -> dict:
    f = _exigir_frame(qid)
    f["status"] = "aprovado"
    f["aprovado_em"] = datetime.now().isoformat(timespec="seconds")
    f.setdefault("historico", []).append({"quando": f["aprovado_em"], "acao": "aprovar"})
    _gravar(qid, "frame.json", f)
    return f


def _remapear_codificacao(qid: str, remap: dict) -> None:
    if not remap:
        return
    cod = _ler(qid, "codificacao.json")
    if not cod:
        return
    for r in cod["itens"]:
        for campo in ("primaria", "secundaria"):
            if r.get(campo) in remap:
                r[campo] = remap[r[campo]]
        if r.get("secundaria") == r.get("primaria"):
            r["secundaria"] = None
    cod["status"] = "rascunho"
    _gravar(qid, "codificacao.json", cod)


def texto_frame(qid: str) -> str:
    f = _exigir_frame(qid)
    linhas = [f"{qid} - frame [{f['status']}] {f.get('enunciado') or ''}"]
    for c in f["categorias"]:
        ex = "; ".join(c.get("exemplos") or [])
        linhas.append(f"  {c['codigo']:>3}  {c['nome']:<40} {c['definicao']}" + (f"  ex.: {ex}" if ex else ""))
    return "\n".join(linhas)
