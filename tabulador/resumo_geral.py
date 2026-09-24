"""Visão geral do projeto (aba Resultados): junta temas e trechos de todas as perguntas abertas
já aprovadas, sem separar por pergunta, e mantém em cache um resumo narrativo gerado pela IA (só
recalculado quando o pesquisador pede, para não gastar chamadas a cada carregamento da página).

Saída: output/resumo_geral.json
"""
from __future__ import annotations

import json
from datetime import datetime

import codeframe as CF
import coding as CD
import config
import llm
import variables as V

_ARQUIVO = "resumo_geral.json"
N_TEMAS = 8
N_TRECHOS = 6
_CODIGOS_FORA = {97, 98}  # Outros, NS/NR: não entram no panorama geral


def _perguntas_aprovadas() -> list[str]:
    return [qid for qid in V.perguntas_codificaveis() if (CD.codificacao(qid) or {}).get("status") == "aprovado"]


def _temas_e_trechos() -> dict:
    temas: list[dict] = []
    trechos: list[dict] = []
    for qid in _perguntas_aprovadas():
        frame = CF.frame(qid)
        t = CD.tabela(qid)
        if not frame or t is None:
            continue
        rotulo = V.por_id(qid).get("rotulo", qid)
        registros = t.to_dict(orient="records")
        cont: dict[int, int] = {}
        for r in registros:
            for chave in ("primaria", "secundaria"):
                cod = r.get(chave)
                if cod is not None:
                    cont[int(cod)] = cont.get(int(cod), 0) + int(r.get("n") or 0)
        for cat in frame["categorias"]:
            if cat["codigo"] in _CODIGOS_FORA:
                continue
            m = cont.get(cat["codigo"], 0)
            if m:
                temas.append({"qid": qid, "pergunta": rotulo, "nome": cat["nome"], "mencoes": m})
        candidatas = [r for r in registros if r.get("primaria") not in (None, *_CODIGOS_FORA) and r.get("texto")]
        if candidatas:
            r = max(candidatas, key=lambda r: r.get("n") or 0)
            trechos.append({"qid": qid, "pergunta": rotulo, "texto": r["texto"]})
    temas.sort(key=lambda t: -t["mencoes"])
    return {"temas": temas[:N_TEMAS], "trechos": trechos[:N_TRECHOS]}


def _cache_path():
    return config.OUTPUT_DIR / _ARQUIVO


def resumo() -> dict:
    """Temas/trechos sempre recalculados na hora (é barato) + narrativa em cache, se já foi gerada."""
    dados = _temas_e_trechos()
    p = _cache_path()
    if p.exists():
        cache = json.loads(p.read_text(encoding="utf-8"))
        dados["narrativa"] = cache.get("narrativa")
        dados["narrativa_gerada_em"] = cache.get("gerada_em")
    return dados


_SCHEMA = {
    "type": "object",
    "properties": {"resumo": {"type": "string"}},
    "required": ["resumo"],
    "additionalProperties": False,
}
_SYSTEM = (
    "Você resume pesquisas de satisfação em português do Brasil, de forma direta e sem clichês. "
    "Escreva um único parágrafo corrido (3 a 5 frases), sem listas nem tópicos, juntando os temas "
    "de TODAS as perguntas do projeto — não organize frase a frase por pergunta, é para ler como "
    "um panorama único do que as pessoas disseram."
)


def gerar_narrativa() -> dict:
    dados = _temas_e_trechos()
    if not dados["temas"]:
        raise RuntimeError("Aprove ao menos uma pergunta classificada antes de gerar o resumo geral.")
    temas_txt = "\n".join(f"- {t['nome']} (pergunta: {t['pergunta']}, {t['mencoes']} menções)" for t in dados["temas"])
    trechos_txt = "\n".join(f'- "{t["texto"]}"' for t in dados["trechos"])
    user = f"Temas mais citados (todas as perguntas abertas do projeto):\n{temas_txt}\n\nTrechos de exemplo:\n{trechos_txt}"
    resposta = llm.chamar_json(_SYSTEM, user, _SCHEMA, nome="resumo_geral")
    config.garantir_pastas()
    cache = {"narrativa": resposta["resumo"], "gerada_em": datetime.now().strftime("%d/%m/%Y %H:%M")}
    _cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {**dados, **cache}
