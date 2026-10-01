"""Progressão do projeto ao longo do tempo — o cabeçalho do painel geral.

Responde duas perguntas: "quanto já andou" e "como chegou aqui". São duas séries, as duas em
**% de PERGUNTAS** (o denominador é o total de perguntas do projeto, fixo) para a linha subir
quando o trabalho avança e **não descer** quando entra entrevista nova na base:

  classificadas : pergunta em que a IA já passou por TODAS as respostas (n_faltantes = 0)
  revisadas     : pergunta em que TODA a classificação já foi conferida por gente

As duas curvas são reconstruídas do que já está gravado item a item, então valem para o histórico
inteiro (não é preciso começar a medir de hoje):

  revisadas     -> carimbo `validado_em` / `revisado_em` de cada item, em `codificacao.json`
  classificadas -> carimbo das chamadas `code_<qid>` em `output/llm_log/` (mesma fonte da aba Consumo)

Aproximação assumida: o ponto de uma pergunta é o dia do ÚLTIMO item que chegou àquele estado, e a
curva inteira é recalculada com o estado de agora. Se a base crescer depois (Recarregar planilha) e
a pergunta voltar a ter respostas novas, ela recua na curva — é o caminho do trabalho, não um
snapshot contábil de cada dia.
"""
from __future__ import annotations

import re
from datetime import date

import coding as CD
import config
import variables as V

# 20260928_150731_1_code_Q35_2.json -> ('2026', '09', '28', 'Q35')
_LOG_CODE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})_\d{6}_\d+_code_(.+?)(?:_\d+)?\.json$")


def _dia(iso: str | None) -> str | None:
    """'2026-09-24T18:15:02' -> '2026-09-24'. None quando não há carimbo (item antigo/importado)."""
    d = (iso or "")[:10]
    return d if len(d) == 10 and d[4] == "-" and d[7] == "-" else None


def dias_de_classificacao() -> dict[str, str]:
    """qid -> último dia em que a IA classificou aquela pergunta.

    Sai do nome dos arquivos do llm_log (o mesmo padrão que a aba Consumo lê), sem abrir arquivo
    nenhum: é uma varredura de diretório.
    """
    dias: dict[str, str] = {}
    pasta = config.LLM_LOG_OUT
    if not pasta.exists():
        return dias
    for p in pasta.glob("*.json"):
        m = _LOG_CODE_RE.match(p.name)
        if not m:
            continue
        dia, qid = f"{m.group(1)}-{m.group(2)}-{m.group(3)}", m.group(4)
        if dia > dias.get(qid, ""):
            dias[qid] = dia
    return dias


def _dia_da_revisao(cod: dict | None) -> str | None:
    """Dia em que a última resposta conferida foi conferida (o mais recente dos carimbos)."""
    dias = []
    for i in (cod or {}).get("itens", []):
        if CD.situacao_revisao(i) in ("confirmada", "corrigida"):
            dias.append(_dia(i.get("validado_em") or i.get("revisado_em")))
    return max((d for d in dias if d), default=None)


def estado_perguntas(perguntas: list[dict] | None = None) -> list[dict]:
    """Uma linha por pergunta codificável: classificada? revisada? e em que dia chegou lá.

    `perguntas` aceita a lista que `report.status_pergunta` já devolveu (é o que o `/api/status`
    faz, para não recalcular duas vezes os mesmos números).
    """
    if perguntas is None:
        import report
        perguntas = [report.status_pergunta(q) for q in V.perguntas_codificaveis()]
    dias_cls = dias_de_classificacao()
    linhas = []
    for s in perguntas:
        qid = s["qid"]
        n_cod = s.get("n_codificadas") or 0
        n_rev = s.get("n_revisadas") or 0
        classificada = n_cod > 0 and not (s.get("n_faltantes") or 0)
        revisada = classificada and n_rev >= n_cod
        linhas.append({
            "qid": qid,
            "rotulo": s.get("rotulo"),
            "n_unicas": s.get("n_unicas") or 0,
            "n_codificadas": n_cod,
            "n_revisadas": n_rev,
            "pct_revisadas": (n_rev / n_cod) if n_cod else 0.0,
            "classificada": classificada,
            "revisada": revisada,
            # só lê o codificacao.json (carimbos de conferência) de quem já está revisada
            "dia_classificada": dias_cls.get(qid) if classificada else None,
            "dia_revisada": _dia_da_revisao(CD.codificacao(qid)) if revisada else None,
        })
    return linhas


def serie(estados: list[dict], total: int | None = None, hoje: str | None = None) -> list[dict]:
    """Pontos cumulativos, um por dia com movimento (mais o dia de hoje, para a linha terminar no
    presente). Pergunta sem carimbo (revisão importada de Excel antigo, por exemplo) conta a partir
    de hoje, em vez de sumir da conta."""
    total = len(estados) if total is None else total
    hoje = hoje or date.today().isoformat()

    def dia_de(e: dict, campo: str) -> str:
        return e[campo] or hoje  # sem carimbo: conta a partir de hoje

    dias = sorted({dia_de(e, "dia_revisada") for e in estados if e["revisada"]}
                  | {dia_de(e, "dia_classificada") for e in estados if e["classificada"]})
    if not dias:
        return []
    if dias[-1] != hoje:
        dias.append(hoje)
    pontos = []
    for d in dias:
        nc = sum(1 for e in estados if e["classificada"] and dia_de(e, "dia_classificada") <= d)
        nr = sum(1 for e in estados if e["revisada"] and dia_de(e, "dia_revisada") <= d)
        pontos.append({
            "dia": d,
            "n_classificadas": nc, "n_revisadas": nr,
            "pct_classificadas": (nc / total) if total else 0.0,
            "pct_revisadas": (nr / total) if total else 0.0,
        })
    return pontos


def resumo(perguntas: list[dict] | None = None) -> dict:
    """Tudo que o cabeçalho do painel precisa: números de agora + a série para o gráfico."""
    estados = estado_perguntas(perguntas)
    total = len(estados)
    n_rev = sum(1 for e in estados if e["revisada"])
    n_cls = sum(1 for e in estados if e["classificada"])
    return {
        "total": total,
        "n_revisadas": n_rev,
        "n_classificadas": n_cls,
        "n_andamento": n_cls - n_rev,          # classificadas com revisão ainda em curso
        "n_a_iniciar": total - n_cls,
        "pct_revisadas": (n_rev / total) if total else 0.0,
        "pct_classificadas": (n_cls / total) if total else 0.0,
        "respostas": {
            "unicas": sum(e["n_unicas"] for e in estados),
            "classificadas": sum(e["n_codificadas"] for e in estados),
            "revisadas": sum(e["n_revisadas"] for e in estados),
        },
        "serie": serie(estados, total),
        "perguntas": estados,
    }
