"""Back-coding dos campos 'Outro. Qual?' (Cargo e Segmento) para fechar os banners.

É o fluxo de codificação com frame FIXO (variables.BACKCODING):
  1. `rodar()`   : frame fixo + codificação LLM das respostas 'Outro' + exporta revisao.xlsx
  2. revisão humana no xlsx (opcional) + `python run.py code <QID> importar`
  3. `aplicar()` : aprova a codificação, grava na base e reconstrói CARGO4 / SEGMENTO4
"""
from __future__ import annotations

import codeframe as CF
import coding as CD
import load
import variables as V


def rodar(qids: list[str] | None = None, forcar: bool = False) -> None:
    for qid in qids or list(V.BACKCODING):
        CF.frame_fixo(qid)
        cod = CD.codificacao(qid)
        if cod and cod.get("status") == "aprovado" and not forcar:
            print(f"  {qid}: codificação já aprovada (use --forcar para refazer)")
            continue
        CD.codificar(qid, forcar=forcar)
        p = CD.exportar_revisao(qid)
        t = CD.tabela(qid)
        print(f"  {qid}: {len(t)} respostas únicas codificadas | alertas: {(t['alertas'] != '').sum()} | revisão: {p}")


def aplicar(qids: list[str] | None = None) -> None:
    for qid in qids or list(V.BACKCODING):
        if CD.codificacao(qid) is None:
            raise RuntimeError(f"{qid}: rode primeiro `python run.py backcode`")
        CD.aprovar(qid)
    CD.aplicar_na_base()


def conferir() -> dict:
    """Retorna, por banner, quantos respondentes ainda estão em 'Outro' (deve ser 0 após o back-coding
    se todas as respostas couberam em algum grupo)."""
    df, _ = load.carregar_base()
    saida = {}
    for qid, bc in V.BACKCODING.items():
        banner = bc["banner"]
        saida[banner] = {
            "distribuicao": df[banner].value_counts(dropna=False).to_dict(),
            "outro_restante": int((df[banner] == "Outro").sum()),
            "sem_valor": int(df[banner].isna().sum()),
        }
    return saida
