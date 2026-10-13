"""Relatório HTML estático de conferência por pergunta (frame + codificação + alertas) e índice.

Saída: output/perguntas/<QID>/relatorio.html e output/perguntas/index.html
Sem dependências externas (HTML/CSS/JS puros; funciona offline a partir do OneDrive).
"""
from __future__ import annotations

import html
import json
from datetime import datetime

import codeframe as CF
import coding as CD
import config
import variables as V

_CSS = """
:root{color-scheme:light;--surface:#fcfcfb;--surface-2:#f1f0ee;--border:#dedcd7;--text:#0b0b0b;--text-2:#52514e;--text-3:#7d7b76;
--bar:#2a78d6;--bar-2:#9ec5f4;--warn-bg:#fff4e0;--warn:#8a5300;--ok:#1b7f4d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--surface:#1a1a19;--surface-2:#242423;--border:#3a3937;--text:#fff;--text-2:#c3c2b7;--text-3:#8f8e87;--bar:#3987e5;--bar-2:#1c5cab;--warn-bg:#3a2a08;--warn:#f2c46d;--ok:#5fcf8f}}
:root[data-theme=dark]{color-scheme:dark;--surface:#1a1a19;--surface-2:#242423;--border:#3a3937;--text:#fff;--text-2:#c3c2b7;--text-3:#8f8e87;--bar:#3987e5;--bar-2:#1c5cab;--warn-bg:#3a2a08;--warn:#f2c46d;--ok:#5fcf8f}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:32px 0 8px}
.sub{color:var(--text-2)}.meta{display:flex;flex-wrap:wrap;gap:8px 20px;margin:12px 0;color:var(--text-2)}.meta b{color:var(--text)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--surface-2);border-radius:8px;padding:10px 12px}.tile .l{font-size:12px;color:var(--text-2)}.tile .v{font-size:22px;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
th{color:var(--text-2);font-weight:600;position:sticky;top:0;background:var(--surface)}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{display:flex;align-items:center;gap:8px}.bar i{display:block;height:14px;max-height:24px;background:var(--bar);border-radius:0 4px 4px 0;min-width:2px}
.bar span{color:var(--text-2);font-variant-numeric:tabular-nums;white-space:nowrap}
.chart .row{display:grid;grid-template-columns:minmax(160px,34%) 1fr;gap:10px;align-items:center;padding:3px 0}.chart .row .n{color:var(--text-2);font-size:13px}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;background:var(--surface-2);color:var(--text-2)}
.pill.warn{background:var(--warn-bg);color:var(--warn)}.pill.ok{color:var(--ok)}
.status{font-weight:600}.status.aprovado{color:var(--ok)}.status.rascunho{color:var(--warn)}
.tools{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}input,select{font:inherit;padding:5px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text)}
tr.hid{display:none}td.txt{max-width:460px}small{color:var(--text-3)}
.hist li{color:var(--text-2)}a{color:inherit}
@media (max-width:640px){.chart .row{grid-template-columns:1fr}}
"""


def _e(s) -> str:
    if s is None or (isinstance(s, float) and s != s):  # None / NaN
        return ""
    return html.escape(str(s))


def _pct(n, d) -> str:
    return f"{(100 * n / d):.0f}%" if d else "–"


