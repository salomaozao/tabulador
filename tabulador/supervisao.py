"""Supervisão da classificação: um SEGUNDO codificador (outra IA) audita o que a IA classificou, e
as respostas com confiança alta E auditoria concordando podem ser confirmadas automaticamente.

Usado pela interface (botões "Auditar com outra IA", "Aceitar alta confiança") e pelo supervisor.py
(linha de comando). Campos gravados em cada item de codificacao.json:
  auditoria   = {"por": "<provedor>:<modelo>", "ok": bool, "em", ["primaria", "secundaria", "nota"]}
  validado_por = "auto" (aceite automático) | "humano" (✓ na interface)
"""
from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import codeframe as CF
import coding as CD
import config
import llm
import progresso
import variables as V

AUTO = "auto"
LIMIAR_PADRAO = 0.85  # decisão do Gabriel (24/09): conservador, ajustável na tela


def auditoria_concorda(item: dict) -> bool | None:
    au = item.get("auditoria")
    return None if not au else bool(au.get("ok"))


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- aceite automático
def auto_aceitar(qid: str, limiar: float = LIMIAR_PADRAO, exigir_auditoria: bool = True, categoria: int | None = None) -> dict:
    """Confirma sozinho o que tem confiança >= limiar (e auditoria concordando, se exigido).
    Se categoria for informada, restringe a essa categoria.
    Nunca mexe no que uma pessoa já conferiu/corrigiu. Retorna a contagem por motivo."""
    cod = CD.codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: ainda não há classificação")
    agora, n = _agora(), Counter()
    for i in cod["itens"]:
        if categoria is not None and i.get("primaria") != categoria:
            continue
        if i.get("primaria") is None or i.get("validado") or i.get("origem") == "humano":
            continue
        motivo = None
        if i.get("origem") == "erro":
            motivo = "erro na chamada"
        elif i["primaria"] == CF.CODIGO_OUTROS:
            motivo = "caiu em Outros"
        elif (i.get("confianca") or 0) < limiar and i.get("origem") != "regra":
            motivo = "confiança abaixo do limiar"
        elif exigir_auditoria and auditoria_concorda(i) is not True:
            motivo = "auditor discordou" if auditoria_concorda(i) is False else "ainda sem auditoria"
        if motivo:
            n[motivo] += 1
            continue
        i["validado"], i["validado_em"], i["validado_por"] = True, agora, AUTO
        n["aceitas"] += 1
    if n["aceitas"]:
        cod["status"] = "rascunho"
        CF._gravar(qid, "codificacao.json", cod)
    return {"aceitas": n.pop("aceitas", 0), "ficaram": dict(n), "limiar": limiar, "exigir_auditoria": exigir_auditoria, "categoria": categoria}


def desfazer_auto(qid: str) -> int:
    """Desfaz todas as confirmações automáticas da pergunta (a auditoria continua guardada)."""
    cod = CD.codificacao(qid)
    if not cod:
        return 0
    k = 0
    for i in cod["itens"]:
        if i.get("validado_por") == AUTO:
            for c in ("validado", "validado_em", "validado_por"):
                i.pop(c, None)
            k += 1
    if k:
        cod["status"] = "rascunho"
        CF._gravar(qid, "codificacao.json", cod)
    return k


# ----------------------------------------------------------------------------- auditoria por outra IA
SCHEMA_AUDITORIA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "auditoria": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "rid": {"type": "integer"},
                    "ok": {"type": "boolean", "description": "true se a classificação proposta está correta"},
                    "primaria": {"type": ["integer", "null"], "description": "se ok=false: o código correto; se ok=true: null"},
                    "secundaria": {"type": ["integer", "null"]},
                    "nota": {"type": "string", "description": "se ok=false: por que (até 15 palavras); se ok=true: vazio"},
                },
                "required": ["rid", "ok", "primaria", "secundaria", "nota"],
            },
        }
    },
    "required": ["auditoria"],
}


def _prompt_auditoria(qid: str, frame: dict, enunciado: str, lote: list[dict]) -> tuple[str, str]:
    system = ("Você é o SEGUNDO codificador (auditor) de uma pesquisa de mercado. Confere, resposta por resposta, "
              "a classificação feita por outro codificador contra um code frame fechado. Seja criterioso mas não "
              "implique com escolhas razoáveis: só discorde quando a categoria estiver errada. Português do Brasil.")
    nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
    cats = "\n".join(f"  {c['codigo']}: {c['nome']} - {c['definicao']}" for c in frame["categorias"])
    linhas = "\n".join(
        f"  rid {r['rid']}: \"{r['texto']}\" -> primária {r['primaria']} ({nomes.get(r['primaria'], '?')})"
        + (f", secundária {r['secundaria']} ({nomes.get(r['secundaria'], '?')})" if r.get("secundaria") else "")
        for r in lote)
    instr = CF.instrucoes_completas(qid)
    user = f"""PERGUNTA ({qid}): {enunciado}

CODE FRAME (códigos válidos):
{cats}
{('Instruções desta pergunta: ' + instr) if instr else ''}

Para CADA rid abaixo, diga se a classificação está correta (ok=true) ou, se não, qual deveria ser
(primaria/secundaria com códigos do frame) e uma nota curta. Um item por rid, na mesma ordem.

CLASSIFICAÇÕES A CONFERIR
{linhas}
"""
    return system, user


