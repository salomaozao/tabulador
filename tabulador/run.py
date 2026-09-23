"""CLI unificado do pipeline (projeto ativo; troque com --projeto sesi|assertiva antes do comando).

  python run.py --projeto sesi status
  python run.py load [--sem-telefone]                    lê a planilha-fonte -> output/base/
  python run.py exportar                                 planilha final no formato da fonte (SAIDA_PLANILHA)
  python run.py backcode [--forcar]                      back-coding de Cargo/Segmento 'Outro' (+ revisao.xlsx)
  python run.py backcode aplicar                         aprova o back-coding e fecha CARGO4/SEGMENTO4 na base
  python run.py frame <QID|all> induzir [--forcar]       LLM propõe o code frame
  python run.py frame <QID> mostrar                      imprime o frame
  python run.py frame <QID> renomear <cod> "Novo nome" ["nova definição"]
  python run.py frame <QID> fundir <destino> <origem> [<origem>...]
  python run.py frame <QID> adicionar "Nome" ["definição"]
  python run.py frame <QID> remover <cod>
  python run.py frame <QID|all> aprovar
  python run.py code <QID|all> [--forcar]                codifica contra o frame aprovado (+ revisao.xlsx + relatório)
  python run.py code <QID> exportar                      gera revisao.xlsx
  python run.py code <QID> importar                      aplica as correções do revisao.xlsx
  python run.py code <QID|all> aprovar                   trava a codificação e grava na base
  python run.py report <QID|all>                         relatório HTML de conferência (+ index.html)
  python run.py codebook                                 codebook.xlsx / .html
  python run.py crosstabs [--banners A B C]              cruzamentos.xlsx
  python run.py status                                   situação de cada pergunta aberta
  python run.py all [--auto]                             load -> backcode -> frames -> (aprovação) -> code -> report -> codebook -> crosstabs
                                                         --auto aprova frames e codificações automaticamente (rascunho rápido)
"""
from __future__ import annotations

import argparse
import sys

import variables as V


def _qids(arg: str) -> list[str]:
    if arg == "all":
        return V.perguntas_codificaveis()
    if arg == "abertas":
        return [q for q in V.perguntas_codificaveis() if q not in V.BACKCODING]
    V.por_id(arg)
    return [arg]


def cmd_load(a):
    import load
    load.executar(incluir_telefone=not a.sem_telefone)


def cmd_backcode(a):
    import backcoding
    if a.acao == "aplicar":
        backcoding.aplicar()
        for banner, d in backcoding.conferir().items():
            print(f"  {banner}: {d['distribuicao']} | ainda em 'Outro': {d['outro_restante']} | sem valor: {d['sem_valor']}")
    else:
        backcoding.rodar(forcar=a.forcar)
        import report
        for qid in V.BACKCODING:
            report.gerar(qid)
        report.gerar_indice()
        print("  revise output/perguntas/<QID>/revisao.xlsx (opcional) e rode: python run.py backcode aplicar")


def cmd_frame(a):
    import codeframe as CF
    qids = _qids(a.qid)
    for qid in qids:
        if a.acao == "induzir":
            f = CF.induzir(qid, forcar=a.forcar)
            print(CF.texto_frame(qid))
            print(f"  -> {CF.pasta(qid) / 'frame.json'} (status: {f['status']})")
        elif a.acao == "mostrar":
            print(CF.texto_frame(qid))
        elif a.acao == "renomear":
            CF.renomear(qid, a.args[0], a.args[1], a.args[2] if len(a.args) > 2 else None)
            print(CF.texto_frame(qid))
        elif a.acao == "fundir":
            CF.fundir(qid, a.args[0], *a.args[1:])
            print(CF.texto_frame(qid))
        elif a.acao == "adicionar":
            CF.adicionar(qid, a.args[0], a.args[1] if len(a.args) > 1 else "")
            print(CF.texto_frame(qid))
        elif a.acao == "remover":
            CF.remover(qid, a.args[0])
            print(CF.texto_frame(qid))
        elif a.acao == "aprovar":
            CF.aprovar(qid)
            print(f"  {qid}: frame aprovado")
        else:
            sys.exit(f"ação desconhecida: {a.acao}")


def cmd_code(a):
    import coding as CD
    import report
    qids = _qids(a.qid)
    for qid in qids:
        if a.acao == "codificar":
            CD.codificar(qid, forcar=a.forcar)
            p = CD.exportar_revisao(qid)
            t = CD.tabela(qid)
            r = report.gerar(qid)
            print(f"  {qid}: {len(t)} respostas únicas | alertas: {(t['alertas'] != '').sum()} | {p.name} | {r}")
        elif a.acao == "exportar":
            print("  ->", CD.exportar_revisao(qid))
        elif a.acao == "importar":
            cod = CD.importar_revisao(qid)
            report.gerar(qid)
            print(f"  {qid}: {cod['_alteracoes']} correções humanas aplicadas (status: rascunho; aprove com `code {qid} aprovar`)")
        elif a.acao == "aprovar":
            CD.aprovar(qid)
            print(f"  {qid}: codificação aprovada")
        else:
            sys.exit(f"ação desconhecida: {a.acao}")
    if a.acao == "aprovar":
        CD.aplicar_na_base()
    report.gerar_indice()


