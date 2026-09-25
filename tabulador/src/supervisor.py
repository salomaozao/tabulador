"""Supervisor da categorização (CLI): roda a IA, audita e aceita automaticamente o que tem alta confiança.

Fluxo pensado para "matar o máximo com alta confiança e deixar o resto para o pesquisador":

  (opções globais: --provedor cli_claude --modelo sonnet --lote 40 --paralelo 3 valem só para a execução)

  python supervisor.py -p sesi status                      painel de todas as perguntas abertas
  python supervisor.py -p sesi rodar Q5 Q29 ...            classifica só o que falta (repete lotes com erro)
  python supervisor.py -p sesi preparar Q35               lê as respostas e induz o frame (NÃO aprova)
  python supervisor.py -p sesi reclassificar Q5 --categorias 97 [--abaixo 0.5]
        depois de mudar o quadro: refaz só as não conferidas nessas categorias / abaixo da confiança
  python supervisor.py -p sesi auditar Q5 [--todas]        gera auditoria/<QID>_para_auditar.tsv (texto + categoria da IA)
  python supervisor.py -p sesi aplicar-auditoria Q5 arq.json
        arq.json = {"<rid>": {"ok": true} | {"primaria": 3, "secundaria": null, "nota": "..."}}
        --resto-ok: o que estava no .tsv e não aparece no json conta como "concorda"
        grava item["auditoria"] (segunda opinião); não muda a classificação
  python supervisor.py -p sesi adotar-sugestoes Q5          onde o auditor discorda, mostra a sugestão dele (segue pendente)
  python supervisor.py -p sesi auto-aceitar Q5 [--limiar 0.85] [--sem-auditoria]
        confirma (validado=True, validado_por="auto") as respostas com confiança >= limiar,
        que não são Outros/erro e cuja auditoria concorda. O resto fica pendente para o pesquisador.
  python supervisor.py -p sesi desfazer-auto Q5            desfaz as confirmações automáticas
  python supervisor.py -p sesi fila Q5 [-n 40]             mostra as pendentes (o que o pesquisador precisa ver)

As confirmações automáticas não entram na taxa "acerto da IA" (só conferências humanas contam).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime

import codeframe as CF
import coding as CD
import config
import supervisao as SUP
import variables as V

AUTO = SUP.AUTO


def _nomes(qid: str) -> dict[int, str]:
    f = CF.frame(qid) or {"categorias": []}
    return {c["codigo"]: c["nome"] for c in f["categorias"]}


def _pasta_auditoria():
    p = config.OUTPUT_DIR / "auditoria"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _auditoria_concorda(item: dict) -> bool | None:
    a = item.get("auditoria")
    if not a:
        return None
    return bool(a.get("ok"))


def cmd_status(a):
    print(f"{'perg':<5}{'únicas':>7}{'classif':>8}{'humano':>7}{'auto':>6}{'pend':>6}{'conf≥.85':>9}{'Outros':>7}{'erro':>5}{'audit':>6}{'discord':>8}  frame/cod")
    for qid in _qids(a.qids or ["abertas"]):
        dados = CF._ler(qid, "respostas.json")
        f = CF.frame(qid)
        cod = CD.codificacao(qid) or {"itens": []}
        it = [i for i in cod["itens"] if i.get("primaria") is not None]
        humano = sum(1 for i in it if i.get("origem") == "humano" or (i.get("validado") and i.get("validado_por") != AUTO))
        auto = sum(1 for i in it if i.get("validado") and i.get("validado_por") == AUTO)
        pend = sum(1 for i in it if not i.get("validado") and i.get("origem") != "humano")
        alta = sum(1 for i in it if i.get("confianca", 0) >= 0.85 and i.get("origem") != "erro")
        outros = sum(1 for i in it if i["primaria"] == CF.CODIGO_OUTROS)
        erro = sum(1 for i in it if i.get("origem") == "erro")
        aud = sum(1 for i in it if i.get("auditoria"))
        disc = sum(1 for i in it if _auditoria_concorda(i) is False)
        n = len(dados["respostas"]) if dados else "-"
        print(f"{qid:<5}{n:>7}{len(it):>8}{humano:>7}{auto:>6}{pend:>6}{alta:>9}{outros:>7}{erro:>5}{aud:>6}{disc:>8}  "
              f"{(f or {}).get('status', '-')}/{cod.get('status', '-')}")


def _qids(lista: list[str]) -> list[str]:
    out = []
    for q in lista:
        if q in ("all", "abertas"):
            out += [x for x in V.perguntas_codificaveis() if x not in V.BACKCODING]
        else:
            V.por_id(q)
            out.append(q)
    return out


def cmd_preparar(a):
    for qid in _qids(a.qids):
        dados = CF.preparar(qid) if a.reler or not CF._ler(qid, "respostas.json") else CF.respostas(qid)
        print(f"{qid}: {dados['n_respondeu']} respostas, {dados['n_unicas']} únicas, {dados['n_nsnr_auto']} NS/NR por regra")
        if not CF.frame(qid) or a.forcar:
            CF.induzir(qid, forcar=a.forcar)
            print(CF.texto_frame(qid))
            print(f"  frame em RASCUNHO — revise e aprove: python run.py frame {qid} aprovar")


def cmd_rodar(a):
    for qid in _qids(a.qids):
        for tentativa in range(1, a.tentativas + 1):
            t0 = datetime.now()
            cod = CD.codificar(qid, somente_faltantes=True)
            it = cod["itens"]
            erros = [i["rid"] for i in it if i.get("origem") == "erro"]
            falta = len(CF.respostas(qid)["respostas"]) - len(it)
            print(f"{qid} tentativa {tentativa}: {len(it)} classificadas, {len(erros)} com erro, {falta} faltando "
                  f"({(datetime.now() - t0).seconds}s)", flush=True)
            if erros:  # erro vira Outros com confiança 0: tira para a próxima tentativa refazer
                cod = CD.codificacao(qid)
                cod["itens"] = [i for i in cod["itens"] if i.get("origem") != "erro"]
                CF._gravar(qid, "codificacao.json", cod)
            if not erros and not falta:
                break


def cmd_reclassificar(a):
    """Depois de mudar o quadro: manda de novo à IA só as respostas não conferidas que estão nas
    categorias indicadas (ex.: 97) e/ou abaixo de uma confiança. O que foi conferido fica intacto."""
    for qid in _qids(a.qids):
        cod = CD.codificacao(qid)
        cats = set(a.categorias or [])
        rids = [i["rid"] for i in cod["itens"]
                if i.get("primaria") is not None and not i.get("validado") and i.get("origem") not in ("humano", "regra")
                and ((cats and i["primaria"] in cats) or (a.abaixo is not None and i.get("confianca", 0) < a.abaixo))]
        if not rids:
            print(f"{qid}: nada para reclassificar")
            continue
        novo = CD.recodificar(qid, rids=rids, apenas_comentados=False)
        print(f"{qid}: {novo.get('_recodificados', 0)} de {len(rids)} respostas reclassificadas", flush=True)


def cmd_auditar(a):
    for qid in _qids(a.qids):
        nomes = _nomes(qid)
        dados = {r["rid"]: r for r in CF.respostas(qid)["respostas"]}
        cod = CD.codificacao(qid)
        caminho = _pasta_auditoria() / f"{qid}_para_auditar.tsv"
        n = 0
        with open(caminho, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(["rid", "n", "conf", "primaria", "secundaria", "texto"])
            for i in cod["itens"]:
                if i.get("primaria") is None or (i.get("auditoria") and not a.todas):
                    continue
                if i.get("origem") == "humano" or (i.get("validado") and i.get("validado_por") != AUTO):
                    continue
                r = dados[i["rid"]]
                w.writerow([i["rid"], r["n"], f"{i.get('confianca', 0):.2f}",
                            f"{i['primaria']} {nomes.get(i['primaria'], '?')}",
                            f"{i['secundaria']} {nomes.get(i['secundaria'], '?')}" if i.get("secundaria") else "",
                            " ".join(str(r["texto"]).split())])
                n += 1
        print(f"{qid}: {n} respostas para auditar -> {caminho}")


def cmd_aplicar_auditoria(a):
    qid = _qids([a.qid])[0]
    with open(a.arquivo, encoding="utf-8") as fh:
        vered = {int(k): v for k, v in json.load(fh).items()}
    if a.resto_ok:  # tudo que estava no .tsv auditado e não foi contestado = concorda
        with open(_pasta_auditoria() / f"{qid}_para_auditar.tsv", encoding="utf-8") as fh:
            for linha in list(csv.reader(fh, delimiter="	"))[1:]:
                vered.setdefault(int(linha[0]), {"ok": True})
    validos = set(_nomes(qid))
    cod = CD.codificacao(qid)
    agora = datetime.now().isoformat(timespec="seconds")
    n = Counter()
    for i in cod["itens"]:
        v = vered.get(i["rid"])
        if v is None:
            continue
        if v.get("ok"):
            i["auditoria"] = {"por": a.por, "ok": True, "em": agora}
            n["concorda"] += 1
            continue
        prim = v.get("primaria")
        if prim is not None and prim not in validos:
            print(f"  aviso rid {i['rid']}: código {prim} não existe no frame — ignorado")
            continue
        sug = {"por": a.por, "ok": False, "em": agora, "primaria": prim, "secundaria": v.get("secundaria"), "nota": v.get("nota", "")}
        i["auditoria"] = sug
        n["discorda"] += 1
    CF._gravar(qid, "codificacao.json", cod)
    print(f"{qid}: auditoria aplicada {dict(n)}")


def cmd_adotar_sugestoes(a):
    """Onde o auditor discorda, a sugestão dele vira a classificação exibida (a da IA fica guardada em
    `ia_original` e citada na justificativa). Continua PENDENTE: o pesquisador só confirma ou corrige."""
    for qid in _qids(a.qids):
        nomes = _nomes(qid)
        cod = CD.codificacao(qid)
        k = 0
        for i in cod["itens"]:
            au = i.get("auditoria") or {}
            if au.get("ok") is not False or au.get("primaria") is None or i.get("validado") or i.get("origem") == "humano":
                continue
            if "ia_original" in i:
                continue
            i["ia_original"] = {"primaria": i["primaria"], "secundaria": i.get("secundaria"), "confianca": i.get("confianca"),
                                "justificativa": i.get("justificativa", "")}
            sec = au.get("secundaria")
            i["primaria"], i["secundaria"] = au["primaria"], (sec if sec != au["primaria"] else None)
            i["justificativa"] = f"[revisor {au.get('por', '')}: {au.get('nota', '')}] IA tinha: {nomes.get(i['ia_original']['primaria'], i['ia_original']['primaria'])}"
            k += 1
        CF._gravar(qid, "codificacao.json", cod)
        print(f"{qid}: {k} sugestões do auditor adotadas (continuam pendentes para o pesquisador)")


def cmd_auto_aceitar(a):
    for qid in _qids(a.qids):
        r = SUP.auto_aceitar(qid, a.limiar, exigir_auditoria=not a.sem_auditoria)
        print(f"{qid}: {r['aceitas']} aceitas; ficam para revisão: {r['ficaram']}")


def cmd_desfazer_auto(a):
    for qid in _qids(a.qids):
        print(f"{qid}: {SUP.desfazer_auto(qid)} confirmações automáticas desfeitas")


def cmd_fila(a):
    qid = _qids([a.qid])[0]
    nomes = _nomes(qid)
    dados = {r["rid"]: r for r in CF.respostas(qid)["respostas"]}
    pend = [i for i in CD.codificacao(qid)["itens"] if not i.get("validado") and i.get("origem") != "humano"]
    pend.sort(key=lambda i: (-dados[i["rid"]]["n"], i.get("confianca", 0)))
    print(f"{qid}: {len(pend)} pendentes")
    for i in pend[: a.n]:
        au = i.get("auditoria") or {}
        sug = f"  → auditor sugere {au.get('primaria')} {nomes.get(au.get('primaria'), '')} ({au.get('nota', '')})" if au and not au.get("ok") else ""
        print(f"  rid {i['rid']:>5} n={dados[i['rid']]['n']:<3} {i.get('confianca', 0):.2f} [{i['primaria']} {nomes.get(i['primaria'], '?')}] "
              f"{str(dados[i['rid']]['texto'])[:110]!r}{sug}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--projeto", "-p", default=None)
    p.add_argument("--provedor", default=None, help="só nesta execução (ex.: cli_claude, groq); não grava no .env")
    p.add_argument("--modelo", default=None)
    p.add_argument("--lote", type=int, default=None, help="respostas por chamada (padrão do config)")
    p.add_argument("--paralelo", type=int, default=None, help="chamadas simultâneas")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("qids", nargs="*"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("preparar"); s.add_argument("qids", nargs="+"); s.add_argument("--forcar", action="store_true"); s.add_argument("--reler", action="store_true"); s.set_defaults(f=cmd_preparar)
    s = sub.add_parser("rodar"); s.add_argument("qids", nargs="+"); s.add_argument("--tentativas", type=int, default=3); s.set_defaults(f=cmd_rodar)
    s = sub.add_parser("reclassificar"); s.add_argument("qids", nargs="+"); s.add_argument("--categorias", type=int, nargs="*"); s.add_argument("--abaixo", type=float, default=None); s.set_defaults(f=cmd_reclassificar)
    s = sub.add_parser("auditar"); s.add_argument("qids", nargs="+"); s.add_argument("--todas", action="store_true"); s.set_defaults(f=cmd_auditar)
    s = sub.add_parser("aplicar-auditoria"); s.add_argument("qid"); s.add_argument("arquivo"); s.add_argument("--por", default="claude"); s.add_argument("--resto-ok", action="store_true", help="linhas do .tsv fora do json = concorda"); s.set_defaults(f=cmd_aplicar_auditoria)
    s = sub.add_parser("auto-aceitar"); s.add_argument("qids", nargs="+"); s.add_argument("--limiar", type=float, default=0.85); s.add_argument("--sem-auditoria", action="store_true"); s.set_defaults(f=cmd_auto_aceitar)
    s = sub.add_parser("adotar-sugestoes"); s.add_argument("qids", nargs="+"); s.set_defaults(f=cmd_adotar_sugestoes)
    s = sub.add_parser("desfazer-auto"); s.add_argument("qids", nargs="+"); s.set_defaults(f=cmd_desfazer_auto)
    s = sub.add_parser("fila"); s.add_argument("qid"); s.add_argument("-n", type=int, default=40); s.set_defaults(f=cmd_fila)
    a = p.parse_args(argv)
    if a.projeto:
        import projetos
        projetos.ativar(a.projeto)
    if a.provedor:
        config.OPENAI_PROVEDOR = a.provedor
        config.OPENAI_MODEL = a.modelo or config.PROVEDORES[a.provedor]["modelo"]
        if not config.PROVEDORES[a.provedor].get("sem_chave"):
            config.OPENAI_API_KEY = config._chave_guardada(a.provedor)
            config.OPENAI_BASE_URL = config.PROVEDORES[a.provedor]["base_url"] or None
    elif a.modelo:
        config.OPENAI_MODEL = a.modelo
    if a.lote:
        config.LLM_LOTE = a.lote
    if a.paralelo:
        config.LLM_PARALELO = a.paralelo
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a.f(a)


if __name__ == "__main__":
    main()