def gerar(qid: str) -> "Path":
    dados = CF.respostas(qid)
    frame = CF.frame(qid)
    cod = CD.codificacao(qid)
    spec = V.por_id(qid)
    n_resp = dados["n_respondeu"]
    partes = []
    partes.append(f"<h1>{_e(qid)} · {_e(spec.get('rotulo'))}</h1><div class='sub'>{_e(dados.get('enunciado'))}</div>")
    st_frame = (frame or {}).get("status", "—")
    st_cod = (cod or {}).get("status", "—") if cod else "não codificado"
    partes.append(
        "<div class='meta'>"
        f"<span>Base: <b>{_e(dados['base_descricao'])}</b></span>"
        f"<span>Frame: <span class='status {st_frame}'>{_e(st_frame)}</span></span>"
        f"<span>Codificação: <span class='status {st_cod}'>{_e(st_cod)}</span></span>"
        f"<span>Modelo: <b>{_e((cod or frame or {}).get('modelo') or '—')}</b></span>"
        f"<span>Gerado: <b>{datetime.now().strftime('%d/%m/%Y %H:%M')}</b></span></div>"
    )
    partes.append(
        "<div class='tiles'>"
        f"<div class='tile'><div class='l'>Na base</div><div class='v'>{dados['n_base']}</div></div>"
        f"<div class='tile'><div class='l'>Responderam</div><div class='v'>{n_resp}</div></div>"
        f"<div class='tile'><div class='l'>Respostas únicas</div><div class='v'>{dados['n_unicas']}</div></div>"
        f"<div class='tile'><div class='l'>NS/NR por regra</div><div class='v'>{dados['n_nsnr_auto']}</div></div>"
    )
    if cod:
        t = CD.tabela(qid)
        n_alert = int(((t["alertas"] != "") & (t["alertas"] != "não codificado")).sum())
        partes.append(f"<div class='tile'><div class='l'>Com alerta</div><div class='v'>{n_alert}</div></div>")
    partes.append("</div>")

    if not frame:
        partes.append("<p>Frame ainda não gerado. Rode <code>python run.py frame %s induzir</code>.</p>" % _e(qid))
        return _escrever(qid, partes, spec)

    # ---- frame + contagens -------------------------------------------------------------
    nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
    cont_p, cont_s = {c: 0 for c in nomes}, {c: 0 for c in nomes}
    if cod:
        for _, r in t.iterrows():
            if r["primaria"] is not None and not (isinstance(r["primaria"], float) and r["primaria"] != r["primaria"]):
                cont_p[int(r["primaria"])] = cont_p.get(int(r["primaria"]), 0) + int(r["n"])
            if r["secundaria"] is not None and not (isinstance(r["secundaria"], float) and r["secundaria"] != r["secundaria"]):
                cont_s[int(r["secundaria"])] = cont_s.get(int(r["secundaria"]), 0) + int(r["n"])
    partes.append("<h2>Code frame</h2>")
    if frame.get("raciocinio"):
        partes.append(f"<p class='sub'>{_e(frame['raciocinio'])}</p>")
    partes.append("<table><thead><tr><th>Cód.</th><th>Categoria</th><th>Definição</th><th>Exemplos</th>"
                  "<th class='num'>Primária</th><th class='num'>Secundária</th><th class='num'>Menções</th><th class='num'>% resp.</th></tr></thead><tbody>")
    for c in frame["categorias"]:
        k = c["codigo"]
        m = cont_p.get(k, 0) + cont_s.get(k, 0)
        partes.append(
            f"<tr><td class='num'>{k}</td><td><b>{_e(c['nome'])}</b></td><td>{_e(c['definicao'])}</td>"
            f"<td><small>{_e('; '.join(c.get('exemplos') or []))}</small></td>"
            f"<td class='num'>{cont_p.get(k, 0)}</td><td class='num'>{cont_s.get(k, 0)}</td><td class='num'>{m}</td><td class='num'>{_pct(m, n_resp)}</td></tr>"
        )
    partes.append("</tbody></table>")

    if cod:
        # ---- gráfico de menções --------------------------------------------------------
        partes.append("<h2>Menções por categoria (primária + secundária, % dos que responderam)</h2><div class='chart'>")
        ordem = sorted(frame["categorias"], key=lambda c: -(cont_p.get(c["codigo"], 0) + cont_s.get(c["codigo"], 0)))
        maxm = max([cont_p.get(c["codigo"], 0) + cont_s.get(c["codigo"], 0) for c in ordem] + [1])
        for c in ordem:
            m = cont_p.get(c["codigo"], 0) + cont_s.get(c["codigo"], 0)
            w = 100 * m / maxm
            partes.append(f"<div class='row'><div class='n'>{_e(c['nome'])}</div><div class='bar'><i style='width:{w:.1f}%'></i><span>{m} · {_pct(m, n_resp)}</span></div></div>")
        partes.append("</div>")

        # ---- confiança + alertas ----------------------------------------------------------
        partes.append("<h2>Confiança da codificação (respostas únicas)</h2><div class='chart'>")
        bins = [("< 0,60 (revisar)", lambda c: c < 0.6), ("0,60 – 0,79", lambda c: 0.6 <= c < 0.8), ("0,80 – 0,94", lambda c: 0.8 <= c < 0.95), ("≥ 0,95", lambda c: c >= 0.95)]
        confs = [float(c) for c in t["confianca"].dropna()]
        for rot, f in bins:
            n = sum(1 for c in confs if f(c))
            partes.append(f"<div class='row'><div class='n'>{rot}</div><div class='bar'><i style='width:{(100 * n / max(len(confs), 1)):.1f}%'></i><span>{n}</span></div></div>")
        partes.append("</div>")
        alertas = t[(t["alertas"] != "") & (t["alertas"] != "não codificado")]
        partes.append(f"<h2>Alertas para revisão humana ({len(alertas)})</h2>")
        if len(alertas):
            partes.append("<table><thead><tr><th>Resposta</th><th class='num'>n</th><th>Primária</th><th>Secundária</th><th class='num'>Conf.</th><th>Alerta</th></tr></thead><tbody>")
            for _, r in alertas.sort_values("confianca").iterrows():
                partes.append(f"<tr><td class='txt'>{_e(r['texto'])}</td><td class='num'>{r['n']}</td><td>{_e(r['primaria_nome'])}</td><td>{_e(r['secundaria_nome'])}</td>"
                              f"<td class='num'>{r['confianca']:.2f}</td><td><span class='pill warn'>{_e(r['alertas'])}</span></td></tr>")
            partes.append("</tbody></table>")
        else:
            partes.append("<p class='sub'>Nenhum alerta.</p>")

        # ---- tabela completa --------------------------------------------------------------
        partes.append("<h2>Todas as respostas codificadas</h2>")
        opts = "".join(f"<option value='{k}'>{k} · {_e(v)}</option>" for k, v in nomes.items())
        partes.append("<div class='tools'><input id='q' placeholder='filtrar texto…'> <select id='cat'><option value=''>todas as categorias</option>"
                      f"{opts}</select> <select id='ord'><option value='conf'>ordenar: confiança ↑</option><option value='n'>ordenar: frequência ↓</option><option value='cat'>ordenar: categoria</option></select></div>")
        partes.append("<table id='tab'><thead><tr><th>rid</th><th>Resposta</th><th class='num'>n</th><th>Primária</th><th>Secundária</th><th class='num'>Conf.</th><th>Justificativa</th><th>Origem</th></tr></thead><tbody>")
        for _, r in t.iterrows():
            p = "" if r["primaria"] is None or r["primaria"] != r["primaria"] else int(r["primaria"])
            s = "" if r["secundaria"] is None or r["secundaria"] != r["secundaria"] else int(r["secundaria"])
            conf = "" if r["confianca"] is None or r["confianca"] != r["confianca"] else f"{r['confianca']:.2f}"
            partes.append(f"<tr data-p='{p}' data-s='{s}' data-n='{r['n']}' data-c='{conf or 0}'><td class='num'>{r['rid']}</td><td class='txt'>{_e(r['texto'])}</td><td class='num'>{r['n']}</td>"
                          f"<td>{_e(r['primaria_nome'])}</td><td>{_e(r['secundaria_nome'])}</td><td class='num'>{conf}</td><td><small>{_e(r['justificativa'])}</small></td>"
                          f"<td><span class='pill{' ok' if r['origem'] == 'humano' else ''}'>{_e(r['origem'])}</span></td></tr>")
        partes.append("</tbody></table>")
        partes.append("""<script>
const q=document.getElementById('q'),cat=document.getElementById('cat'),ord=document.getElementById('ord'),tb=document.querySelector('#tab tbody');
function filtra(){const t=q.value.toLowerCase(),c=cat.value;for(const tr of tb.rows){const ok=(!t||tr.cells[1].textContent.toLowerCase().includes(t))&&(!c||tr.dataset.p===c||tr.dataset.s===c);tr.classList.toggle('hid',!ok);}}
function ordena(){const rows=[...tb.rows];const k=ord.value;rows.sort((a,b)=>k==='conf'?(+a.dataset.c)-(+b.dataset.c):k==='n'?(+b.dataset.n)-(+a.dataset.n):(+a.dataset.p||999)-(+b.dataset.p||999));rows.forEach(r=>tb.appendChild(r));}
q.oninput=filtra;cat.onchange=filtra;ord.onchange=()=>{ordena();filtra();};ordena();
</script>""")

    if frame.get("historico"):
        partes.append("<h2>Histórico de edições do frame</h2><ul class='hist'>")
        for h in frame["historico"]:
            partes.append(f"<li>{_e(h.get('quando'))} — {_e(json.dumps({k: v for k, v in h.items() if k != 'quando'}, ensure_ascii=False))}</li>")
        partes.append("</ul>")
    return _escrever(qid, partes, spec)