def cmd_report(a):
    import report
    for qid in _qids(a.qid):
        print("  ->", report.gerar(qid))
    print("  ->", report.gerar_indice())


def cmd_codebook(a):
    import codebook
    codebook.gerar()


def cmd_crosstabs(a):
    import crosstabs
    crosstabs.gerar(banners=a.banners)


def cmd_exportar(a):
    import exportar
    exportar.gerar()


def cmd_status(a):
    import report
    print(f"{'pergunta':<24}{'resp.':>6}{'únicas':>8}  {'frame':<10}{'cat.':>5}  {'codificação':<12}{'alertas':>8}")
    for qid in V.perguntas_codificaveis():
        s = report.status_pergunta(qid)
        print(f"{qid:<24}{s['respondeu'] or '-':>6}{s['respostas'] or '-':>8}  {s['frame'] or '-':<10}{s['n_categorias'] or '-':>5}  {s['codificacao'] or '-':<12}{'' if s['alertas'] is None else s['alertas']:>8}")


def cmd_all(a):
    import backcoding
    import codeframe as CF
    import codebook
    import coding as CD
    import crosstabs
    import load
    import report

    print("[1/7] load")
    load.executar(incluir_telefone=not a.sem_telefone)
    print("[2/7] back-coding")
    backcoding.rodar()
    backcoding.aplicar()
    print("[3/7] code frames")
    pendentes = []
    for qid in _qids("abertas"):
        f = CF.frame(qid)
        if f and f["status"] == "aprovado":
            print(f"  {qid}: frame já aprovado")
            continue
        if not f:
            CF.induzir(qid)
        if a.auto:
            CF.aprovar(qid)
        else:
            pendentes.append(qid)
    if pendentes:
        for qid in pendentes:
            print(CF.texto_frame(qid))
        report.gerar_indice()
        print("\nFrames aguardando aprovação humana:", ", ".join(pendentes))
        print("Edite (frame <QID> renomear|fundir|adicionar|remover) e aprove (frame <QID> aprovar); depois rode `python run.py all` de novo.")
        return
    print("[4/7] codificação")
    for qid in _qids("abertas"):
        cod = CD.codificacao(qid)
        if cod and cod["status"] == "aprovado":
            continue
        if not cod:
            CD.codificar(qid)
            CD.exportar_revisao(qid)
        if a.auto:
            CD.aprovar(qid)
    CD.aplicar_na_base()
    print("[5/7] relatórios")
    for qid in V.perguntas_codificaveis():
        report.gerar(qid)
    report.gerar_indice()
    nao_aprov = [q for q in _qids("abertas") if (CD.codificacao(q) or {}).get("status") != "aprovado"]
    if nao_aprov:
        print("Codificações aguardando revisão/aprovação:", ", ".join(nao_aprov))
        print("Revise revisao.xlsx / relatorio.html, importe (code <QID> importar) e aprove (code <QID> aprovar); depois rode `python run.py all` de novo.")
    print("[6/7] codebook")
    codebook.gerar()
    print("[7/7] cruzamentos")
    crosstabs.gerar()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--projeto", "-p", default=None, help="projeto (ver projetos.json); padrão: o último usado")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("exportar"); s.set_defaults(f=cmd_exportar)

    s = sub.add_parser("load"); s.add_argument("--sem-telefone", action="store_true"); s.set_defaults(f=cmd_load)
    s = sub.add_parser("backcode"); s.add_argument("acao", nargs="?", default="rodar", choices=["rodar", "aplicar"]); s.add_argument("--forcar", action="store_true"); s.set_defaults(f=cmd_backcode)
    s = sub.add_parser("frame"); s.add_argument("qid"); s.add_argument("acao", nargs="?", default="mostrar"); s.add_argument("args", nargs="*"); s.add_argument("--forcar", action="store_true"); s.set_defaults(f=cmd_frame)
    s = sub.add_parser("code"); s.add_argument("qid"); s.add_argument("acao", nargs="?", default="codificar"); s.add_argument("--forcar", action="store_true"); s.set_defaults(f=cmd_code)
    s = sub.add_parser("report"); s.add_argument("qid", nargs="?", default="all"); s.set_defaults(f=cmd_report)
    s = sub.add_parser("codebook"); s.set_defaults(f=cmd_codebook)
    s = sub.add_parser("crosstabs"); s.add_argument("--banners", nargs="+", default=None); s.set_defaults(f=cmd_crosstabs)
    s = sub.add_parser("status"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("all"); s.add_argument("--auto", action="store_true"); s.add_argument("--sem-telefone", action="store_true"); s.set_defaults(f=cmd_all)

    a = p.parse_args(argv)
    if a.projeto:
        import projetos
        projetos.ativar(a.projeto)
    a.f(a)


if __name__ == "__main__":
    main()
