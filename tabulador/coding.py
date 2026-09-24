"""Fase 2 - Codificação contra o frame aprovado.

`codificar(qid)`        : classifica cada resposta ÚNICA contra a lista fechada (primária obrigatória,
                          secundária opcional, confiança, justificativa). NS/NR detectados por regex
                          nem vão ao LLM. -> codificacao.json (status 'rascunho')
`exportar_revisao(qid)` : revisao.xlsx com colunas REVISAO_* para o pesquisador sobrescrever.
`importar_revisao(qid)` : lê o xlsx de volta e aplica as correções humanas (origem='humano').
`aprovar(qid)`          : trava a codificação (status 'aprovado').
`aplicar_na_base()`     : grava <QID>_COD1/<QID>_COD2 (+ nomes) de todas as perguntas aprovadas na base.
"""
from __future__ import annotations

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd

import codeframe as CF
import config
import progresso
import llm
import load
import variables as V

LIMIAR_CONFIANCA = 0.6

SCHEMA_CODIFICACAO = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "codificacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "rid": {"type": "integer"},
                    "primaria": {"type": "integer"},
                    "secundaria": {"type": ["integer", "null"]},
                    "confianca": {"type": "number"},
                    "justificativa": {"type": "string"},
                },
                "required": ["rid", "primaria", "secundaria", "confianca", "justificativa"],
            },
        }
    },
    "required": ["codificacoes"],
}


def _prompt(qid: str, frame: dict, enunciado: str, lote: list[dict]) -> tuple[str, str]:
    system = (
        "Você é um codificador sênior de pesquisa de mercado. Classifica respostas abertas contra um "
        "code frame FECHADO e aprovado. Nunca inventa categorias. Responde em português do Brasil."
    )
    cats = "\n".join(
        f"  {c['codigo']}: {c['nome']} - {c['definicao']}" + (f" (ex.: {'; '.join(c['exemplos'][:3])})" if c.get("exemplos") else "")
        for c in frame["categorias"]
    )
    def _linha(r):
        obs = r.get("comentario")
        return f"  rid {r['rid']}: \"{r['texto']}\"" + (f"   [OBSERVAÇÃO DO PESQUISADOR - siga obrigatoriamente: {obs}]" if obs else "")

    linhas = "\n".join(_linha(r) for r in lote)
    instr = CF.instrucoes_completas(qid)
    user = f"""CONTEXTO DO PROJETO
{config.CONTEXTO_PROJETO}

PERGUNTA ({qid}): {enunciado}

CODE FRAME APROVADO (use SOMENTE estes códigos):
{cats}

REGRAS
1. `primaria` = a categoria da PRIMEIRA ideia/ideia principal da resposta (obrigatória).
2. `secundaria` = a segunda ideia claramente distinta, se houver; caso contrário null. Nunca igual à primária.
3. Use {CF.CODIGO_OUTROS} (Outros) só quando a resposta é válida mas não cabe em nenhuma categoria.
4. Use {CF.CODIGO_NSNR} (NS/NR) para 'não sei', 'não conheço', respostas vazias ou sem sentido.
5. `confianca` de 0 a 1: 1.0 = literal/inequívoco; < 0.6 = ambíguo, precisa de revisão humana.
6. `justificativa` curta (até 15 palavras).
7. Retorne EXATAMENTE um item por rid, na mesma ordem.
{('Instruções específicas desta pergunta: ' + instr) if instr else ''}

RESPOSTAS
{linhas}
"""
    return system, user


# andamento da operação longa em curso (lido pela interface em /api/progresso)
PROGRESSO: dict = {"ativo": False}


def _progresso(**kw) -> None:
    PROGRESSO.update(kw)