def _escrever(qid: str, partes: list[str], spec: dict):
    doc = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{_e(qid)} · conferência</title><style>{_CSS}</style></head><body><main><p><a href='../index.html'>← índice</a></p>"
           + "".join(partes) + "</main></body></html>")
    p = CF.pasta(qid) / "relatorio.html"
    p.write_text(doc, encoding="utf-8")
    return p


def status_pergunta(qid: str) -> dict:
    frame = CF.frame(qid)
    cod = CD.codificacao(qid)
    resp = CF._ler(qid, "respostas.json")
    n_alert = None
    top = []
    if cod and frame:
        t = CD.tabela(qid)
        n_alert = int(((t["alertas"] != "") & (t["alertas"] != "não codificado")).sum())
        nomes = {c["codigo"]: c["nome"] for c in frame["categorias"]}
        cont: dict = {}
        for p, s, n in zip(t["primaria"], t["secundaria"], t["n"]):
            for k in (p, s):
                if k is not None and k == k:
                    cont[int(k)] = cont.get(int(k), 0) + int(n)
        top = [{"nome": nomes.get(k, str(k)), "n": v} for k, v in sorted(cont.items(), key=lambda kv: -kv[1])[:5]]
    return {
        **CD.resumo_revisao(qid),
        "top": top,
        "qid": qid, "rotulo": V.por_id(qid).get("rotulo"),
        "respostas": resp["n_unicas"] if resp else None,
        "respondeu": resp["n_respondeu"] if resp else None,
        "frame": (frame or {}).get("status"),
        "n_categorias": len([c for c in frame["categorias"] if not c.get("fixa")]) if frame else None,
        "codificacao": (cod or {}).get("status"),
        "alertas": n_alert,
        "revisao_xlsx": (CF.pasta(qid) / "revisao.xlsx").exists(),
        "relatorio": (CF.pasta(qid) / "relatorio.html").exists(),
    }


