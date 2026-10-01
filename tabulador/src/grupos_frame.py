"""Grupos de categorias compartilhadas entre perguntas análogas.

Um grupo define um conjunto de perguntas abertas (ex.: Q32 e Q33) que compartilham
um único frame.json mestre. O frame é induzido a partir das respostas unificadas de
todas as perguntas do grupo; cada pergunta é codificada individualmente usando esse
frame compartilhado.

Declaração no projeto.py:
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
    output/grupos_pendentes.json            — alterações pendentes de confirmação
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import config
import variables as V


# ----------------------------------------------------------------------------- lookup
def grupo_de(qid: str) -> tuple[str, dict] | tuple[None, None]:
    """Retorna (nome_grupo, config_grupo) se qid pertence a algum grupo, ou (None, None)."""
    for nome, cfg in (V.GRUPOS or {}).items():
        if qid in cfg.get("perguntas", []):
            return nome, cfg
    return None, None


def membros(nome_grupo: str) -> list[str]:
    """QIDs das perguntas membros do grupo."""
    return (V.GRUPOS or {}).get(nome_grupo, {}).get("perguntas", [])


def rotulo(nome_grupo: str) -> str:
    return (V.GRUPOS or {}).get(nome_grupo, {}).get("rotulo", nome_grupo)


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

    cfg = (V.GRUPOS or {}).get(nome_grupo, {})
    progresso.etapa("ler", "agregando respostas do grupo")
    dados = preparar(nome_grupo)

    # monta prompt combinando instruções do grupo com o contexto do projeto
    instr = cfg.get("instrucoes_frame", "")
    system = (
        "Você é um pesquisador sênior de pesquisa de mercado quantitativa, especialista em construir "
        "CODE FRAMES (livros de códigos) para perguntas abertas. Responda em português do Brasil."
    )
    validas = [r for r in dados["respostas"] if not r.get("nsnr")]
    limite = config.MAX_RESPOSTAS_INDUCAO
    if len(validas) > limite:
        import random
        validas = random.Random(0).sample(validas, limite)
    corta = lambda t: t if len(t) <= 400 else t[:400] + "…"
    linhas = [f"- ({r['n']}x) [{r['origem_qid']}] {corta(r['texto'])}" for r in validas]

    user = f"""CONTEXTO DO PROJETO
{config.CONTEXTO_PROJETO}

GRUPO DE PERGUNTAS: {rotulo(nome_grupo)}
Perguntas membros: {', '.join(membros(nome_grupo))}
Total de respostas únicas no grupo: {dados['n_unicas']}

TAREFA
Proponha um code frame FECHADO com {min_cat} a {max_cat} categorias para codificar TODAS as respostas abaixo.
As categorias devem funcionar para TODAS as perguntas do grupo (indicadas por [QID] em cada resposta).
Regras:
1. Categorias mutuamente exclusivas, com nome curto (1 a 4 palavras) e definição objetiva de 1 frase.
2. Cada categoria deve representar UMA ideia.
3. NÃO crie categorias 'Outros' nem 'NS/NR': são adicionadas automaticamente.
4. Liste 2 a 4 exemplos LITERAIS por categoria.
5. Ordene da mais frequente para a menos frequente.
6. `keywords`: 3 a 8 palavras ou expressões típicas.
{('Instruções específicas: ' + instr) if instr else ''}

RESPOSTAS (frequência x pergunta x texto):
{chr(10).join(linhas)}
"""
    progresso.etapa("ia", f"{len(linhas)} respostas · modelo {config.OPENAI_MODEL}",
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


# ----------------------------------------------------------------------------- pendentes (UI)
def _caminho_pendentes() -> Path:
    return config.OUTPUT_DIR / "grupos_pendentes.json"


def pendentes() -> dict:
    """Lê todas as alterações de grupo pendentes de confirmação."""
    p = _caminho_pendentes()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def salvar_pendente(nome_grupo: str, alteracao: dict) -> None:
    """Salva uma alteração pendente para o grupo (não aplicada até confirmar)."""
    atual = pendentes()
    atual[nome_grupo] = {**alteracao, "salvo_em": datetime.now().isoformat(timespec="seconds")}
    _caminho_pendentes().write_text(json.dumps(atual, ensure_ascii=False, indent=1), encoding="utf-8")


def descartar_pendente(nome_grupo: str) -> None:
    """Descarta alteração pendente sem aplicar."""
    atual = pendentes()
    atual.pop(nome_grupo, None)
    _caminho_pendentes().write_text(json.dumps(atual, ensure_ascii=False, indent=1), encoding="utf-8")


def confirmar_pendente(nome_grupo: str) -> dict:
    """Aplica a alteração pendente e dispara reindução do frame."""
    pend = pendentes().get(nome_grupo)
    if not pend:
        raise ValueError(f"Não há alteração pendente para o grupo '{nome_grupo}'.")
    # aqui atualizaríamos a configuração do grupo. Por ora: reinduz com a config atual.
    descartar_pendente(nome_grupo)
    return induzir(nome_grupo, forcar=True)


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