def _chamar_lote(qid: str, frame: dict, enunciado: str, pendentes: list[dict], itens: dict, codigos_validos: dict) -> dict:
    """Codifica `pendentes` via LLM em lotes (config.LLM_PARALELO chamadas simultâneas) e preenche
    `itens` (rid -> item). Lote que falha vira origem 'erro' (alerta); se TODOS falharem, levanta o erro.
    Se algum lote falhar por cota/limite do provedor esgotado, os lotes ainda não iniciados são
    cancelados (não vale insistir) e ficam pendentes — não entram em `itens` nem viram 'erro' — para
    serem retomados na próxima classificação. Retorna {'limite_atingido', 'nao_tentados'}."""
    lotes = [pendentes[i:i + config.LLM_LOTE] for i in range(0, len(pendentes), config.LLM_LOTE)]
    if not lotes:
        return {"limite_atingido": False, "nao_tentados": 0}
    _progresso(ativo=True, qid=qid, feitos=0, total=len(pendentes), erros=0, limite_atingido=False)
    par = min(config.paralelo(), len(lotes))
    media = progresso.tempo_medio("code_")
    progresso.atualizar(feitos=0, total=len(pendentes), lotes_feitos=0, lotes_total=len(lotes), erros=0, limite_atingido=False,
                        paralelo=par, tamanho_lote=config.LLM_LOTE)
    progresso.etapa("ia", f"{len(pendentes)} respostas em {len(lotes)} lote(s) de até {config.LLM_LOTE} · {par} chamada(s) ao mesmo tempo · modelo {config.OPENAI_MODEL}",
                    estimativa=media * -(-len(lotes) // par) if media else None)
    t_ini = time.time()

    def _um(k_lote):
        k, lote = k_lote
        system, user = _prompt(qid, frame, enunciado, lote)
        return llm.chamar_json(system, user, SCHEMA_CODIFICACAO, nome=f"code_{qid}_{k + 1}")

    resultados, falhas = {}, []
    limite_atingido = False
    with ThreadPoolExecutor(max_workers=config.paralelo()) as ex:
        futuros = {ex.submit(_um, (k, lote)): k for k, lote in enumerate(lotes)}
        for fut in as_completed(futuros):
            k = futuros[fut]
            if fut.cancelled():
                continue  # cancelado antes de começar: fica pendente, não conta como tentado
            try:
                resultados[k] = fut.result()
            except Exception as e:  # noqa: BLE001 - registrado como erro do lote
                falhas.append(e)
                resultados[k] = None
                if not limite_atingido and llm.e_limite_ou_cota(e):
                    limite_atingido = True
                    for outro in futuros:  # só cancela quem ainda não começou a rodar
                        if outro is not fut:
                            outro.cancel()
            _progresso(feitos=PROGRESSO.get("feitos", 0) + len(lotes[k]), erros=len(falhas), limite_atingido=limite_atingido)
            progresso.atualizar(feitos=PROGRESSO["feitos"], lotes_feitos=progresso.ESTADO.get("lotes_feitos", 0) + 1,
                                erros=len(falhas), limite_atingido=limite_atingido)
            progresso.evento(f"Lote {k + 1} de {len(lotes)} {'com ERRO' if resultados[k] is None else 'concluído'} "
                             f"({len(lotes[k])} respostas) · {PROGRESSO['feitos']} de {len(pendentes)} prontas em {time.time() - t_ini:.0f} s")
    progresso.etapa("gravar", "juntando as respostas classificadas e salvando")
    _progresso(ativo=False)
    nao_tentados = sum(len(lote) for k, lote in enumerate(lotes) if k not in resultados)
    if falhas and len(falhas) == len(resultados) and resultados:
        raise falhas[0]
    if not resultados and limite_atingido:
        # nenhum lote chegou a rodar (limite já esgotado desde o primeiro) — nada para gravar aqui
        return {"limite_atingido": True, "nao_tentados": nao_tentados}
    for k, lote in enumerate(lotes):
        if k not in resultados:
            continue  # cancelado por limite: permanece pendente para a próxima tentativa
        saida = resultados[k]
        if saida is None:
            for r in lote:
                itens[r["rid"]] = {"rid": r["rid"], "primaria": CF.CODIGO_OUTROS, "secundaria": None, "confianca": 0.0,
                                   "justificativa": f"erro na chamada à IA: {str(falhas[0])[:120]}", "origem": "erro"}
                if r.get("comentario"):
                    itens[r["rid"]]["comentario"] = r["comentario"]
            continue
        devolvidos = {c["rid"]: c for c in saida["codificacoes"]}
        for r in lote:
            c = devolvidos.get(r["rid"])
            if c is None:
                itens[r["rid"]] = {"rid": r["rid"], "primaria": CF.CODIGO_OUTROS, "secundaria": None, "confianca": 0.0,
                                   "justificativa": "LLM não devolveu esta resposta", "origem": "erro"}
                continue
            prim = c["primaria"] if c["primaria"] in codigos_validos else CF.CODIGO_OUTROS
            sec = c["secundaria"] if c["secundaria"] in codigos_validos and c["secundaria"] != prim else None
            conf = float(c["confianca"])
            if c["primaria"] not in codigos_validos:
                conf = 0.0
            novo = {"rid": r["rid"], "primaria": prim, "secundaria": sec, "confianca": round(max(0.0, min(1.0, conf)), 2),
                    "justificativa": c.get("justificativa", ""), "origem": "llm"}
            if r.get("comentario"):
                novo["comentario"] = r["comentario"]
                novo["origem"] = "llm+comentario"
                novo["comentario_aplicado_em"] = datetime.now().isoformat(timespec="seconds")
            itens[r["rid"]] = novo
    return {"limite_atingido": limite_atingido, "nao_tentados": nao_tentados}


def _protegido(item: dict, codigos_validos: dict) -> bool:
    """Correção ou confirmação do pesquisador: não é refeita pela IA em 'Reclassificar tudo'."""
    return (item.get("origem") == "humano" or bool(item.get("validado"))) and item.get("primaria") in codigos_validos


def _amostra(pendentes: list[dict], limite: int) -> list[dict]:
    """Amostra para validar a classificação antes de rodar tudo: metade das mais frequentes +
    sorteio fixo (semente 0) das demais, para cobrir respostas típicas e variadas."""
    if limite >= len(pendentes):
        return pendentes
    ordem = sorted(pendentes, key=lambda r: (-r["n"], r["rid"]))
    topo = ordem[: limite // 2]
    resto = ordem[limite // 2:]
    return topo + random.Random(0).sample(resto, limite - len(topo))


def codificar(qid: str, forcar: bool = False, preservar_humano: bool = True,
              limite: int | None = None, somente_faltantes: bool = False) -> dict:
    """Codifica as respostas únicas. Se já houver codificação, mantém as correções/confirmações do
    pesquisador e reaproveita os comentários como instrução para o LLM.

    limite            : classifica só uma amostra de `limite` respostas (para validar antes de rodar tudo)
    somente_faltantes : mantém tudo que já foi classificado e envia à IA só o que falta
    """
    frame = CF.frame(qid)
    if not frame or frame.get("status") != "aprovado":
        raise RuntimeError(f"{qid}: frame não aprovado. Rode: python run.py frame {qid} aprovar")
    atual = CF._ler(qid, "codificacao.json")
    if atual and atual.get("status") == "aprovado" and not forcar:
        raise RuntimeError(f"{qid}: codificação já aprovada. Use --forcar para recodificar.")
    progresso.etapa("preparar", "separando NS/NR (por regra) e o que você já conferiu")
    dados = CF.respostas(qid)
    codigos_validos = {c["codigo"]: c for c in frame["categorias"]}
    anteriores = {i["rid"]: i for i in (atual or {}).get("itens", [])}
    itens: dict[int, dict] = {}
    pendentes = []
    for r in dados["respostas"]:
        ant = anteriores.get(r["rid"])
        if ant and somente_faltantes and ant.get("primaria") in codigos_validos:
            itens[r["rid"]] = ant
        elif ant and preservar_humano and _protegido(ant, codigos_validos):
            itens[r["rid"]] = ant
        elif r["nsnr"] and not (ant and ant.get("comentario")):
            itens[r["rid"]] = {"rid": r["rid"], "primaria": CF.CODIGO_NSNR, "secundaria": None, "confianca": 1.0,
                               "justificativa": "NS/NR detectado por regra", "origem": "regra"}
        else:
            pendentes.append(dict(r, comentario=(ant or {}).get("comentario")))
    if limite:
        escolhidos = _amostra(pendentes, int(limite))
        fora = {r["rid"] for r in pendentes} - {r["rid"] for r in escolhidos}
        for rid in fora:  # fora da amostra: mantém a classificação anterior, se houver
            if rid in anteriores and anteriores[rid].get("primaria") in codigos_validos:
                itens[rid] = anteriores[rid]
        pendentes = escolhidos
    info = _chamar_lote(qid, frame, dados.get("enunciado") or V.por_id(qid).get("rotulo"), pendentes, itens, codigos_validos)
    cod = {
        "pergunta": qid,
        "status": "rascunho",
        "modelo": config.OPENAI_MODEL,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "frame_aprovado_em": frame.get("aprovado_em"),
        "itens": [itens[r["rid"]] for r in dados["respostas"] if r["rid"] in itens],
    }
    CF._gravar(qid, "codificacao.json", cod)
    cod["_limite_atingido"] = info["limite_atingido"]
    cod["_nao_tentados"] = info["nao_tentados"]
    return cod


def recodificar(qid: str, rids: list[int] | None = None, apenas_comentados: bool = True, nao_revisados: bool = False) -> dict:
    """Reenvia ao LLM só as respostas escolhidas (por padrão, as que têm comentário do pesquisador
    ainda não aplicado). O comentário vai no prompt como instrução obrigatória.
    nao_revisados=True: todas as já classificadas que o pesquisador ainda não corrigiu/confirmou
    (o 'Reclassificar tudo' da interface; não classifica as que estão fora da amostra)."""
    frame = CF.frame(qid)
    if not frame or frame.get("status") != "aprovado":
        raise RuntimeError(f"{qid}: frame não aprovado")
    cod = codificacao(qid)
    if not cod:
        return codificar(qid)
    dados = CF.respostas(qid)
    itens = {i["rid"]: i for i in cod["itens"]}
    por_rid = {r["rid"]: r for r in dados["respostas"]}
    codigos_validos = {c["codigo"]: c for c in frame["categorias"]}
    if rids is None and nao_revisados:
        rids = [rid for rid, i in itens.items() if i.get("primaria") is not None and i.get("origem") != "regra" and not _protegido(i, codigos_validos)]
    elif rids is None:
        rids = [rid for rid, i in itens.items() if i.get("comentario") and not i.get("comentario_aplicado_em")] if apenas_comentados else list(itens)
    pendentes = [dict(por_rid[rid], comentario=(itens.get(rid) or {}).get("comentario")) for rid in rids if rid in por_rid]
    progresso.etapa("preparar", f"{len(pendentes)} resposta(s) para a IA refazer (o que você corrigiu/confirmou é mantido)")
    if not pendentes:
        cod["_recodificados"] = 0
        return cod
    novos: dict[int, dict] = {}
    info = _chamar_lote(qid, frame, dados.get("enunciado") or V.por_id(qid).get("rotulo"), pendentes, novos, codigos_validos)
    for rid, novo in novos.items():
        itens[rid] = novo
    cod["itens"] = [itens[r["rid"]] for r in dados["respostas"] if r["rid"] in itens]
    cod["status"] = "rascunho"
    cod["recodificado_em"] = datetime.now().isoformat(timespec="seconds")
    CF._gravar(qid, "codificacao.json", cod)
    cod["_recodificados"] = len(novos)
    cod["_limite_atingido"] = info["limite_atingido"]
    cod["_nao_tentados"] = info["nao_tentados"]
    return cod


def atualizar_item(qid: str, rid: int, primaria=None, secundaria="__manter__", comentario="__manter__", validado=None) -> dict:
    """Correção manual de uma resposta (vinda da interface): categoria primária/secundária,
    comentário para a IA e/ou confirmação ('validado': a IA acertou). Mudança de categoria marca
    origem='humano'; correções e confirmações ficam protegidas em reclassificações."""
    frame = CF._exigir_frame(qid)
    cod = codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: ainda não há codificação")
    item = next((i for i in cod["itens"] if i["rid"] == int(rid)), None)
    if item is None:
        # resposta ainda não classificada (fora da amostra): o pesquisador classifica à mão
        if not any(r["rid"] == int(rid) for r in CF.respostas(qid)["respostas"]):
            raise KeyError(f"rid {rid} não existe em {qid}")
        if primaria is None:
            raise ValueError("Esta resposta ainda não foi classificada: escolha a categoria principal primeiro.")
        item = {"rid": int(rid), "primaria": None, "secundaria": None, "confianca": 0.0, "justificativa": "", "origem": None}
        cod["itens"].append(item)
        ordem = {r["rid"]: k for k, r in enumerate(CF.respostas(qid)["respostas"])}
        cod["itens"].sort(key=lambda i: ordem.get(i["rid"], 0))
    anterior = item.get("primaria")
    mudou = False
    if primaria is not None:
        novo = CF._cat(frame, primaria)["codigo"]
        if novo != item["primaria"]:
            item["primaria"] = novo
            mudou = True
    if secundaria != "__manter__":
        novo = None if secundaria in (None, "", "nenhuma") else CF._cat(frame, secundaria)["codigo"]
        if novo != item.get("secundaria"):
            item["secundaria"] = novo
            mudou = True
    if item.get("secundaria") == item["primaria"]:
        item["secundaria"] = None
    if comentario != "__manter__":
        texto = (comentario or "").strip()
        if texto != (item.get("comentario") or ""):
            item["comentario"] = texto or None
            item.pop("comentario_aplicado_em", None)
            if not texto:
                item.pop("comentario", None)
    agora = datetime.now().isoformat(timespec="seconds")
    if mudou:
        if item.get("origem") not in ("humano", None) and "corrigido_de" not in item:
            item["corrigido_de"] = anterior  # a IA tinha classificado diferente (entra na taxa de acerto)
        item["origem"] = "humano"
        item["confianca"] = 1.0
        item["revisado_em"] = agora
        item.pop("validado", None)
    elif validado is not None:
        if validado:
            item["validado"] = True
            item["validado_em"] = agora
        else:
            item.pop("validado", None)
            item.pop("validado_em", None)
    cod["status"] = "rascunho"
    CF._gravar(qid, "codificacao.json", cod)
    return item


def validar(qid: str, rids: list[int], valor: bool = True) -> int:
    """Confirma (ou desfaz a confirmação de) várias respostas de uma vez. Retorna quantas mudaram."""
    cod = codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: ainda não há codificação")
    alvo = {int(r) for r in rids}
    agora = datetime.now().isoformat(timespec="seconds")
    n = 0
    for item in cod["itens"]:
        if item["rid"] not in alvo or item.get("primaria") is None or item.get("origem") == "humano":
            continue
        if valor and not item.get("validado"):
            item["validado"], item["validado_em"] = True, agora
            n += 1
        elif not valor and item.get("validado"):
            item.pop("validado", None)
            item.pop("validado_em", None)
            n += 1
    if n:
        cod["status"] = "rascunho"
        CF._gravar(qid, "codificacao.json", cod)
    return n


def situacao_revisao(item: dict | None) -> str | None:
    if not item or item.get("primaria") is None:
        return None
    if item.get("origem") == "humano":
        return "corrigida"
    if item.get("validado"):
        return "confirmada"
    return "pendente"


def resumo_revisao(qid: str) -> dict:
    """Números do loop de validação: quanto já foi classificado, revisado e a taxa de acerto da IA
    (confirmadas / (confirmadas + corrigidas depois de classificadas pela IA))."""
    dados = CF._ler(qid, "respostas.json") or {"respostas": []}
    cod = codificacao(qid) or {"itens": []}
    itens = {i["rid"]: i for i in cod["itens"] if i.get("primaria") is not None}
    n_unicas = len(dados["respostas"])
    confirmadas = sum(1 for i in itens.values() if situacao_revisao(i) == "confirmada")
    # confirmadas pelo supervisor.py (alta confiança + auditoria) não medem o acerto da IA
    auto = sum(1 for i in itens.values() if situacao_revisao(i) == "confirmada" and i.get("validado_por") == "auto")
    corrigidas = sum(1 for i in itens.values() if situacao_revisao(i) == "corrigida")
    corrigidas_ia = sum(1 for i in itens.values() if situacao_revisao(i) == "corrigida" and "corrigido_de" in i)
    avaliadas = confirmadas - auto + corrigidas_ia
    return {
        "n_unicas": n_unicas,
        "n_codificadas": len(itens),
        "n_faltantes": max(0, n_unicas - len(itens)),
        "n_confirmadas": confirmadas,
        "n_confirmadas_auto": auto,
        "n_corrigidas": corrigidas,
        "n_revisadas": confirmadas + corrigidas,
        "acerto_ia": round((confirmadas - auto) / avaliadas, 3) if avaliadas else None,
        "n_avaliadas_ia": avaliadas,
    }


def codificacao(qid: str) -> dict | None:
    return CF._ler(qid, "codificacao.json")


def alertas_item(item: dict, frame: dict) -> list[str]:
    a = []
    if item["origem"] == "erro":
        a.append("erro LLM")
    if item["confianca"] < LIMIAR_CONFIANCA and item.get("origem") != "humano" and not item.get("validado"):
        a.append(f"confiança baixa ({item['confianca']:.2f})")
    if item["primaria"] == CF.CODIGO_OUTROS and item.get("origem") != "humano" and not item.get("validado"):
        a.append("Outros")
    return a


def tabela(qid: str) -> pd.DataFrame:
    """Une respostas + codificação + nomes de categoria em um DataFrame (uma linha por resposta única)."""
    dados = CF.respostas(qid)
    frame = CF._exigir_frame(qid)
    cod = codificacao(qid)
    nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
    itens = {i["rid"]: i for i in (cod or {}).get("itens", [])}
    linhas = []
    for r in dados["respostas"]:
        i = itens.get(r["rid"], {"primaria": None, "secundaria": None, "confianca": None, "justificativa": "", "origem": None, "comentario": None})
        linhas.append({
            "rid": r["rid"], "texto": r["texto"], "n": r["n"], "nsnr_regra": r["nsnr"],
            "primaria": i["primaria"], "primaria_nome": nomes.get(i["primaria"]),
            "secundaria": i["secundaria"], "secundaria_nome": nomes.get(i["secundaria"]),
            "confianca": i["confianca"], "justificativa": i["justificativa"], "origem": i["origem"],
            "comentario": i.get("comentario"), "comentario_pendente": bool(i.get("comentario")) and not i.get("comentario_aplicado_em"),
            "alertas": "; ".join(alertas_item(i, frame)) if i["primaria"] is not None else "não codificado",
            "respondent_ids": r["respondent_ids"],
            "revisao": situacao_revisao(i),
            "validado_por": i.get("validado_por"),
            "corrigido_de_nome": nomes.get(i.get("corrigido_de")) if i.get("corrigido_de") is not None else None,
        })
    return pd.DataFrame(linhas)


def exportar_revisao(qid: str):
    df = tabela(qid).drop(columns=["respondent_ids", "comentario", "comentario_pendente", "revisao", "corrigido_de_nome"])
    df["REVISAO_PRIMARIA"] = None
    df["REVISAO_SECUNDARIA"] = None
    df["COMENTARIO"] = None
    frame = CF._exigir_frame(qid)
    legenda = pd.DataFrame([{"codigo": c["codigo"], "nome": c["nome"], "definicao": c["definicao"]} for c in frame["categorias"]])
    p = CF.pasta(qid) / "revisao.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        df.sort_values(["confianca", "n"], ascending=[True, False]).to_excel(xw, sheet_name="revisao", index=False)
        legenda.to_excel(xw, sheet_name="frame", index=False)
        ws = xw.sheets["revisao"]
        ws.freeze_panes = "C2"
        for col, largura in {"B": 60, "J": 45, "L": 30, "M": 18, "N": 18, "O": 30}.items():
            ws.column_dimensions[col].width = largura
    return p


def importar_revisao(qid: str) -> dict:
    p = CF.pasta(qid) / "revisao.xlsx"
    if not p.exists():
        raise FileNotFoundError(f"{qid}: revisao.xlsx não existe. Rode: python run.py code {qid} exportar")
    frame = CF._exigir_frame(qid)
    cod = codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: não há codificação para revisar")
    rev = pd.read_excel(p, sheet_name="revisao")
    itens = {i["rid"]: i for i in cod["itens"]}
    n_alt = 0
    for _, linha in rev.iterrows():
        rid = int(linha["rid"])
        item = itens.get(rid)
        if item is None:
            continue
        mudou = False
        for campo, col in (("primaria", "REVISAO_PRIMARIA"), ("secundaria", "REVISAO_SECUNDARIA")):
            v = linha.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
                continue
            v = str(v).strip()
            if campo == "secundaria" and V.norm(v) in ("nenhuma", "null", "none", "-", "0"):
                novo = None
            else:
                novo = CF._cat(frame, v.replace(".0", "") if v.endswith(".0") else v)["codigo"]
            if item.get(campo) != novo:
                item[campo] = novo
                mudou = True
        com = linha.get("COMENTARIO")
        if com is not None and not (isinstance(com, float) and pd.isna(com)) and str(com).strip():
            item["comentario"] = str(com).strip()
        if mudou:
            if item["secundaria"] == item["primaria"]:
                item["secundaria"] = None
            item["origem"] = "humano"
            item["confianca"] = 1.0
            item["revisado_em"] = datetime.now().isoformat(timespec="seconds")
            n_alt += 1
    cod["status"] = "rascunho"
    cod["revisao_importada_em"] = datetime.now().isoformat(timespec="seconds")
    CF._gravar(qid, "codificacao.json", cod)
    cod["_alteracoes"] = n_alt
    return cod


def aprovar(qid: str) -> dict:
    cod = codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: nada para aprovar")
    frame = CF._exigir_frame(qid)
    if frame.get("status") != "aprovado":
        raise RuntimeError(f"{qid}: o frame foi editado depois da codificação; aprove o frame e recodifique/revise")
    faltam = resumo_revisao(qid)["n_faltantes"]
    if faltam:
        raise RuntimeError(f"{qid}: ainda há {faltam} resposta(s) sem classificação. Clique em 'Classificar as restantes' antes de aprovar.")
    cod["status"] = "aprovado"
    cod["aprovado_em"] = datetime.now().isoformat(timespec="seconds")
    CF._gravar(qid, "codificacao.json", cod)
    return cod


def mapa_respondentes(qid: str) -> dict[int, dict]:
    """{respondent_id: {'primaria': cod, 'secundaria': cod}} para a pergunta (requer codificação)."""
    dados = CF.respostas(qid)
    cod = codificacao(qid)
    if not cod:
        return {}
    itens = {i["rid"]: i for i in cod["itens"]}
    saida = {}
    for r in dados["respostas"]:
        i = itens.get(r["rid"])
        if not i:
            continue
        for rid_resp in r["respondent_ids"]:
            saida[int(rid_resp)] = {"primaria": i["primaria"], "secundaria": i["secundaria"]}
    return saida


def recarregar_base(incluir_telefone: bool = True) -> dict:
    """Relê a planilha-fonte (versão nova da base) SEM perder o trabalho feito: cada pergunta já
    preparada é relida com rids estáveis (a mesma resposta continua com a mesma classificação e
    conferência), respostas novas ficam para classificar e as aprovadas que ganharam respostas
    novas voltam para revisão. Registra a versão da base em base/versoes.json."""
    df, _ = load.executar(incluir_telefone=incluir_telefone, verbose=False)
    perguntas = {}
    for qid in V.perguntas_codificaveis():
        if CF._existe(qid, "respostas.json"):
            perguntas[qid] = CF.preparar(qid)["_mudancas"]
    aplicar_na_base(verbose=False)
    arq = config.BASE_OUT / "versoes.json"
    versoes = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
    versoes.append({"quando": datetime.now().isoformat(timespec="seconds"), "arquivo": config.FONTE_XLSX.name,
                    "n_respondentes": int(len(df)), "perguntas": perguntas})
    arq.write_text(json.dumps(versoes, ensure_ascii=False, indent=1), encoding="utf-8")
    anterior = versoes[-2]["n_respondentes"] if len(versoes) > 1 else None
    return {"n": int(len(df)), "n_anterior": anterior, "perguntas": perguntas}


def aplicar_na_base(somente_aprovadas: bool = True, verbose: bool = True) -> list[str]:
    """Grava as codificações na base (base.json/base.xlsx) e refaz os banners com back-coding."""
    df, registro = load.carregar_base()
    aplicadas = []
    backcodes: dict = {}
    for qid in V.perguntas_codificaveis():
        cod = codificacao(qid)
        if not cod or (somente_aprovadas and cod.get("status") != "aprovado"):
            continue
        frame = CF._exigir_frame(qid)
        nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
        mapa = mapa_respondentes(qid)
        if qid in V.BACKCODING:
            backcodes[qid] = {rid: v["primaria"] for rid, v in mapa.items()}
        c1, c2 = f"{qid}_COD1", f"{qid}_COD2"
        df[c1] = df["respondent_id"].map(lambda r: mapa.get(int(r), {}).get("primaria") if pd.notna(r) else None)
        df[c2] = df["respondent_id"].map(lambda r: mapa.get(int(r), {}).get("secundaria") if pd.notna(r) else None)
        df[f"{c1}_NOME"] = df[c1].map(nomes)
        df[f"{c2}_NOME"] = df[c2].map(nomes)
        rot = V.por_id(qid)["rotulo"]
        for col, suf in ((c1, "categoria primária"), (c2, "categoria secundária")):
            registro[col] = {"id": col, "pergunta": qid, "rotulo": f"{rot} - {suf} (código)", "enunciado": frame.get("enunciado"),
                             "tipo": "codificada", "opcao": None, "base": registro.get(qid, {}).get("base", "todos"),
                             "origem": {"codificacao": qid}, "frame": [{"codigo": c["codigo"], "nome": c["nome"]} for c in frame["categorias"]]}
            registro[f"{col}_NOME"] = {"id": f"{col}_NOME", "pergunta": qid, "rotulo": f"{rot} - {suf}", "enunciado": frame.get("enunciado"),
                                       "tipo": "codificada_nome", "opcao": None, "base": registro.get(qid, {}).get("base", "todos"),
                                       "origem": {"codificacao": qid}}
        aplicadas.append(qid)
    df = load.derivar_banners(df, backcodes)
    load.salvar_base(df, registro)
    if verbose:
        print(f"  codificações aplicadas na base: {aplicadas or 'nenhuma'}")
        for q in backcodes:
            b = V.BACKCODING[q]["banner"]
            print(f"  {b}: {df[b].value_counts(dropna=False).to_dict()}")
    return aplicadas
