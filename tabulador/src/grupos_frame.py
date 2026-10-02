"""Grupos de categorias compartilhadas entre perguntas análogas.

Um grupo define um conjunto de perguntas abertas (ex.: Q32 e Q33) que compartilham
um único frame.json mestre. O frame é induzido a partir das respostas unificadas de
todas as perguntas do grupo; cada pergunta é codificada individualmente usando esse
frame compartilhado.

Declaração inicial no projeto.py (a aba "Grupos de perguntas" edita depois, e a edição fica em
output/grupos_config.json, que passa a valer no lugar do projeto.py):
    GRUPOS = {
        "motivo_troca": {
            "rotulo": "Motivo para trocar de escola",
            "perguntas": ["Q32", "Q33"],
            "instrucoes_frame": "...",
        }
    }

Arquivos gerados:
    output/grupos/<nome>/frame.json         — frame mestre compartilhado
    output/grupos/<nome>/frame_proposto.json
    output/grupos/<nome>/respostas.json     — respostas unificadas (campo origem_qid)
    output/grupos_config.json               — grupos editados na aba (substitui GRUPOS do projeto.py)
    output/grupos/_dissolvidos/<nome>_<data>/ — pasta de um grupo dissolvido (guardada, não apagada)
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

import config
import variables as V


# ----------------------------------------------------------------------------- configuração dos grupos
def _caminho_config() -> Path:
    return config.OUTPUT_DIR / "grupos_config.json"


def todos() -> dict:
    """Grupos em vigor: o que foi editado na aba (grupos_config.json) ou, se nunca foi, o GRUPOS do projeto.py."""
    p = _caminho_config()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {n: dict(c) for n, c in (V.GRUPOS or {}).items()}


def _gravar_config(grupos: dict) -> None:
    p = _caminho_config()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(grupos, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def grupo_de(qid: str) -> tuple[str, dict] | tuple[None, None]:
    """Retorna (nome_grupo, config_grupo) se qid pertence a algum grupo, ou (None, None)."""
    for nome, cfg in todos().items():
        if qid in cfg.get("perguntas", []):
            return nome, cfg
    return None, None


def grupo_efetivo(qid: str) -> tuple[str, dict] | tuple[None, None]:
    """Como grupo_de, mas só quando o grupo JÁ TEM quadro. Enquanto não tem, a pergunta segue com o
    quadro dela: agrupar não pode esconder categorias já aprovadas nem o trabalho conferido sobre elas."""
    nome, cfg = grupo_de(qid)
    return (nome, cfg) if nome and frame(nome) else (None, None)


def membros(nome_grupo: str) -> list[str]:
    """QIDs das perguntas membros do grupo."""
    return todos().get(nome_grupo, {}).get("perguntas", [])


def rotulo(nome_grupo: str) -> str:
    return todos().get(nome_grupo, {}).get("rotulo", nome_grupo)


# ----------------------------------------------------------------------------- pastas / IO
def pasta_grupos() -> Path:
    p = config.OUTPUT_DIR / "grupos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pasta(nome_grupo: str) -> Path:
    p = pasta_grupos() / nome_grupo
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ler_grupo(nome_grupo: str, nome_arquivo: str) -> dict | None:
    """Lê arquivo JSON da pasta do grupo. Retorna None se não existir."""
    import nuvem
    if nuvem.ativa():
        # por ora a nuvem não suporta grupos: fallback para arquivo local
        pass
    p = pasta(nome_grupo) / nome_arquivo
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _gravar_grupo(nome_grupo: str, nome_arquivo: str, dados: dict) -> None:
    import nuvem
    if nuvem.ativa():
        pass  # nuvem não suporta grupos ainda; grava local
    (pasta(nome_grupo) / nome_arquivo).write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ----------------------------------------------------------------------------- respostas unificadas
def preparar(nome_grupo: str) -> dict:
    """Agrega respostas de todas as perguntas do grupo em um respostas.json unificado.
    Cada resposta ganha o campo origem_qid para rastreabilidade.
    Chaves de deduplicação são (origem_qid, chave_texto) para não misturar perguntas."""
    import codeframe as CF

    qids = membros(nome_grupo)
    if not qids:
        raise ValueError(f"Grupo '{nome_grupo}' não tem perguntas declaradas.")

    todas: list[dict] = []
    proximo_rid = 1

    for qid in qids:
        dados_q = CF.preparar(qid)
        for r in dados_q.get("respostas", []):
            entrada = dict(r)
            entrada["origem_qid"] = qid
            # RID do grupo é sequencial global; o RID original fica em rid_origem
            entrada["rid_origem"] = entrada.pop("rid")
            entrada["rid"] = proximo_rid
            proximo_rid += 1
            todas.append(entrada)

    dados = {
        "grupo": nome_grupo,
        "rotulo": rotulo(nome_grupo),
        "perguntas": qids,
        "n_total": sum(r["n"] for r in todas),
        "n_unicas": len(todas),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "respostas": todas,
    }
    _gravar_grupo(nome_grupo, "respostas.json", dados)
    return dados


def respostas(nome_grupo: str) -> dict:
    """Respostas unificadas já preparadas (ou prepara agora, se ainda não existem)."""
    return _ler_grupo(nome_grupo, "respostas.json") or preparar(nome_grupo)


# ----------------------------------------------------------------------------- frame mestre
def frame(nome_grupo: str) -> dict | None:
    """Lê o frame mestre do grupo."""
    return _ler_grupo(nome_grupo, "frame.json")


def induzir(nome_grupo: str, min_cat: int = 6, max_cat: int = 15, forcar: bool = False) -> dict:
    """Induz o frame mestre do grupo a partir das respostas unificadas de todas as perguntas."""
    import codeframe as CF
    import llm
    import progresso

    atual = frame(nome_grupo)
    if atual and atual.get("status") == "aprovado" and not forcar:
        raise RuntimeError(
            f"Grupo '{nome_grupo}': frame já aprovado. Use --forcar para reinduzir."
        )

    cfg = todos().get(nome_grupo, {})
    progresso.etapa("ler", "agregando respostas do grupo")
    dados = preparar(nome_grupo)

    # monta prompt combinando instruções do grupo com o contexto do projeto
    instr = cfg.get("instrucoes_frame", "")
    system = (
        "Você é um pesquisador sênior de pesquisa de mercado quantitativa, especialista em construir "
        "CODE FRAMES (livros de códigos) para perguntas abertas. Responda em português do Brasil."
    )
    escolhidas, cobertura = CF._amostra_inducao(dados)
    corta = lambda t: t if len(t) <= 400 else t[:400] + "…"
    linhas = [f"- ({r['n']}x) [{r['origem_qid']}] {corta(r['texto'])}" for r in escolhidas]
    lidas = " · ".join(f"{q}: {c['lidas']} de {c['unicas']}" for q, c in cobertura["perguntas"].items())

    user = f"""CONTEXTO DO PROJETO
{config.CONTEXTO_PROJETO}