def gerar_indice() -> "Path":
    linhas = []
    for qid in V.perguntas_codificaveis():
        s = status_pergunta(qid)
        link = f"<a href='{qid}/relatorio.html'>{qid}</a>" if s["relatorio"] else qid
        linhas.append(
            f"<tr><td>{link}</td><td>{_e(s['rotulo'])}</td><td class='num'>{s['respondeu'] or ''}</td><td class='num'>{s['respostas'] or ''}</td>"
            f"<td><span class='status {s['frame'] or ''}'>{_e(s['frame'] or '—')}</span> {('(' + str(s['n_categorias']) + ' cat.)') if s['n_categorias'] else ''}</td>"
            f"<td><span class='status {s['codificacao'] or ''}'>{_e(s['codificacao'] or '—')}</span></td>"
            f"<td class='num'>{'' if s['alertas'] is None else s['alertas']}</td><td>{'sim' if s['revisao_xlsx'] else ''}</td></tr>"
        )
    doc = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>Categorização · índice</title><style>{_CSS}</style></head><body><main><h1>Categorização de respostas abertas — {_e(config.NOME_PROJETO)}</h1>"
           f"<div class='sub'>Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} · modelo {_e(config.OPENAI_MODEL)}</div>"
           "<table><thead><tr><th>Pergunta</th><th>Rótulo</th><th class='num'>Responderam</th><th class='num'>Únicas</th><th>Frame</th><th>Codificação</th><th class='num'>Alertas</th><th>revisao.xlsx</th></tr></thead><tbody>"
           + "".join(linhas) + "</tbody></table></main></body></html>")
    config.PERGUNTAS_OUT.mkdir(parents=True, exist_ok=True)
    p = config.PERGUNTAS_OUT / "index.html"
    p.write_text(doc, encoding="utf-8")
    return p