def auditar(qid: str, provedor: str | None = None, modelo: str | None = None, escopo: str = "pendentes") -> dict:
    """Pede a outra IA (provedor/modelo escolhidos na tela) que confira a classificação.
    escopo: 'pendentes' = ainda não conferidas e não auditadas; 'todas' = todas as não conferidas."""
    frame = CF._exigir_frame(qid)
    cod = CD.codificacao(qid)
    if not cod:
        raise RuntimeError(f"{qid}: ainda não há classificação para auditar")
    textos = {r["rid"]: r["texto"] for r in CF.respostas(qid)["respostas"]}
    alvo = [i for i in cod["itens"]
            if i.get("primaria") is not None and not i.get("validado") and i.get("origem") not in ("humano", "regra", "erro")
            and (escopo == "todas" or not i.get("auditoria"))]
    if not alvo:
        return {"auditadas": 0, "concorda": 0, "discorda": 0, "por": None}
    lote_n = config.LLM_LOTE
    lotes = [[{**i, "texto": textos.get(i["rid"], "")} for i in alvo[k:k + lote_n]] for k in range(0, len(alvo), lote_n)]
    enunciado = V.por_id(qid).get("rotulo")
    validos = {c["codigo"] for c in frame["categorias"]}
    with llm.usando(provedor, modelo):
        por = f"{config.OPENAI_PROVEDOR}:{config.OPENAI_MODEL}"
        progresso.atualizar(feitos=0, total=len(alvo), lotes_feitos=0, lotes_total=len(lotes), erros=0)
        progresso.etapa("ia", f"{len(alvo)} respostas em {len(lotes)} lote(s) · auditor {por}",
                        estimativa=None)
        t0, resultados, falhas = time.time(), {}, []

        def _um(k):
            system, user = _prompt_auditoria(qid, frame, enunciado, lotes[k])
            return llm.chamar_json(system, user, SCHEMA_AUDITORIA, nome=f"audit_{qid}_{k + 1}")

        with ThreadPoolExecutor(max_workers=config.paralelo()) as ex:
            futuros = {ex.submit(_um, k): k for k in range(len(lotes))}
            feitos = 0
            for fut in as_completed(futuros):
                k = futuros[fut]
                try:
                    resultados[k] = fut.result()
                except Exception as e:  # noqa: BLE001 - lote com erro fica sem auditoria
                    falhas.append(e)
                feitos += len(lotes[k])
                progresso.atualizar(feitos=feitos, lotes_feitos=len(resultados) + len(falhas), erros=len(falhas))
                progresso.evento(f"Lote {k + 1} de {len(lotes)} {'com ERRO' if k not in resultados else 'auditado'} · {time.time() - t0:.0f} s")
    if falhas and not resultados:
        raise falhas[0]
    progresso.etapa("gravar", "gravando a auditoria")
    cod = CD.codificacao(qid)  # relê: a pessoa pode ter conferido algo enquanto a IA auditava
    por_rid = {i["rid"]: i for i in cod["itens"]}
    agora, n = _agora(), Counter()
    for saida in resultados.values():
        for a in saida.get("auditoria", []):
            i = por_rid.get(a.get("rid"))
            if i is None or i.get("validado") or i.get("origem") == "humano":
                continue
            if a.get("ok") or a.get("primaria") == i.get("primaria"):
                i["auditoria"] = {"por": por, "ok": True, "em": agora}
                n["concorda"] += 1
            elif a.get("primaria") in validos:
                sec = a.get("secundaria") if a.get("secundaria") in validos and a.get("secundaria") != a["primaria"] else None
                i["auditoria"] = {"por": por, "ok": False, "em": agora, "primaria": a["primaria"], "secundaria": sec,
                                  "nota": (a.get("nota") or "")[:200]}
                n["discorda"] += 1
    CF._gravar(qid, "codificacao.json", cod)
    return {"auditadas": n["concorda"] + n["discorda"], "concorda": n["concorda"], "discorda": n["discorda"],
            "lotes_com_erro": len(falhas), "por": por}


# ----------------------------------------------------------------------------- quem conferiu
def conferencia(item_lista: list[dict]) -> dict:
    """Separa as conferências: pessoas (✓ ou correção), automáticas e sugestões do auditor adotadas."""
    n = Counter()
    for i in item_lista:
        au = i.get("auditoria") or {}
        if "ia_original" in i or (i.get("origem") == "humano" and au.get("ok") is False and au.get("primaria") == i.get("primaria")):
            n["sugestoes_adotadas"] += 1
        if i.get("origem") == "humano":
            n["corrigidas_humano"] += 1
        elif i.get("validado"):
            n["confirmadas_auto" if i.get("validado_por") == AUTO else "confirmadas_humano"] += 1
        if au:
            n["auditadas"] += 1
            n["auditor_discordou" if au.get("ok") is False else "auditor_concordou"] += 1
    return dict(n)