GRUPO DE PERGUNTAS: {rotulo(nome_grupo)}
Perguntas membros: {', '.join(membros(nome_grupo))}
Total de respostas únicas no grupo: {dados['n_unicas']}
Respostas lidas por pergunta (únicas): {lidas}{' — AMOSTRA' if cobertura['amostra'] else ''}

TAREFA
Proponha um code frame FECHADO com {min_cat} a {max_cat} categorias para codificar TODAS as respostas abaixo.
As categorias devem funcionar para TODAS as perguntas do grupo (indicadas por [QID] em cada resposta).
Regras:
1. Categorias mutuamente exclusivas, com nome curto (1 a 4 palavras) e definição objetiva de 1 frase.
2. Cada categoria avalia UM atributo/ideia; não junte conceitos distintos no mesmo nome ("Preço e Atendimento" é proibido).
3. NÃO crie categorias 'Outros' nem 'NS/NR': são adicionadas automaticamente.
4. Liste 2 a 4 exemplos LITERAIS por categoria.
5. Ordene da mais frequente para a menos frequente.
6. `keywords`: 3 a 8 palavras ou expressões típicas.
{('Instruções específicas: ' + instr) if instr else ''}

RESPOSTAS (frequência x pergunta x texto):
{chr(10).join(linhas)}
"""
    progresso.etapa("ia", f"{lidas} · modelo {config.OPENAI_MODEL}",
                    estimativa=progresso.tempo_medio("frame_"))
    saida = llm.chamar_json(system, user, CF.SCHEMA_FRAME, nome=f"frame_grupo_{nome_grupo}")
    progresso.etapa("gravar", f"{len(saida['categorias'])} categorias")

    categorias = []
    for i, c in enumerate(saida["categorias"], start=1):
        categorias.append({
            "codigo": i, "nome": c["nome"].strip(), "definicao": c["definicao"].strip(),
            "exemplos": c.get("exemplos", []),
            "keywords": CF._limpar_keywords(c.get("keywords")), "fixa": False,
        })

    f = {
        "grupo": nome_grupo,
        "rotulo": rotulo(nome_grupo),
        "perguntas": membros(nome_grupo),
        "status": "rascunho",
        "fixo": False,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "modelo": config.OPENAI_MODEL,
        "raciocinio": saida.get("raciocinio", ""),
        "cobertura": cobertura,
        "categorias": categorias + [dict(f_) for f_ in CF.FIXAS],
        "historico": [],
        "versao": 1,
    }
    _gravar_grupo(nome_grupo, "frame_proposto.json", f)
    _gravar_grupo(nome_grupo, "frame.json", f)
    return f


def aprovar(nome_grupo: str) -> dict:
    """Aprova o frame mestre do grupo."""
    f = frame(nome_grupo)
    if not f:
        raise FileNotFoundError(f"Grupo '{nome_grupo}': frame.json não existe.")
    f["status"] = "aprovado"
    f["aprovado_em"] = datetime.now().isoformat(timespec="seconds")
    f.setdefault("historico", []).append({"quando": f["aprovado_em"], "acao": "aprovar"})
    _gravar_grupo(nome_grupo, "frame.json", f)
    return f


# ----------------------------------------------------------------------------- administração (aba Grupos)
def _slug(rotulo_: str, existentes) -> str:
    base = unicodedata.normalize("NFKD", rotulo_).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_") or "grupo"
    nome, i = base, 2
    while nome in existentes:
        nome, i = f"{base}_{i}", i + 1
    return nome


def _situacao(qid: str) -> dict:
    """O que a pergunta já tem de trabalho feito (para avisar antes de mexer no grupo)."""
    import codeframe as CF
    import coding as CD
    r = CD.resumo_revisao(qid)
    return {"n_cod": r["n_codificadas"], "n_rev": r["n_revisadas"], "frame_proprio": CF._existe(qid, "frame.json")}


def _respondentes(qid: str) -> set:
    import codeframe as CF
    ids: set = set()
    for r in (CF._ler(qid, "respostas.json") or {}).get("respostas", []):
        ids.update(r.get("respondent_ids") or [])
    return ids


def sobreposicao(a: str, b: str) -> float | None:
    """Fração de quem respondeu a menos respondida das duas que também respondeu a outra
    (0 = ninguém respondeu as duas, ou seja, bases excludentes). None se faltar leitura."""
    ia, ib = _respondentes(a), _respondentes(b)
    menor = min(len(ia), len(ib))
    return len(ia & ib) / menor if menor else None


def sugerir(limite: float = 0.05, minimo: int = 30) -> list[dict]:
    """Pares de perguntas ainda sem grupo cujas bases quase não se cruzam (as pessoas respondem uma OU
    outra) — o sinal de que são a mesma pergunta aplicada a bases diferentes e podem dividir categorias."""
    livres = [q for q in V.perguntas_codificaveis() if not grupo_de(q)[0]]
    resp = {q: _respondentes(q) for q in livres}
    out = []
    for i, a in enumerate(livres):
        for b in livres[i + 1:]:
            menor = min(len(resp[a]), len(resp[b]))
            if menor < minimo:
                continue
            em_comum = len(resp[a] & resp[b])
            if em_comum / menor <= limite:
                out.append({"perguntas": [a, b], "em_comum": em_comum, "pct": round(em_comum / menor, 4)})
    return sorted(out, key=lambda x: x["pct"])


def impacto(nome: str | None, rotulo_: str, perguntas: list[str], instrucoes: str = "") -> dict:
    """Confere a edição ANTES de gravar. `erros` impedem salvar; `avisos` (nivel 'alto' ou 'info')
    descrevem o que o trabalho já feito vai sofrer — a tela mostra e pede confirmação."""
    erros, avisos = [], []
    grupos = todos()
    atual = grupos.get(nome, {}) if nome else {}
    antes, depois = list(atual.get("perguntas", [])), list(dict.fromkeys(perguntas))

    if not (rotulo_ or "").strip():
        erros.append("Dê um nome ao grupo.")
    if len(depois) < 2:
        erros.append("Um grupo precisa de pelo menos 2 perguntas.")
    validas = set(V.perguntas_codificaveis())
    for q in depois:
        if q not in validas:
            erros.append(f"{q} não é uma pergunta aberta a categorizar.")
        outro, _ = grupo_de(q)
        if outro and outro != nome:
            erros.append(f"{q} já está no grupo '{rotulo(outro)}'. Tire-a de lá primeiro.")
    if erros:
        return {"erros": erros, "avisos": []}

    entrando = [q for q in depois if q not in antes]
    saindo = [q for q in antes if q not in depois]
    f = frame(nome) if nome else None

    for q in entrando:  # perguntas de um grupo costumam ter bases excludentes: avisa quando não é o caso
        for outra in depois:
            sob = sobreposicao(q, outra) if outra != q and (outra not in entrando or outra > q) else None
            if sob is not None and sob > 0.2:
                avisos.append({"nivel": "alto", "msg": (
                    f"{q} e {outra} foram respondidas pelas mesmas pessoas ({sob:.0%} de quem respondeu a menor das duas). "
                    f"Grupos funcionam melhor com perguntas de bases diferentes (quem responde uma não responde a outra); "
                    f"confira se juntar as duas é mesmo o que você quer.")})
    if entrando:
        avisos.append({"nivel": "alto", "msg": (
            "Perguntas de grupo ainda não permitem renomear, fundir, remover, adicionar categoria nem pedir ajuste à IA "
            "(só gerar e aprovar o quadro do grupo). Se precisar mexer nas categorias, faça antes de agrupar.")})
    for q in entrando:
        s = _situacao(q)
        if s["n_cod"]:
            avisos.append({"nivel": "alto", "msg": (
                f"{q} já tem {s['n_cod']} respostas classificadas ({s['n_rev']} conferidas por pessoas) com o quadro próprio. "
                f"Ao entrar no grupo ela passa a usar o quadro do grupo: os códigos já gravados continuam, mas podem "
                f"apontar para outra categoria. Reclassifique {q} depois.")})
        elif s["frame_proprio"]:
            avisos.append({"nivel": "info", "msg": f"{q} tem um quadro próprio; ele fica guardado, mas só volta a valer se {q} sair do grupo."})
        if not f and s["frame_proprio"]:
            avisos.append({"nivel": "info", "msg": f"O grupo ainda não tem quadro: {q} continua com o quadro próprio até o quadro do grupo ser criado."})
    for q in saindo:
        s = _situacao(q)
        if s["n_cod"]:
            volta = ("Ela volta ao quadro próprio, que ainda existe." if s["frame_proprio"]
                     else "Ela não tem quadro próprio: vai ficar sem categorias e será preciso gerar um quadro para ela.")
            avisos.append({"nivel": "alto", "msg": (
                f"{q} tem {s['n_cod']} respostas classificadas ({s['n_rev']} conferidas por pessoas) com o quadro do grupo. "
                f"Ao sair, {volta}")})
    if f and (entrando or saindo):
        if f.get("status") == "aprovado":
            avisos.append({"nivel": "alto", "msg": "O quadro do grupo está APROVADO. Ao mudar as perguntas ele volta a rascunho e precisa ser aprovado de novo; a classificação das perguntas do grupo fica travada até lá."})
        if entrando:
            avisos.append({"nivel": "info", "msg": "Para o quadro cobrir as respostas das perguntas novas, gere as categorias do grupo de novo (✨ Gerar do zero)."})
    if nome and f and (instrucoes or "") != atual.get("instrucoes_frame", ""):
        avisos.append({"nivel": "info", "msg": "As instruções novas só valem na próxima vez que a IA gerar categorias para o grupo."})
    return {"erros": [], "avisos": avisos}


def salvar(nome: str | None, rotulo_: str, perguntas: list[str], instrucoes: str = "") -> str:
    """Cria (nome=None) ou atualiza um grupo. Quem chama já mostrou os avisos de `impacto`."""
    res = impacto(nome, rotulo_, perguntas, instrucoes)
    if res["erros"]:
        raise ValueError(" ".join(res["erros"]))
    grupos = todos()
    nome = nome or _slug(rotulo_, grupos)
    antes = list(grupos.get(nome, {}).get("perguntas", []))
    depois = list(dict.fromkeys(perguntas))
    grupos[nome] = {"rotulo": rotulo_.strip(), "perguntas": depois, "instrucoes_frame": (instrucoes or "").strip()}
    _gravar_config(grupos)

    f = frame(nome)
    if f:  # o frame guarda cópia do rótulo e dos membros: mantém em dia
        f["rotulo"], f["perguntas"] = rotulo_.strip(), depois
        if antes != depois:
            f.setdefault("historico", []).append({"quando": datetime.now().isoformat(timespec="seconds"), "acao": "membros_alterados", "de": antes, "para": depois})
            if f.get("status") == "aprovado":
                f["status"] = "rascunho"
        _gravar_grupo(nome, "frame.json", f)
    return nome


def dissolver(nome: str) -> list[str]:
    """Desfaz o grupo: as perguntas voltam a ter quadro próprio. A pasta do grupo é guardada, não apagada."""
    grupos = todos()
    if nome not in grupos:
        raise KeyError(f"Grupo '{nome}' não existe.")
    liberadas = list(grupos[nome].get("perguntas", []))
    del grupos[nome]
    _gravar_config(grupos)
    origem = pasta_grupos() / nome
    if origem.exists():
        destino = pasta_grupos() / "_dissolvidos" / f"{nome}_{datetime.now():%Y%m%d_%H%M%S}"
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), str(destino))
    return liberadas


# ----------------------------------------------------------------------------- saúde consolidada
def dossie_consolidado(nome_grupo: str) -> tuple[dict | None, dict[int, dict]]:
    """Retorna (frame, dossie_agregado) com dados de codificação de TODAS as perguntas do grupo."""
    import aprendizado
    import codeframe as CF

    f = frame(nome_grupo)
    if not f:
        return None, {}

    respostas_todas: list[dict] = []
    itens_todos: list[dict] = []

    for qid in membros(nome_grupo):
        resp = (CF._ler(qid, "respostas.json") or {}).get("respostas", [])
        itens = (CF._ler(qid, "codificacao.json") or {}).get("itens", [])
        respostas_todas.extend(resp)
        itens_todos.extend(itens)

    if not itens_todos:
        return f, {}

    return f, aprendizado.dossie_de(f, respostas_todas, itens_todos)


def assimetrias(nome_grupo: str, limiar: float | None = None) -> list[dict]:
    """Alertas de assimetria de distribuição entre perguntas do grupo.
    Dispara quando |pct_QA - pct_QB| > limiar (padrão: SAUDE_ASSIMETRIA_GRUPO_PCT ou 0.15)."""
    import aprendizado
    import codeframe as CF

    if limiar is None:
        try:
            limiar = getattr(V._p(), "SAUDE_ASSIMETRIA_GRUPO_PCT")
        except Exception:  # noqa: BLE001 - projeto não define o limiar; usa padrão
            limiar = 0.15

    f = frame(nome_grupo)
    if not f:
        return []

    qids = membros(nome_grupo)
    if len(qids) < 2:
        return []

    # dossiê por pergunta
    dossies: dict[str, dict[int, dict]] = {}
    for qid in qids:
        resp = (CF._ler(qid, "respostas.json") or {}).get("respostas", [])
        itens = (CF._ler(qid, "codificacao.json") or {}).get("itens", [])
        if itens:
            dossies[qid] = aprendizado.dossie_de(f, resp, itens)

    if len(dossies) < 2:
        return []

    alertas = []
    nomes_cat = {c["codigo"]: c["nome"] for c in f["categorias"]}

    for c in f["categorias"]:
        if c.get("fixa"):
            continue
        cod = c["codigo"]
        pcts = {qid: dossies[qid].get(cod, {}).get("pct", 0.0) for qid in dossies}
        vals = list(pcts.values())
        delta = max(vals) - min(vals)
        if delta >= limiar:
            maior_qid = max(pcts, key=pcts.get)
            menor_qid = min(pcts, key=pcts.get)
            alertas.append({
                "tipo": "assimetria_grupo",
                "codigo": cod,
                "grupo": nome_grupo,
                "msg": (
                    f'A categoria "{nomes_cat.get(cod, cod)}" tem {pcts[maior_qid]:.0%} em {maior_qid} '
                    f'e {pcts[menor_qid]:.0%} em {menor_qid}: as bases respondem de forma muito '
                    f'diferente — verifique se o frame cobre bem ambas.'
                ),
                "delta": round(delta, 4),
                "por_pergunta": pcts,
            })

    return alertas
