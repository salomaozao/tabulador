/* Tabulador — front-end (vanilla JS, sem build). */
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (n, d) => (d ? Math.round((100 * n) / d) + "%" : "–");
const POR_PAGINA = 100;

const filtroInicial = () => ({ q: "", cat: "", alertas: false, comentarios: false, situacao: "", ordem: "conf", origem: "" });
const state = { view: "painel", status: null, qid: null, P: null, filtro: filtroInicial(), mostrar: POR_PAGINA, amostra: 50 };

// ---------------------------------------------------------------- infra
// Janela de "processando": mostra o que o servidor está fazendo (/api/progresso, a cada 0,8 s) —
// etapas, barra, tempo decorrido, estimativa, velocidade e as últimas mensagens.
let progT, relT, busyIni = 0;
const fmtDur = (s) => { s = Math.max(0, Math.round(s)); const m = Math.floor(s / 60); return m ? `${m}min ${String(s % 60).padStart(2, "0")}s` : `${s}s`; };
const fmtMil = (n) => (n >= 1000 ? (n / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mil" : String(n));
function fmtDataHora(iso) {
  if (!iso) return "nunca";
  const d = new Date(iso), hoje = new Date();
  const mesmoDia = d.toDateString() === hoje.toDateString();
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return mesmoDia ? `às ${hora}` : `${d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} às ${hora}`;
}
function barraBusy(pct) {
  const b = $("#busy-bar");
  b.classList.toggle("indet", pct == null);
  b.firstElementChild.style.width = pct == null ? "" : `${Math.max(2, Math.min(100, pct))}%`;
  $("#busy-pct").textContent = pct == null ? "" : `${Math.floor(pct)}%`;
}
function renderProgresso(p) {
  $("#busy-msg").textContent = p.titulo;
  barraBusy(p.indeterminado ? null : p.pct);
  const ativa = (p.etapas || []).find((e) => e.estado === "ativo");
  $("#busy-sub").textContent = p.parando && ativa ? "⏹ Cancelando lotes pendentes e gravando os concluídos…" : ativa ? ativa.nome + "…" : "";
  const st = [`⏱ <b>${fmtDur(p.decorrido)}</b> decorridos`];
  if (p.restante != null && !p.parando) st.push(`${p.restante < 1 ? "<b>quase pronto…</b> <small>(a IA está demorando mais que a média)</small>" : `faltam <b>~${fmtDur(p.restante)}</b>`}${p.restante < 1 ? "" :ativa && ativa.estimativa && !p.feitos ? " <small>(pela média das últimas vezes)</small>" : ""}`);
  if (p.total && ativa && ativa.chave === "ia") st.push(`<b>${p.feitos}</b> de <b>${p.total}</b> ${p.unidade || "respostas"}`);
  if (p.lotes_total) st.push(`lote <b>${p.lotes_feitos}</b>/${p.lotes_total}`);
  if (p.velocidade_min) st.push(`<b>${Math.round(p.velocidade_min)}</b> respostas/min`);
  if (p.ia_ativas) st.push(`🤖 ${p.ia_ativas} chamada(s) à IA em andamento`);
  if (p.ia_feitas) st.push(`${p.ia_feitas} chamada(s) concluída(s)`);
  if (p.tokens) st.push(`${fmtMil(p.tokens)} tokens`);
  if (p.erros) st.push(`<span class="warn-t">${p.erros} lote(s) com erro</span>`);
  if (p.limite_atingido) st.push(`<span class="warn-t">limite do provedor atingido — parando…</span>`);
  if (p.parando) st.push(`<span class="warn-t">⏹ parando a pedido: só os lotes já em andamento terminam</span>`);
  $("#busy-stats").innerHTML = st.join("<span>·</span>");
  const btnParar = $("#busy-parar");
  btnParar.classList.toggle("hidden", !p.lotes_total);
  btnParar.disabled = !!p.parando;
  btnParar.textContent = p.parando ? "Parando…" : "⏹ Parar";
  $("#busy-etapas").innerHTML = (p.etapas || []).map((e) => {
    const ic = e.estado === "feito" ? "✓" : e.estado === "ativo" ? '<span class="mini-spin"></span>' : e.estado === "erro" ? "✕" : e.estado === "interrompida" ? "⏹" : "○";
    const t = e.estado === "ativo" && e.decorrido != null ? fmtDur(e.decorrido) : e.estado === "feito" && e.fim && e.inicio ? fmtDur(e.fim - e.inicio) : "";
    return `<li class="${e.estado}"><span class="ic">${ic}</span><span>${esc(e.nome)}${e.detalhe && e.estado !== "pendente" ? `<span class="det">${esc(e.detalhe)}</span>` : ""}</span><span class="t">${t}</span></li>`;
  }).join("");
  $("#busy-log").innerHTML = (p.eventos || []).slice(-6).reverse().map((e) => `<div><span>${esc(e.hora)}</span>${esc(e.msg)}</div>`).join("");
}
function busy(msg) {
  busyIni = Date.now();
  $("#busy-msg").textContent = msg || "Processando…"; $("#busy-sub").textContent = "";
  $("#busy-stats").innerHTML = ""; $("#busy-etapas").innerHTML = ""; $("#busy-log").innerHTML = "";
  const btnParar = $("#busy-parar");
  btnParar.classList.add("hidden"); btnParar.disabled = false; btnParar.textContent = "⏹ Parar";
  barraBusy(null);
  $("#busy").classList.remove("hidden");
  clearInterval(progT); clearInterval(relT);
  let detalhado = false;
  // sem detalhes do servidor (operação curta): mostra ao menos o tempo passando
  relT = setInterval(() => { if (!detalhado) $("#busy-stats").innerHTML = `⏱ <b>${fmtDur((Date.now() - busyIni) / 1000)}</b> decorridos`; }, 1000);
  const tick = async () => {
    try {
      const p = await (await fetch("/api/progresso")).json();
      if (p.ativo && p.etapas && p.inicio * 1000 >= busyIni - 5000) { detalhado = true; renderProgresso(p); }
    } catch (e) { /* ignora */ }
  };
  setTimeout(tick, 250); progT = setInterval(tick, 800);
}
function idle() { clearInterval(progT); clearInterval(relT); $("#busy").classList.add("hidden"); }
$("#busy-parar").onclick = () => {
  const btn = $("#busy-parar");
  btn.disabled = true; btn.textContent = "Parando…";
  fetch("/api/parar", { method: "POST" }).catch(() => {}); // sem `api()`: não deve abrir outra janela de "processando"
};
// Lotes grandes gastam muitos tokens e muito tempo: confirma antes (pedido da reunião de 30/09).
const AVISO_VOLUME = 500;
function confirmarVolume(n, acao) {
  if (!n || n <= AVISO_VOLUME) return true;
  const lotes = Math.ceil(n / 30);
  return confirm(`${acao}: ${fmtN(n)} respostas vão para a IA (~${fmtN(lotes)} chamadas).\n\n`
    + `Isso pode levar muitos minutos e gastar bastante crédito do provedor. Dá para parar no meio (⏹ Parar): `
    + `o que já foi classificado fica salvo e o resto continua pendente.\n\nContinuar?`);
}
let toastT;
function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.add("hidden"), err ? 9000 : 2800);
}
async function api(path, opts = {}, msg, progresso = false) {
  if (msg) busy(msg, progresso);
  // Operações com progresso (classificação, recodificação, auditoria) são longas e acompanhadas por /api/progresso;
  // não devem ser abortadas pelo navegador enquanto o servidor trabalha.
  const timeoutMs = opts.timeout ?? (progresso ? 0 : 240000);
  const signal = opts.signal || (timeoutMs > 0 && AbortSignal.timeout ? AbortSignal.timeout(timeoutMs) : undefined);
  try {
    // quem está nesta aba vai junto (revisado_por / atualizado_por); codificado porque cabeçalho não aceita acento
    const headers = { "Content-Type": "application/json", "X-Tabulador-Usuario": encodeURIComponent(nomeExibicao()) };
    const r = await fetch(path, { headers, signal, ...opts }).catch((err) => {
      if (err?.name === "TimeoutError") {
        const seg = Math.round(timeoutMs / 1000);
        const tempoTxt = seg >= 60 ? `${Math.round(seg / 60)} min` : `${seg}s`;
        throw new Error(`o servidor demorou mais de ${tempoTxt} para responder.`);
      }
      throw new Error("o Tabulador não respondeu — a janela do programa foi fechada ou reiniciada. Abra-o de novo pelo atalho e recarregue a página.");
    });
    const j = await r.json().catch(() => ({ erro: r.statusText }));
    if (r.status === 409 && j.precisa_confirmar) {
      // mudança que afeta outras perguntas do grupo: mostra o impacto e reenvia já confirmada
      if (msg) idle();
      if (!confirm("Esta mudança afeta o grupo:\n\n• " + j.avisos.join("\n• ") + "\n\nContinuar?")) throw new Error("cancelado");
      const corpo = opts.body ? JSON.stringify({ ...JSON.parse(opts.body), confirmado: true }) : undefined;
      const url = opts.method === "DELETE" ? path + (path.includes("?") ? "&" : "?") + "confirmado=1" : path;
      return api(url, { ...opts, ...(corpo ? { body: corpo } : {}) }, msg, progresso);
    }
    if (!r.ok) throw new Error(j.erro || r.statusText);
    return j;
  } catch (e) { if (e.message !== "cancelado") toast("Erro: " + e.message, true); throw e; }
  finally { if (msg) idle(); }
}
const post = (path, body, msg, progresso, opts = {}) => api(path, { method: "POST", body: JSON.stringify(body || {}), ...opts }, msg, progresso);
const manterScroll = (fn) => { const y = window.scrollY; fn(); window.scrollTo(0, y); };

// ---------------------------------------------------------------- status / topo / barra lateral
async function carregarStatus() {
  state.status = await api("/api/status");
  const S = state.status, b = S.base;
  $("#proj-nome").textContent = S.projeto.nome;
  $("#lista-projetos").innerHTML = S.projetos.map((p) => {
    const atual = p.slug === S.projeto.slug;
    return `<li class="proj-item${atual ? " atual" : ""}${p.ok ? "" : " erro"}" data-slug="${esc(p.slug)}"
      title="${p.ok ? "Trocar para este projeto" : "Este projeto não abre (erro ao carregar)"}">
      <span class="tick">${atual ? "✓" : ""}</span>${esc(p.nome)}<span class="slug">${esc(p.slug)}</span></li>`;
  }).join("");
  document.querySelectorAll("#lista-projetos .proj-item").forEach((li) => (li.onclick = () => {
    if (li.classList.contains("atual")) return fecharPainelProjeto();
    if (li.classList.contains("erro")) return toast("Este projeto não abre: veja o erro na pasta dele.", true);
    fecharPainelProjeto(); trocarProjeto(li.dataset.slug);
  }));
  $("#ia-status").innerHTML = `IA: ${S.ia.tem_chave ? esc(S.ia.modelo) + (S.ia.provedor !== "openai" ? ` <small>(${esc(S.ia.provedor)})</small>` : "") : '<span class="pill warn">sem chave</span>'}`;
  const n = S.nuvem, ns = $("#nuvem-status");
  const dotCls = n.conectada ? "ok" : n.ativa ? "warn" : "off";
  const texto = n.conectada ? `sincronizado ${fmtDataHora(n.ultima_sincronizacao)}` : n.ativa ? "nuvem configurada, sem conexão" : "sem nuvem (local)";
  const titulo = n.conectada ? "Conectado ao banco compartilhado da equipe — a revisão de todo mundo aparece aqui."
    : n.ativa ? "TABULADOR_TURSO_URL configurado, mas não deu para conectar agora — a revisão pode estar desatualizada."
    : "Sem TABULADOR_TURSO_URL configurado: a revisão fica só nesta máquina, não sincroniza com a equipe. Peça as credenciais de nuvem da equipe a quem já usa o Tabulador (ver tabulador/docs/nuvem_turso.md).";
  ns.className = "nuvem-status muted " + dotCls;
  ns.title = titulo;
  ns.innerHTML = `<span class="dot ${dotCls}"></span>${esc(texto)}`;
  document.title = `${S.ia.modo_teste ? "🧪 TESTE · " : ""}Tabulador · ${S.projeto.nome}`;
  aplicarModoTeste(); medirTopo();
  renderSidebar();
}
function pillStatus(s) {
  if (s.codificacao === "aprovado") return '<span class="pill ok">aprovada</span>';
  if (s.codificacao) return s.n_faltantes ? '<span class="pill acc">amostra classificada</span>' : '<span class="pill acc">classificada</span>';
  if (s.frame === "aprovado") return '<span class="pill">categorias ok</span>';
  if (s.frame) return '<span class="pill warn">categorias em rascunho</span>';
  return '<span class="pill">a iniciar</span>';
}
function renderSidebar() {
  $("#li-painel").className = state.view === "painel" ? "ativa" : "";
  $("#li-grupos").className = state.view === "grupos" ? "ativa" : "";
  $("#li-usage").className = state.view === "usage" ? "ativa" : "";
  $("#li-resultados").className = state.view === "resultados" ? "ativa" : "";
  $("#li-gerenciar").className = state.view === "gerenciar" ? "ativa" : "";
  const ul = $("#lista-perguntas"); ul.innerHTML = "";
  const itemPergunta = (s, noGrupo) => {
    const li = document.createElement("li");
    li.className = (s.qid === state.qid ? "ativa" : "") + (noGrupo ? " no-grupo" : "");
    const badges = [pillStatus(s)];
    if (s.codificacao && s.n_codificadas) badges.push(`<span class="pill">${pct(s.n_revisadas, s.n_codificadas)} revisado</span>`);
    li.innerHTML = `<span class="t">${esc(s.rotulo)}</span><span class="small">${esc(s.qid)}${s.backcoding ? " · back-coding" : ""}${s.respondeu ? " · " + s.respondeu + " resp." : ""}</span><span class="b">${badges.join("")}</span>`;
    li.onclick = () => irPara(s.qid);
    return li;
  };
  const vistos = new Set();
  for (const s of state.status.perguntas) {
    if (!s.grupo) { ul.appendChild(itemPergunta(s, false)); continue; }
    if (vistos.has(s.grupo.nome)) continue;  // o grupo aparece uma vez, com as perguntas dele logo abaixo
    vistos.add(s.grupo.nome);
    const li = document.createElement("li");
    li.className = "grupo-li" + (state.view === "grupo" && state.grupo === s.grupo.nome ? " ativa" : "");
    li.innerHTML = `<span class="t">🔗 ${esc(s.grupo.rotulo)}</span><span class="small">grupo · ${esc(s.grupo.membros.join(" + "))}</span>
      <span class="b">${s.grupo.fechado ? '<span class="pill ok">fechado</span>' : '<span class="pill warn">em andamento</span>'}</span>`;
    li.onclick = () => { location.hash = "grupo/" + encodeURIComponent(s.grupo.nome); };
    ul.appendChild(li);
    for (const m of state.status.perguntas.filter((x) => x.grupo?.nome === s.grupo.nome)) ul.appendChild(itemPergunta(m, true));
  }
}
function irPara(qid) { location.hash = qid || "painel"; }

// ---------------------------------------------------------------- painel geral
// ---- cabeçalho do projeto: % de perguntas revisadas + a curva de progressão (src/historico.py)
// ---- cabeçalho do projeto: % de respostas revisadas + a curva de progressão (src/historico.py)
// Destaque primário em RESPOSTAS ÚNICAS (unidade do trabalho), com quebra de humanos e automáticas.
// O gráfico plota a contagem absoluta de conferidas e o total em degrau (não cai quando entra base nova).
const DIA_MS = 86400000;
const diaMs = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const msParaIso = (ms) => new Date(ms).toISOString().slice(0, 10);
// Projeção do ritmo (respostas conferidas/dia, só dias com evolução): neutro = média dos últimos 7 dias ativos,
// otimista = percentil 75, pessimista = percentil 25. Sem 2 dias com evolução não projeta nada.
function ritmosProjecao(serie) {
  const taxas = [];
  for (let i = 1; i < serie.length; i++) {
    const dd = (diaMs(serie[i].dia) - diaMs(serie[i - 1].dia)) / DIA_MS;
    const ganho = (serie[i].respostas_revisadas ?? 0) - (serie[i - 1].respostas_revisadas ?? 0);
    if (dd > 0 && ganho > 0) taxas.push(ganho / dd);
  }
  if (taxas.length < 2) return null;
  const ord = [...taxas].sort((x, y) => x - y);
  const pctl = (q) => ord[Math.min(ord.length - 1, Math.round(q * (ord.length - 1)))];
  const ult = taxas.slice(-7);
  return { pessimista: pctl(0.25), neutro: ult.reduce((x, y) => x + y, 0) / ult.length, otimista: pctl(0.75) };
}
function graficoProgresso(serie, totalUnicas) {
  const dias = (serie || []).map((p) => p.dia);
  if (dias.length < 2) return "";
  const maxResp = totalUnicas || Math.max(...serie.map((p) => Math.max(p.respostas_total || 0, p.respostas_revisadas || 0)), 1);
  const ultimo = serie[serie.length - 1], rev0 = ultimo.respostas_revisadas ?? 0, faltam = Math.max(0, maxResp - rev0);
  // projeção: cada cenário sai do último ponto e vai até 100% (ou até o horizonte de 90 dias)
  const rit = faltam > 0 ? ritmosProjecao(serie) : null;
  const HORIZ = 90;
  const cen = rit ? [["pessimista", "ritmo lento"], ["neutro", "ritmo atual"], ["otimista", "ritmo rápido"]].map(([k, rot]) => {
    const dd = Math.ceil(faltam / rit[k]);
    return { k, rot, taxa: rit[k], dd, fim: Math.min(dd, HORIZ), data: msParaIso(diaMs(ultimo.dia) + dd * DIA_MS) };
  }) : [];
  const horiz = cen.length ? Math.max(...cen.map((c) => c.fim)) : 0;
  const L = 52, R = 508, T = 16, B = 186;  // à direita sobra espaço para a escala em %
  const t0 = diaMs(dias[0]), span = Math.max(1, (diaMs(dias[dias.length - 1]) - t0) / DIA_MS + horiz);
  const x = (ms) => L + (R - L) * (((ms - t0) / DIA_MS) / span);
  const y = (v) => B - (B - T) * (Math.max(0, Math.min(maxResp, v)) / maxResp);
  const xi = (i) => x(diaMs(dias[i]));
  const linhaResp = serie.map((p, i) => `${i ? "L" : "M"}${xi(i).toFixed(1)},${y(p.respostas_revisadas ?? 0).toFixed(1)}`).join(" ");
  const linhaTot = serie.map((p, i) => `${i ? "L" : "M"}${xi(i).toFixed(1)},${y(p.respostas_total || maxResp).toFixed(1)}`).join(" ");
  const area = `${linhaResp} L${xi(dias.length - 1).toFixed(1)},${B} L${xi(0).toFixed(1)},${B} Z`;
  const pontos = serie.map((p, i) => {
    const rev = p.respostas_revisadas ?? 0, tot = p.respostas_total || maxResp;
    const pRev = tot ? Math.round((100 * rev) / tot) : 0;
    return `<circle cx="${xi(i).toFixed(1)}" cy="${y(rev).toFixed(1)}" r="3.5" fill="var(--ok)">
      <title>${diaBR(p.dia)}: ${fmtN(rev)} de ${fmtN(tot)} respostas únicas conferidas (${pRev}%)</title>
    </circle>`;
  }).join("");
  const ticks = [1.0, 0.75, 0.5, 0.25, 0];
  const grade = ticks.map((f) => `<line x1="${L}" y1="${y(f * maxResp).toFixed(1)}" x2="${R}" y2="${y(f * maxResp).toFixed(1)}"${f && f < 1 ? ' stroke-dasharray="3 4"' : ""}/>`).join("");
  const rotulosY = ticks.map((f) => `<text x="4" y="${(y(f * maxResp) + 4).toFixed(1)}">${f === 0 ? "0" : fmtN(Math.round(f * maxResp))}</text>`).join("");
  const rotulosPct = ticks.map((f) => `<text x="${R + 6}" y="${(y(f * maxResp) + 3.5).toFixed(1)}">${Math.round(f * 100)}%</text>`).join("");
  // rótulos de data só quando cabem (eixo em escala de calendário): o último dia real sempre aparece; o fim projetado só se couber
  const xsRot = [];
  dias.forEach((d, i) => {
    const xx = xi(i), ult = i === dias.length - 1;
    if (xsRot.length && xx - xsRot[xsRot.length - 1].x < 36) { if (!ult) return; xsRot.pop(); }  // o último dia real sempre aparece
    xsRot.push({ x: xx, d });
  });
  const xUlt = xsRot[xsRot.length - 1].x;
  const rotulosX = xsRot.map(({ x: xx, d }) => `<text x="${(xx - 16).toFixed(1)}" y="${B + 22}">${diaBR(d)}</text>`).join("");
  const neutro = cen.find((c) => c.k === "neutro");
  const quandoDe = (c) => (c.dd > HORIZ ? `além de ${HORIZ} dias` : diaBR(c.data));
  const projecao = cen.map((c) => {
    const xf = x(diaMs(ultimo.dia) + c.fim * DIA_MS), yf = y(Math.min(maxResp, rev0 + c.taxa * c.fim));
    const d = `M${xi(dias.length - 1).toFixed(1)},${y(rev0).toFixed(1)} L${xf.toFixed(1)},${yf.toFixed(1)}`;
    const dica = `<title>Projeção (${c.rot}, ~${fmtN(Math.round(c.taxa))} respostas/dia): 100% em ${quandoDe(c)}</title>`;
    return `<path fill="none" stroke="var(--text-3)" stroke-width="${c.k === "neutro" ? 1.6 : 1.2}" stroke-opacity="${c.k === "neutro" ? 0.95 : 0.6}" stroke-dasharray="3 3" d="${d}">${dica}</path>
      <path fill="none" stroke="transparent" stroke-width="9" d="${d}">${dica}</path>`;
  }).join("");
  const rotuloFim = neutro && neutro.dd <= HORIZ && x(diaMs(neutro.data)) - xUlt >= 36 ? `<text x="${(x(diaMs(neutro.data)) - 16).toFixed(1)}" y="${B + 22}">${diaBR(neutro.data)}</text>` : "";
  const previsao = !neutro ? "" : (() => {
    const ot = cen.find((c) => c.k === "otimista"), pe = cen.find((c) => c.k === "pessimista");
    return `<span class="small prev">previsão de conclusão: <b>${quandoDe(neutro)}</b> no ritmo atual (entre ${quandoDe(ot)} e ${quandoDe(pe)})</span>`;
  })();
  return `<div class="grafico">
    <svg viewBox="0 0 560 214" width="100%" height="196" role="img"
         aria-label="Progressão: volume de respostas únicas conferidas em relação ao total">
      <defs><linearGradient id="gProg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--ok)" stop-opacity="0.06"/><stop offset="1" stop-color="var(--ok)" stop-opacity="0.38"/>
      </linearGradient></defs>
      <g stroke="var(--border)">${grade}</g>
      <g font-size="10.5" fill="var(--text-3)" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">${rotulosY}${rotulosX}</g>
      <g font-size="9.5" fill="var(--text-3)" opacity="0.8" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">${rotulosPct}${rotuloFim}</g>
      <path fill="none" stroke="var(--text-3)" stroke-width="1.8" stroke-dasharray="4 4" stroke-linejoin="round" d="${linhaTot}"/>
      <path d="${area}" fill="url(#gProg)" stroke="none"/>
      ${projecao}
      <path fill="none" stroke="var(--ok)" stroke-width="2.6" stroke-linejoin="round" d="${linhaResp}"/>
      ${pontos}
    </svg>
    <div class="legenda">
      <span><i class="sw ok"></i>respostas conferidas</span>
      <span><i class="sw total"></i>total de respostas únicas</span>
      ${cen.length ? `<span><i class="sw proj"></i>projeção</span>` : ""}
      ${previsao}
      <span class="small">contagem absoluta de respostas únicas — a linha sobe a cada revisão; entrada de dados cria degrau no total</span>
    </div>
  </div>`;
}
function diaBR(iso) { return `${iso.slice(8, 10)}/${iso.slice(5, 7)}`; }
function cabecalhoProjeto(S) {
  const H = S.historico;
  if (!H || !H.total) return "";
  const R = H.respostas || {}, tot = R.unicas || 0;
  const nRev = R.revisadas || 0, nCls = R.classificadas || 0;
  const nAuto = R.revisadas_auto || 0;
  const nHum = R.revisadas_humano ?? Math.max(0, nRev - nAuto);
  const nAConf = Math.max(0, nCls - nRev), nSem = Math.max(0, tot - nCls);
  const faltam = R.faltam ?? Math.max(0, tot - nRev);
  const pctRev = tot ? Math.floor((100 * nRev) / tot) : 0;
  const parte = (n) => `${tot ? (100 * n) / tot : 0}%`;
  return `<div class="cab">
    <div class="cab-num">
      <div class="pct-linha">
        <div class="pct-grande">${pctRev}<small>%</small></div>
        <div class="pct-destaque">
          <div class="pct-lab"><b>${fmtN(nRev)}</b> de <b>${fmtN(tot)}</b> respostas únicas conferidas</div>
          <div class="pct-faltam">${faltam ? `faltam <b>${fmtN(faltam)}</b> respostas para concluir o projeto` : "todas as respostas conferidas!"}</div>
        </div>
      </div>
      <div class="pct-sec">
        <b>${fmtN(nHum)}</b> confirmadas por pessoas${nAuto ? ` · <b>⚡ ${fmtN(nAuto)}</b> automáticas` : ""}
        ${nAConf ? ` · <b>${fmtN(nAConf)}</b> classificadas a conferir` : ""}${nSem ? ` · <b>${fmtN(nSem)}</b> a classificar` : ""}
        <div class="small muted" style="margin-top:4px">${H.n_revisadas} de ${H.total} pergunta${H.total === 1 ? "" : "s"} com a revisão concluída</div>
      </div>
      <div class="pilha" title="${fmtN(nHum)} por pessoas · ${fmtN(nAuto)} automáticas · ${fmtN(nAConf)} a conferir · ${fmtN(nSem)} ainda não classificadas">
        <i class="rev-hum" style="width:${parte(nHum)}"></i>
        <i class="rev-auto" style="width:${parte(nAuto)}"></i>
        <i class="cls" style="width:${parte(nAConf)}"></i>
        <i class="nada" style="width:${parte(nSem)}"></i>
      </div>
      <div class="legenda">
        <span><i class="sw ok"></i>pessoas ${fmtN(nHum)}</span>
        ${nAuto ? `<span><i class="sw auto"></i>automáticas ${fmtN(nAuto)}</span>` : ""}
        <span><i class="sw acc"></i>a conferir ${fmtN(nAConf)}</span>
        <span><i class="sw nada"></i>a classificar ${fmtN(nSem)}</span>
      </div>
    </div>
    ${graficoProgresso(H.serie, tot)}
  </div>`;
}
function renderPainel() {
  state.view = "painel"; state.qid = null; state.P = null; renderSidebar();
  const S = state.status, b = S.base, R = S.resultados;
  const avisos = [];
  if (!S.ia.tem_chave) avisos.push(`<div class="aviso">A chave da OpenAI ainda não foi configurada — sem ela a IA não funciona. <button class="btn sm" data-acao="ia">⚙ Configurar IA</button></div>`);
  if (!b.fonte_existe) avisos.push(`<div class="aviso">Planilha-fonte não encontrada: <code>${esc(b.fonte)}</code></div>`);
  else if (!b.carregada) avisos.push(`<div class="aviso">A planilha ainda não foi lida. <button class="btn sm primary" data-acao="load">Ler a planilha agora</button></div>`);

  const cardPergunta = (s, dentroDoGrupo) => {
    const cod = s.n_codificadas || 0, tot = s.n_unicas || s.respostas || 0, rev = s.n_revisadas || 0;
    const barra = (v, d, cls = "") => `<div class="prog ${cls}"><i style="width:${d ? (100 * v) / d : 0}%"></i></div>`;
    const pctRev = tot ? Math.round((100 * rev) / tot) : 0;
    // canto direito do card: quantas já foram revisadas do total — é o que diz se falta trabalho aqui
    const contador = tot ? `<div class="contador" title="${fmtN(rev)} de ${fmtN(tot)} respostas conferidas por pessoas">
        <div class="n">${fmtN(rev)}<i> / ${fmtN(tot)}</i></div><div class="lab">revisadas / total</div>
        <div class="bar"><i style="width:${pctRev}%"></i></div></div>` : "";
    // badge de grupo: aparece logo abaixo do título do card quando a pergunta pertence a um grupo
    const grupoBadge = s.grupo && !dentroDoGrupo
      ? (() => {
          const outros = (s.grupo.membros || []).filter((m) => m !== s.qid).join(', ');
          return `<span class="grupo-badge" title="Grupo: ${esc(s.grupo.rotulo)}">🔗 ${esc(s.grupo.rotulo)}${outros ? ` (+${esc(outros)})` : ''}</span>`;
        })()
      : '';
    return `<div class="card" data-qid="${esc(s.qid)}">
      <div class="card-h"><b>${esc(s.rotulo)}</b><span class="small">${esc(s.qid)}</span></div>
      ${grupoBadge}
      ${contador}
      <div class="small">${s.respondeu ? `${s.respondeu} responderam · ${tot} respostas únicas` : "respostas ainda não lidas"}</div>
      <div>${pillStatus(s)} ${s.alertas ? `<span class="pill warn">${s.alertas} alertas</span>` : ""}</div>
      ${s.codificacao ? `
        <div class="kv"><span>Classificadas</span><span>${cod} de ${tot}</span></div>${barra(cod, tot)}
        <div class="kv"><span>Revisadas</span><span>${s.n_revisadas} (${pct(s.n_revisadas, cod)})</span></div>${barra(s.n_revisadas, cod, "hum")}
        ${s.n_revisadas ? `<div class="small dist-status">✓ ${s.n_confirmadas - (s.n_confirmadas_auto || 0)} manual${s.n_confirmadas_auto ? ` · ⚡ ${s.n_confirmadas_auto} automática${s.n_confirmadas_auto === 1 ? "" : "s"}` : ""}${s.n_corrigidas ? ` · ✎ ${s.n_corrigidas} corrigida${s.n_corrigidas === 1 ? "" : "s"}` : ""}</div>` : ""}
        <div class="kv"><span>Acerto da IA</span><span>${s.acerto_ia == null ? "–" : Math.round(100 * s.acerto_ia) + "%"} <small>${s.n_avaliadas_ia ? `(${s.n_avaliadas_ia} conferidas)` : ""}</small></span></div>
        ${s.top && s.top.length ? `<div class="small top">Mais citadas: ${s.top.slice(0, 3).map((t) => esc(t.nome)).join(" · ")}</div>` : ""}` : ""}
      <button class="btn sm ${s.codificacao === "aprovado" ? "" : "primary"}">${s.codificacao === "aprovado" ? "Ver" : s.frame ? "Continuar" : "Começar"}</button>
    </div>`;
  };
  // perguntas de um grupo ficam juntas num bloco com o andamento do grupo; as demais, em cartões soltos
  const blocos = [], gruposVistos = new Map();
  for (const s of S.perguntas) {
    if (!s.grupo) {
      const ult = blocos[blocos.length - 1];
      if (ult && ult.solta) ult.itens.push(s); else blocos.push({ solta: true, itens: [s] });
    } else if (gruposVistos.has(s.grupo.nome)) gruposVistos.get(s.grupo.nome).itens.push(s);
    else { const b = { grupo: s.grupo, itens: [s] }; gruposVistos.set(s.grupo.nome, b); blocos.push(b); }
  }
  const andamentoGrupo = (g) => g.andamento.map((a) => `<span class="pill ${a.classificacao === "aprovado" ? "ok" : a.quadro_aprovado ? "" : "warn"}" title="${a.classificacao === "aprovado" ? "concluída" : a.quadro_aprovado ? "categorias aprovadas; classificação em andamento" : "categorias ainda não aprovadas"}">${esc(a.qid)} ${a.classificacao === "aprovado" ? "✓ concluída" : a.quadro_aprovado ? "em revisão" : "categorias a aprovar"}</span>`).join(" ");
  const cards = blocos.map((b) => b.solta
    ? `<div class="cards">${b.itens.map((s) => cardPergunta(s, false)).join("")}</div>`
    : `<div class="bloco-grupo">
        <div class="bloco-grupo-cab"><div><b>🔗 ${esc(b.grupo.rotulo)}</b> ${b.grupo.fechado ? '<span class="pill ok">✓ grupo fechado</span>' : ""}
          <div class="small">${b.grupo.tem_quadro ? "Um quadro de categorias para as perguntas do grupo" : "Ainda sem quadro de categorias: gere no grupo"} · ${andamentoGrupo(b.grupo)}</div></div>
          <button class="btn ${b.grupo.fechado ? "" : "primary"} b-abrir-grupo" data-grupo="${esc(b.grupo.nome)}">${b.grupo.tem_quadro ? "Abrir o grupo" : "Gerar categorias do grupo"}</button></div>
        <div class="cards">${b.itens.map((s) => cardPergunta(s, true)).join("")}</div></div>`).join("");

  const aprovadas = S.perguntas.filter((s) => s.codificacao === "aprovado").length;
  const nArq = Object.values(R).filter((r) => r.existe).length;
  $("#main").innerHTML = `
    <h1>${esc(S.projeto.nome)}</h1>
    <div class="small">Planilha-fonte: ${esc(b.fonte)}</div>
    ${b.carregada ? `<div class="small">Base: <b>${b.n}</b> respondentes · atualizada ${b.atualizada_em}</div>` : ""}
    ${cabecalhoProjeto(S)}
    ${avisos.join("")}
    <h2>Perguntas abertas <small>${aprovadas} de ${S.perguntas.length} aprovadas${gruposVistos.size ? ` · ${[...gruposVistos.values()].filter((b) => b.grupo.fechado).length} de ${gruposVistos.size} grupos fechados` : ""}</small></h2>
    ${cards}
    <h2>Resultados</h2>
    <div class="info">📦 ${aprovadas} pergunta(s) aprovada(s) · ${nArq} arquivo(s) gerado(s). O resumo das categorias e os downloads (planilha final, codebook, cruzamentos) ficam na aba <a href="#resultados"><b>Resultados</b></a>.</div>`;
  document.querySelectorAll(".card").forEach((c) => (c.onclick = () => irPara(c.dataset.qid)));
  document.querySelectorAll(".b-abrir-grupo").forEach((b) => (b.onclick = () => { location.hash = "grupo/" + encodeURIComponent(b.dataset.grupo); }));
  document.querySelectorAll("[data-acao=ia]").forEach((b) => (b.onclick = abrirIA));
  document.querySelectorAll("[data-acao=load]").forEach((b) => (b.onclick = recarregarPlanilha));
}

// ---------------------------------------------------------------- pergunta
async function abrir(qid) {
  if (state.qid !== qid) { state.filtro = filtroInicial(); state.mostrar = POR_PAGINA; }
  state.qid = qid; state.view = "pergunta"; renderSidebar();
  state.P = await api(`/api/pergunta/${qid}`, {}, "Abrindo pergunta…");
  if (!state.P.respostas || !state.P.respostas.n_unicas) {
    try { state.P = await post(`/api/pergunta/${qid}/preparar`, {}, "Lendo respostas da base…"); } catch (e) { /* base não carregada */ }
  }
  prepararItens(); render(); window.scrollTo(0, 0);
  iniciarPresenca(qid);
}

// ---------------------------------------------------------------- presença (avisa edição simultânea)
let presencaT = null, presencaQid = null;
function pararPresenca() {
  clearInterval(presencaT); presencaT = null;
  if (presencaQid) { try { navigator.sendBeacon(`/api/pergunta/${presencaQid}/presenca/sair`); } catch (e) { /* ignora */ } }
  presencaQid = null;
}
async function presencaTick(qid) {
  try {
    const r = await (await fetch(`/api/pergunta/${qid}/presenca`, { method: "POST" })).json();
    if (state.qid === qid) renderPresenca(r.outros || []);
  } catch (e) { /* heartbeat: falha em silêncio, não atrapalha a revisão */ }
}
function iniciarPresenca(qid) {
  pararPresenca(); presencaQid = qid;
  presencaTick(qid);
  presencaT = setInterval(() => presencaTick(qid), 12000);
}
function renderPresenca(outros) {
  const el = $("#presenca-banner");
  if (!el) return;
  el.innerHTML = outros.length
    ? `<div class="aviso">⚠ ${outros.length === 1 ? `<b>${esc(outros[0])}</b> também está` : `<b>${outros.map(esc).join(", ")}</b> também estão`} revisando esta pergunta agora. Evitem mexer ao mesmo tempo: quem gravar por último apaga a mudança do outro.</div>`
    : "";
}
window.addEventListener("beforeunload", pararPresenca);

// ---------------------------------------------------------------- presença do PROJETO INTEIRO (PEND-09)
// Não confundir com a de cima (por pergunta, avisa edição simultânea). Esta é a sidebar "quem está
// aqui agora" pro projeto todo. sessao_id é por ABA (memória, nunca salvo), nome_exibicao é
// autodeclarado uma vez e fica no localStorage (assim não pergunta de novo em cada aba nova).
const SESSAO_ID = (crypto.randomUUID ? crypto.randomUUID() : `sessao-${Date.now()}-${Math.random().toString(36).slice(2)}`);
let presencaProjT = null;
function nomeExibicao() { return localStorage.getItem("tabulador_nome") || ""; }
function localizacaoAtual() {
  if (state.view === "pergunta" && state.qid) return `Pergunta ${state.qid}`;
  const nomes = { painel: "Painel geral", resultados: "Resultados", grupos: "Grupos de perguntas", usage: "Consumo da IA", gerenciar: "Gerenciar projeto", novo: "Criando projeto novo" };
  return nomes[state.view] || state.view || "—";
}
async function presencaProjTick() {
  const nome = nomeExibicao();
  if (!nome) return;
  try {
    const r = await (await fetch("/api/presenca", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessao_id: SESSAO_ID, nome_exibicao: nome, localizacao: localizacaoAtual() }),
    })).json();
    renderPresencaProjeto(r.outros || []);
  } catch (e) { /* heartbeat: falha em silêncio */ }
}
function renderPresencaProjeto(outros) {
  const bloco = $("#bloco-presenca-projeto"), lista = $("#lista-presenca-projeto");
  if (!bloco || !lista) return;
  bloco.classList.toggle("hidden", outros.length === 0);
  lista.innerHTML = outros.map((o) => `<li><b>${esc(o.nome_exibicao)}</b><span class="small muted"> · ${esc(o.localizacao)}</span></li>`).join("");
}
function pararPresencaProjeto() {
  clearInterval(presencaProjT); presencaProjT = null;
  try { navigator.sendBeacon("/api/presenca/sair", new Blob([JSON.stringify({ sessao_id: SESSAO_ID })], { type: "application/json" })); } catch (e) { /* ignora */ }
}
window.addEventListener("beforeunload", pararPresencaProjeto);
async function garantirIdentificacao() {
  if (nomeExibicao()) return;
  const dlg = $("#dlg-identificacao");
  await new Promise((resolve) => {
    dlg.addEventListener("close", function onClose() {
      dlg.removeEventListener("close", onClose);
      const nome = $("#ident-nome").value.trim();
      if (nome) localStorage.setItem("tabulador_nome", nome);
      resolve();
    });
    dlg.showModal();
  });
}
function iniciarPresencaProjeto() {
  $("#presenca-eu").textContent = nomeExibicao() ? `(você: ${nomeExibicao()})` : "";
  presencaProjTick();
  presencaProjT = setInterval(presencaProjTick, 12000);
}
async function refresh(payload) {
  if (state.view === "grupo") return refreshGrupo(payload);  // a tela do grupo junta as perguntas: recarrega tudo
  state.P = payload || (await api(`/api/pergunta/${state.qid}`)); prepararItens();
  manterScroll(render); carregarStatus();
  avisosDoPayload(payload);
}
function avisosDoPayload(payload) {
  if (payload?.limite_atingido) {
    toast(`Limite de uso do provedor atingido: parei a classificação. ${payload.nao_tentados} resposta(s) ficaram pendentes — espere um pouco (ou troque de provedor em '⚙ Configurar IA') e tente de novo.`, true);
  } else if (payload?.parado_usuario) {
    toast(`Classificação interrompida a seu pedido. O que já foi classificado foi salvo; ${payload.nao_tentados} resposta(s) permanecem pendentes.`);
  } else if (payload?.n_erro) {
    toast(`${payload.n_erro} resposta(s) deram erro na IA e continuam sem classificação (não foram para Outros). Use "Classificar as restantes" para tentar de novo.`, true);
  }
}
function prepararItens() { for (const r of state.P.itens || []) if (r._alertas_ia === undefined) r._alertas_ia = r.alertas; }

function catsValidas() { return state.P.frame?.categorias || []; }
function nomeCat(c) { const x = catsValidas().find((k) => k.codigo === +c); return x ? x.nome : ""; }

// recalcula contagens e números da revisão no navegador (sem recarregar tudo a cada clique)
function recalcular() {
  const P = state.P, cont = {};
  let cod = 0, conf = 0, confAuto = 0, corr = 0, corrIA = 0, alt = 0, cong = 0;
  for (const r of P.itens) {
    for (const [k, campo] of [[r.primaria, "primaria"], [r.secundaria, "secundaria"]]) {
      if (k == null) continue;
      cont[k] = cont[k] || { primaria: 0, secundaria: 0 }; cont[k][campo] += r.n;
    }
    if (r.primaria == null || r.origem === "erro") continue;  // erro na chamada = ainda falta classificar
    cod++;
    if (r.revisao === "confirmada") { conf++; if (r.validado_por === "auto") confAuto++; }
    if (r.revisao === "corrigida") { corr++; if (r.corrigido_de_nome != null) corrIA++; }
    if (r.revisao === "alterada") { alt++; }
    if (r.revisao === "congelada") { cong++; }
  }
  P.contagens = cont;
  P.n_alertas = P.itens.filter((r) => r.alertas && r.alertas !== "não codificado").length;
  P.n_comentarios_pendentes = P.itens.filter((r) => r.comentario_pendente).length;
  // confirmadas pelo supervisor.py (auto) não medem o acerto da IA — mesma regra de coding.resumo_revisao
  const aval = conf - confAuto + corrIA, tot = P.itens.length;
  P.revisao = { n_unicas: tot, n_codificadas: cod, n_faltantes: tot - cod, n_confirmadas: conf, n_confirmadas_auto: confAuto, n_corrigidas: corr, n_alteradas: alt, n_congeladas: cong, n_revisadas: conf + corr, acerto_ia: aval ? (conf - confAuto) / aval : null, n_avaliadas_ia: aval };
}
function aplicarItem(r, it) {
  const au = it.auditoria || null;
  Object.assign(r, {
    primaria: it.primaria, secundaria: it.secundaria, origem: it.origem, confianca: it.confianca,
    comentario: it.comentario || null, comentario_pendente: !!it.comentario && !it.comentario_aplicado_em,
    revisao: it.primaria == null ? null : it.congelada ? "congelada" : it.alterada ? "alterada" : it.origem === "humano" ? "corrigida" : it.validado ? "confirmada" : "pendente",
    congelada: it.congelada || null,
    alterada: !!it.alterada,
    alterada_motivo: it.alterada_motivo || null,
    alterada_em: it.alterada_em || null,
    alterada_de: it.alterada_de ?? null,
    validado_por: it.validado_por ?? null,
    corrigido_de_nome: it.corrigido_de != null ? nomeCat(it.corrigido_de) : null,
    auditoria: au,
    sugestao_nome: au && au.ok === false ? nomeCat(au.primaria) : null,
    sugestao_sec_nome: au && au.ok === false && au.secundaria != null ? nomeCat(au.secundaria) : null,
    ia_original_nome: it.ia_original ? nomeCat(it.ia_original.primaria) : null,
  });
  r.primaria_nome = nomeCat(r.primaria); r.secundaria_nome = nomeCat(r.secundaria);
  r.alertas = (r.revisao === "pendente" || r.revisao === "alterada") ? r._alertas_ia || "" : r.revisao ? "" : "não codificado";
}

function badgeSaudeQuadro() {
  const S = state.P?.saude || [];
  const n = S.length;
  if (!n) return { classe: "ghost", texto: " (100% ok)" };
  const criticos = S.filter((a) => a.tipo === "ampla" || a.tipo === "confusao" || a.tipo === "outros").length;
  const classe = criticos > 0 ? "warn" : "";
  return { classe, texto: ` (${n})` };
}

function render() {
  if (state.view === "grupo") return renderGrupo();
  const P = state.P, R = P.respostas || {}, F = P.frame, C = P.codificacao, V = P.revisao;
  const noGrupo = !!P.grupo?.tem_quadro;  // o quadro é do grupo: gerar/editar lá, aqui só aprovar
  const frameOk = F && F.status === "aprovado", codOk = C && C.status === "aprovado";
  const faltam = V ? V.n_faltantes : 0;
  const bs = badgeSaudeQuadro();
  // contador do canto direito: quantas respostas já foram conferidas do total desta pergunta.
  // Fica dentro do cabeçalho sticky, então acompanha a rolagem da tabela de revisão.
  const totRev = V ? V.n_unicas : (R.n_unicas || 0), nRev = V ? V.n_revisadas : 0;
  const pctRev = totRev ? Math.round((100 * nRev) / totRev) : 0;
  $("main").innerHTML = `
    <div class="q-cab">
      <div class="q-cab-txt">
        <div class="small"><a href="#painel">← Painel geral</a></div>
        <h1>${esc(P.rotulo)} <small>${esc(P.qid)}</small></h1>
        <div class="muted">${esc(R.enunciado || P.enunciado || "")}</div>
        <div class="small">Quem respondeu: ${esc(R.base_descricao || "")}</div>
        <div id="presenca-banner"></div>
        ${C ? `<div style="margin-top:6px"><a class="btn sm ghost" href="#area-revisao" id="link-ir-revisao">↓ ir para a revisão</a></div>` : ""}
      </div>
      ${totRev ? `<div class="sticky-num" title="${fmtN(nRev)} de ${fmtN(totRev)} respostas conferidas por pessoas">
        <div class="n">${fmtN(nRev)}<i> / ${fmtN(totRev)}</i></div>
        <div class="lab">revisadas / total</div>
        <div class="bar"><i style="width:${pctRev}%"></i></div>
      </div>` : ""}
    </div>
    ${renderGrupoBanner(P)}
    <div class="tiles">
      <div class="tile"><div class="l">Responderam</div><div class="v">${R.n_respondeu ?? "–"}</div></div>
      <div class="tile"><div class="l">Respostas únicas</div><div class="v">${R.n_unicas ?? "–"}</div></div>
      <div class="tile"><div class="l">NS/NR automático</div><div class="v">${R.n_nsnr_auto ?? "–"}</div></div>
      <div class="tile"><div class="l">Classificadas</div><div class="v">${V ? V.n_codificadas : "–"}</div></div>
      <div class="tile"><div class="l">Revisadas por você</div><div class="v">${V ? V.n_revisadas : "–"}</div></div>
      <div class="tile"><div class="l">Acerto da IA</div><div class="v">${V && V.acerto_ia != null ? Math.round(100 * V.acerto_ia) + "%" : "–"}</div></div>
    </div>
    <div class="stepper">
      <div class="step ${R.n_unicas ? "done" : "atual"}"><b>1. Respostas</b>${R.n_unicas ? R.n_unicas + " únicas" : "ler da base"}</div>
      <div class="step ${frameOk ? "done" : R.n_unicas ? "atual" : ""}"><b>2. Categorias</b>${F ? (frameOk ? "aprovadas" : "rascunho — revise e aprove") : "gerar com IA"}</div>
      <div class="step ${codOk ? "done" : frameOk ? "atual" : ""}"><b>3. Classificação e revisão</b>${C ? (codOk ? "aprovada" : faltam ? `amostra: ${V.n_codificadas} de ${V.n_unicas}` : "confira e corrija") : "testar numa amostra"}</div>
      <div class="step ${codOk ? "done" : ""}"><b>4. Aprovação</b>${codOk ? "nos resultados ✓" : "pendente"}</div>
    </div>

    <h2>Instruções para a IA <small>(valem para gerar categorias e para classificar)</small></h2>
    <div class="box-instr">
      ${P.instrucoes_fixas ? `<div class="small" style="margin-bottom:6px">Regra fixa desta pergunta: ${esc(P.instrucoes_fixas)}</div>` : ""}
      <textarea id="instr" placeholder="Ex.: 'Reclamações de preço e de mensalidade são a mesma categoria', 'Separe professores de coordenação pedagógica'…">${esc(P.instrucoes)}</textarea>
      <div class="small">Salvo automaticamente ao sair do campo. Vale a partir da próxima vez que a IA gerar categorias ou classificar.</div>
    </div>

    <h2>Categorias
      ${F ? `<span class="pill ${frameOk ? "ok" : "warn"}">${frameOk ? "aprovadas" : "rascunho"}${F.fixo ? " · fixo" : ""}</span>` : ""}
      <span class="acoes">
        ${P.grupo && !F ? `<a class="btn primary" href="#grupo/${esc(P.grupo.nome)}">✨ Gerar categorias do grupo</a>` : ""}
        ${noGrupo ? `<a class="btn" href="#grupo/${esc(P.grupo.nome)}">🔗 Editar no grupo</a>` : ""}
        ${!F && !P.grupo ? `<button class="btn primary" id="b-induzir">✨ Gerar categorias com IA</button>` : ""}
        ${F && !F.fixo && !noGrupo ? `<button class="btn" id="b-induzir">✨ Gerar do zero</button>` : ""}
        ${F ? `<button class="btn" id="b-janela-cat" title="Cada categoria com definição, exemplos${C ? ", perfil de quem citou e confirmação em bloco" : ""}">🗂 Revisar por categoria</button>` : ""}
        ${F ? `<button class="btn ${bs.classe}" id="b-saude-quadro" title="Saúde do quadro: diagnóstico por categoria e soluções propostas">🩺 Saúde do quadro${bs.texto}</button>` : ""}
        ${F && !frameOk ? `<button class="btn ok" id="b-aprovar-frame">✓ Aprovar categorias</button>` : ""}
      </span>
    </h2>
    ${F ? (noGrupo ? renderFrameLeitura() : renderFrame()) : `<div class="info">A IA lê as respostas e propõe uma lista fechada de categorias com definição e exemplos. Você pode renomear, mesclar, excluir, acrescentar ou pedir ajustes à IA antes de aprovar.</div>`}

    <h2 id="area-revisao">Classificação das respostas
      ${C ? `<span class="pill ${codOk ? "ok" : "warn"}">${codOk ? "aprovada" : "rascunho"}</span>` : ""}
      <span class="acoes">
        ${codOk ? `<button class="btn" id="b-reabrir">Reabrir para correções</button>` : ""}
        ${C ? `<a class="btn ghost" href="/relatorio/${P.qid}" target="_blank">Relatório</a><a class="btn ghost" href="/revisao/${P.qid}.xlsx">Baixar Excel</a>` : ""}
      </span>
    </h2>
    ${!frameOk ? `<div class="info">Aprove as categorias para liberar a classificação.</div>` : ""}
    ${C ? renderRevbar() : ""}
    ${frameOk && !codOk ? renderAcoesCod() : ""}
    ${C ? renderCodificacao() : ""}
  `;
  $("#link-ir-revisao")?.addEventListener("click", (e) => {
    e.preventDefault();
    $("#area-revisao")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#instr").onblur = async (e) => { if (e.target.value !== P.instrucoes) { await post(`/api/pergunta/${P.qid}/instrucoes`, { texto: e.target.value }); P.instrucoes = e.target.value; toast("Instruções salvas"); } };
  $("#b-induzir")?.addEventListener("click", async () => {
    if (F && !confirm("Gerar do zero substitui as categorias atuais" + (C ? " e a classificação terá de ser refeita" : "") + ". Para ajustes pontuais, use 'Pedir ajuste à IA'. Continuar?")) return;
    refresh(await post(`/api/pergunta/${P.qid}/frame/induzir`, {}, "Gerando categorias com IA…"));
  });
  $("#b-aprovar-frame")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/frame/aprovar`, {}, "Aprovando…")));
  $("#b-janela-cat")?.addEventListener("click", () => abrirJanelaCategorias());
  $("#b-saude-quadro")?.addEventListener("click", () => abrirJanelaSaudeQuadro());
  $("#b-reabrir")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/reabrir`, {}, "Reabrindo…")));
  bindFrame(); bindAcoesCod(); bindCodificacao(); bindAprovarBar();
  medirAlturasFixas(); observarCabecalho();
}

// ---------------------------------------------------------------- frame
// Categorias nos menus de escolha: ordem alfabética (Outros e NS/NR no fim) e sem o número, que não ajuda o analista.
// O número continua valendo no atalho de teclado (digitar o código na linha da resposta).
const catsAlfabetica = (cats) => [...cats].sort((a, b) => (!!a.fixa - !!b.fixa) || a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" }));
const optsCategorias = (cats, { excluir = null, sel = null } = {}) => catsAlfabetica(cats).filter((c) => c.codigo !== excluir)
  .map((c) => `<option value="${c.codigo}" ${c.codigo === sel ? "selected" : ""}>${esc(c.nome)}</option>`).join("");
function renderFrame() {
  const P = state.P, F = P.frame, n = P.respostas?.n_respondeu || 0, cats = F.categorias;
  // destino pode ser Outros (97) ou NS/NR (98); só a ORIGEM não pode ser fixa (a linha fixa não tem o menu)
  const opts = (excl) => optsCategorias(cats, { excluir: excl });
  const rows = cats.map((c) => {
    const k = P.contagens[c.codigo] || { primaria: 0, secundaria: 0 }, m = k.primaria + k.secundaria;
    const ro = c.fixa || F.fixo;
    return `<tr data-cod="${c.codigo}">
      <td class="num">${c.codigo}</td>
      <td>${ro ? `<b>${esc(c.nome)}</b>` : `<input class="inline f-nome" value="${esc(c.nome)}" title="Clique para renomear">`}</td>
      <td>${ro ? esc(c.definicao) : `<textarea class="inline f-def" rows="2">${esc(c.definicao)}</textarea>`}</td>
      <td>${renderKeywords(c, ro)}</td>
      <td class="ex"><small title="${esc((c.exemplos || []).join(" | "))}">${esc((c.exemplos || []).slice(0, 3).join("; "))}</small></td>
      <td class="num">${k.primaria}</td><td class="num">${k.secundaria}</td><td class="num"><b>${m}</b> <small>${pct(m, n)}</small></td>
      <td class="acoes">${ro ? "" : `<select class="f-mesclar sm" title="Mesclar esta categoria em outra"><option value="">mesclar em…</option>${opts(c.codigo)}</select> <button class="btn sm danger f-remover" title="Excluir (respostas vão para Outros)">✕</button>`}</td>
    </tr>`;
  }).join("");
  const avisos = [...(P.avisos_atributo || []).map((a) => a.msg), ...(F.avisos_ultimo_refino || [])];
  return `
    ${F.raciocinio && !F.fixo ? `<div class="info">💡 ${esc(F.raciocinio)}</div>` : ""}
    ${avisos.length ? `<div class="aviso">⚠️ Uma categoria = um atributo:<ul>${avisos.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div>` : ""}
    <table id="tab-frame"><thead><tr><th style="width:44px">Cód.</th><th style="width:16%">Categoria</th><th style="width:24%">Definição</th><th style="width:17%" title="Palavras típicas da categoria. Entram no pedido à IA como pista. Tracejadas = aprendidas com a revisão (📌 fixa, × descarta e não volta).">Palavras-chave</th><th>Exemplos</th><th class="num" style="width:60px">Prim.</th><th class="num" style="width:60px">Sec.</th><th class="num" style="width:90px">Menções</th><th style="width:200px">Ações</th></tr></thead>
    <tbody>${rows}
      ${F.fixo ? "" : `<tr class="frame-add"><td>+</td><td><input class="inline" id="f-novo-nome" placeholder="Nova categoria"></td><td><input class="inline" id="f-novo-def" placeholder="Definição (1 frase)"></td><td colspan="5"></td><td><button class="btn sm" id="f-add">Adicionar</button></td></tr>`}
    </tbody></table>
    <div class="small">Renomear/definir: edite o texto e saia do campo. Mesclar: as respostas passam para a categoria de destino (dá para mesclar em 97 Outros ou 98 NS/NR). 97 e 98 são fixas: não podem ser renomeadas nem excluídas.</div>
    ${P.codificacao ? `<div class="info">Já há respostas classificadas, então as mudanças aqui valem na hora, sem aprovar de novo. <b>Renomear</b> não muda as respostas. <b>Mesclar</b> e <b>excluir</b> movem as respostas (as excluídas vão para Outros). Uma <b>definição nova</b> vale para as próximas classificações; para refazer as que você ainda não conferiu, use <b>Reclassificar tudo</b>.</div>` : ""}
    ${F.fixo ? "" : `
    <div class="box-instr refino">
      <b>Pedir ajuste à IA</b> <span class="small">— descreva o que mudar; a IA revisa a lista mantendo o resto</span>
      <textarea id="refino" placeholder="Ex.: 'Junte Estrutura física e Conservação', 'Crie uma categoria para transporte escolar', 'A categoria Ensino está ampla demais: separe metodologia e professores'"></textarea>
      <div class="tools"><button class="btn primary" id="b-refinar">✨ Ajustar categorias com IA</button>${P.pode_desfazer_refino ? `<button class="btn" id="b-desfazer">↶ Desfazer último ajuste</button>` : ""}</div>
    </div>`}`;
}
// quadro de pergunta que pertence a um grupo: só leitura (quem edita é o grupo)
function renderFrameLeitura() {
  const P = state.P, F = P.frame;
  const lin = F.categorias.map((c) => `<tr><td class="num">${c.codigo}</td><td><b>${esc(c.nome)}</b></td><td>${esc(c.definicao)}</td>
    <td class="num">${(P.contagens[c.codigo]?.primaria || 0) + (P.contagens[c.codigo]?.secundaria || 0)}</td></tr>`).join("");
  return `<div class="info">🔗 Este quadro é do grupo <b>${esc(P.grupo.rotulo)}</b> (${esc(P.grupo.membros.join(" + "))}). Para gerar, ajustar ou pedir mudança à IA, abra <a href="#grupo/${esc(P.grupo.nome)}">a página do grupo</a>; aqui você só aprova as categorias para <b>${esc(P.qid)}</b>.</div>
    <table id="tab-frame-leitura"><thead><tr><th style="width:44px">Cód.</th><th style="width:22%">Categoria</th><th>Definição</th><th class="num" style="width:90px">Menções</th></tr></thead><tbody>${lin}</tbody></table>`;
}
// palavras-chave: fixas (definidas por alguém) e aprendidas com a revisão (tracejadas, dá para fixar ou descartar)
function renderKeywords(c, ro) {
  const chip = (k, auto) => `<span class="kw${auto ? " auto" : ""}" data-kw="${esc(k)}" title="${auto ? "Aprendida com as respostas conferidas" : "Palavra-chave fixa"}">${esc(k)}${ro ? "" :
    (auto ? `<button class="kw-fixar" title="Fixar">📌</button>` : "") + `<button class="kw-tirar" title="Remover (não volta pelo aprendizado)">×</button>`}</span>`;
  return `<div class="kws">${(c.keywords || []).map((k) => chip(k, false)).join("")}${(c.keywords_auto || []).map((k) => chip(k, true)).join("")}${ro ? "" : `<input class="inline f-kw" placeholder="+ palavra" title="Digite e tecle Enter (várias: separe por vírgula)">`}</div>`;
}
function renderSaude() {
  const A = state.P.saude || [];
  if (!A.length) return "";
  return `<div class="saude"><b>Saúde do quadro</b> <span class="small">— sinais tirados da revisão; mudar a estrutura (separar, mesclar, criar) é decisão de vocês</span>
    <ul>${A.map((a) => `<li>${esc(a.msg)}</li>`).join("")}</ul>
    ${state.P.frame?.fixo || state.P._cods ? "" : `<div class="tools"><button class="btn sm" id="b-aprender" title="Recalcula agora as palavras-chave aprendidas (isso também acontece sozinho antes de classificar, a cada 25 revisões novas)">🧠 Aprender com a revisão agora</button></div>`}
  </div>`;
}
function bindFrame() {
  const P = state.P; if (!P.frame) return;
  $("#b-aprender")?.addEventListener("click", async () => {
    const r = await post(`/api/pergunta/${P.qid}/frame/aprender`, {}, "Aprendendo com a revisão…");
    const m = r.aprendizado?.mudancas?.length || 0;
    toast(m ? `Palavras-chave aprendidas atualizadas em ${m} categoria(s)` : "Nada novo para aprender ainda"); refresh(r);
  });
  document.querySelectorAll("#tab-frame tr[data-cod]").forEach((tr) => {
    const cod = tr.dataset.cod;
    const kw = (corpo, msg) => post(`/api/pergunta/${P.qid}/frame/keywords`, { codigo: cod, ...corpo }).then((r) => { manterScroll(() => refresh(r)); if (msg) toast(msg); });
    tr.querySelector(".f-kw")?.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const novas = e.target.value.split(",").map((s) => s.trim()).filter(Boolean);
      if (novas.length) kw({ adicionar: novas }, "Palavra-chave salva");
    });
    tr.querySelectorAll(".kw-tirar").forEach((b) => b.addEventListener("click", () => kw({ remover: [b.closest(".kw").dataset.kw] })));
    tr.querySelectorAll(".kw-fixar").forEach((b) => b.addEventListener("click", () => kw({ fixar: [b.closest(".kw").dataset.kw] })));
    tr.querySelector(".f-nome")?.addEventListener("change", async (e) => { refresh(await post(`/api/pergunta/${P.qid}/frame/categoria`, { codigo: cod, nome: e.target.value })); toast("Categoria renomeada"); });
    tr.querySelector(".f-def")?.addEventListener("change", async (e) => { await post(`/api/pergunta/${P.qid}/frame/categoria`, { codigo: cod, definicao: e.target.value }); toast("Definição salva"); });
    tr.querySelector(".f-mesclar")?.addEventListener("change", async (e) => {
      const dest = e.target.value; if (!dest) return;
      e.target.value = "";
      await abrirModalFusao(P.qid, [cod], dest, async (r) => { refresh(r); });
    });
    tr.querySelector(".f-remover")?.addEventListener("click", async () => {
      if (!confirm(`Excluir a categoria "${nomeCat(cod)}"? Respostas já classificadas nela vão para Outros.`)) return;
      refresh(await api(`/api/pergunta/${P.qid}/frame/categoria/${cod}`, { method: "DELETE" }, "Excluindo…"));
    });
  });
  $("#f-add")?.addEventListener("click", async () => {
    const nome = $("#f-novo-nome").value.trim(); if (!nome) return toast("Dê um nome à categoria", true);
    refresh(await post(`/api/pergunta/${P.qid}/frame/categoria`, { nome, definicao: $("#f-novo-def").value }, "Adicionando…"));
  });
  $("#b-refinar")?.addEventListener("click", async () => {
    const fb = $("#refino").value.trim(); if (!fb) return toast("Escreva o que deve mudar nas categorias", true);
    const r = await post(`/api/pergunta/${P.qid}/frame/refinar`, { feedback: fb }, "A IA está ajustando as categorias…");
    toast("Categorias ajustadas — confira e aprove"); refresh(r);
  });
  $("#b-desfazer")?.addEventListener("click", async () => { if (!confirm("Voltar as categorias para antes do último ajuste da IA?")) return; refresh(await post(`/api/pergunta/${P.qid}/frame/desfazer`, {}, "Desfazendo…")); });
}

// ---------------------------------------------------------------- ações de classificação (amostra / restantes / aprovar)
function renderRevbar() {
  // distribuição de status das respostas (conferidas por pessoa, automáticas, corrigidas...).
  // Mostrado sempre que existe codificação, mesmo depois de aprovada — agora com barra sticky no topo (PEND-15).
  const P = state.P, V = P.revisao;
  if (!V) return "";
  const acerto = V.acerto_ia == null ? null : Math.round(100 * V.acerto_ia);
  const nCong = V.n_congeladas || 0;
  const nPendentes = V.n_codificadas - V.n_revisadas - nCong;
  const nPessoas = V.n_confirmadas - (V.n_confirmadas_auto || 0);
  return `
    <div class="passo revbar-sticky" id="revbar-passo">
      <div class="revbar">
        <div class="revbar-linha1">
          <div class="revbar-status">
            <b>Revisão:</b> <b>${fmtN(V.n_revisadas)}</b> de ${fmtN(V.n_codificadas)} conferidas (${pct(V.n_revisadas, V.n_codificadas)}) · <span class="pill ok">✓ ${fmtN(nPessoas)} manual</span>${V.n_confirmadas_auto ? ` <span class="pill ok auto" title="Confirmadas sozinhas: confiança alta e auditor concordou">⚡ ${fmtN(V.n_confirmadas_auto)} auto</span>` : ""} <span class="pill human">✎ ${fmtN(V.n_corrigidas)} corrigidas</span>
            ${acerto != null ? ` · <b>IA: ${acerto}%</b> <small>(${V.n_avaliadas_ia} avaliadas)</small>` : ""}
            ${nCong ? ` · <button type="button" class="pill cong linkbtn" id="b-so-congeladas" title="Congeladas: nem a conferir nem confirmadas, categoria travada até você descongelar. Clique para ver só elas">❄ ${fmtN(nCong)} congelada${nCong === 1 ? "" : "s"}</button>` : ""}
            ${V.n_alteradas ? ` · <button type="button" class="pill warn linkbtn" id="b-so-alteradas-revbar" title="Filtra a tabela só pelas ${V.n_alteradas} respostas que precisam de reconferência">⚠️ ${fmtN(V.n_alteradas)} a reconferir</button>` : ""}
            ${nPendentes ? ` · <button type="button" class="pill warn linkbtn" id="b-so-pendentes" title="Filtra a tabela abaixo só pelas ${nPendentes} que ainda faltam conferir">👁 ver as ${fmtN(nPendentes)} a conferir</button>` : ""}
          </div>
          <div class="revbar-acoes">
            ${renderAprovarBtn()}
          </div>
        </div>
        <div class="revbar-linha2 small">
          <span><b>Classificadas:</b> ${fmtN(V.n_codificadas)} de ${fmtN(V.n_unicas)} respostas (${pct(V.n_codificadas, V.n_unicas)})${V.n_faltantes ? ` · faltam <b>${fmtN(V.n_faltantes)}</b>` : ""}</span>
          <div class="prog pilha" title="${V.n_revisadas} conferidas · ${nPendentes} a conferir${nCong ? ` · ${nCong} congeladas` : ""} · ${V.n_faltantes} ainda não classificadas">
            <i class="conf" style="width:${V.n_unicas ? (100 * V.n_revisadas) / V.n_unicas : 0}%"></i><i class="ia" style="width:${V.n_unicas ? (100 * nPendentes) / V.n_unicas : 0}%"></i>
          </div>
        </div>
      </div>
    </div>`;
}
function renderAcoesCod() {
  const P = state.P, C = P.codificacao, V = P.revisao, R = P.respostas || {}, bs = badgeSaudeQuadro();
  // quantidade livre (com sugestões): fica FORA do botão — dentro dele, clicar no campo disparava a classificação
  const maxTam = (C ? V.n_faltantes : R.n_unicas) || "";
  const tam = `<input id="tam-amostra" class="tam-amostra" type="number" min="1" ${maxTam ? `max="${maxTam}"` : ""} step="1" value="${maxTam ? Math.min(state.amostra, maxTam) : state.amostra}"
      list="tam-sugestoes" title="Quantas respostas mandar para a IA (digite ou escolha)"><datalist id="tam-sugestoes">${[30, 50, 100, 200, 500].map((n) => `<option value="${n}">`).join("")}</datalist>`;
  if (!C) return `
    <div class="passo">
      <div><b>Comece por uma amostra.</b> A IA classifica ${tam} respostas; você confere, corrige e ajusta as instruções/categorias. Quando a taxa de acerto estiver boa, classifique o restante.</div>
      <div class="tools"><button class="btn primary" id="b-amostra">✨ Classificar amostra</button><button class="btn" id="b-codificar">Classificar todas as ${R.n_unicas || ""} de uma vez</button></div>
    </div>`;
  return `
    <div class="passo">
      <div class="small">Loop: confirme ✓ o que está certo · corrija na hora pelo menu · ou escreva um comentário e clique em <b>Reclassificar comentadas</b>. Se o erro se repete, ajuste as <b>instruções</b> ou as <b>categorias</b> e clique em <b>Reclassificar tudo</b> (o que você corrigiu/confirmou é mantido).</div>
      <div class="tools">
        <button class="btn primary" id="b-recod-com" ${P.n_comentarios_pendentes ? "" : "disabled"}>✨ Reclassificar comentadas (${P.n_comentarios_pendentes})</button>
        <button class="btn" id="b-recod-tudo" title="Refaz com a IA tudo que você ainda não conferiu">↻ Reclassificar tudo</button>
        ${V.n_faltantes ? `<span class="sep"></span><span class="tam-grupo"><button class="btn" id="b-mais">+ Classificar mais</button>${tam}<span class="small">respostas</span></span><button class="btn primary" id="b-restantes">Classificar as restantes (${V.n_faltantes})</button>` : ""}
      </div>
      <div class="tools supervisao">
        <b>Supervisão:</b>
        <button class="btn" id="b-auditar" title="Outra IA confere a classificação, resposta por resposta (segundo codificador)">🔎 Auditar com outra IA</button>
        <button class="btn" id="b-auto" title="Confirma sozinho o que tem confiança alta E o auditor concordou">⚡ Aceitar alta confiança</button>
        <label class="small">limiar <input id="auto-limiar" type="number" min="0.5" max="1" step="0.05" value="${state.limiar ?? 0.85}" style="width:64px"></label>
        ${V.n_confirmadas_auto ? `<button class="btn ghost" id="b-desfazer-auto">↶ Desfazer as ${V.n_confirmadas_auto} automáticas</button>` : ""}
        <span class="sep"></span>
        ${V.n_alteradas ? `<button class="btn warn" id="b-so-alteradas" title="Filtrar as ${V.n_alteradas} respostas que precisam de reconferência após alteração no quadro">⚠️ Reconferir alteradas (${V.n_alteradas})</button>` : ""}
        <button class="btn" id="b-janela" title="Cada categoria com exemplos, perfil de quem citou e confirmação em bloco">🗂 Revisar por categoria</button>
        <button class="btn ${bs.classe}" id="b-saude-quadro-rev" title="Saúde do quadro: diagnóstico por categoria e soluções propostas">🩺 Saúde do quadro${bs.texto}</button>
        <button class="btn ghost" id="b-versoes" title="Versões guardadas desta pergunta (volta a um ponto anterior se algo deu errado)">🕘 Versões</button>
      </div>
    </div>`;
}
function bindAcoesCod() {
  const P = state.P;
  // lê o campo na hora do clique (a pessoa pode digitar e clicar direto, sem sair do campo)
  const lerTam = () => {
    const campo = $("#tam-amostra"), max = +campo.max || Infinity, n = Math.floor(+campo.value);
    if (!(n >= 1)) { toast("Digite quantas respostas mandar para a IA (1 ou mais).", true); campo.focus(); return null; }
    state.amostra = Math.min(n, max); campo.value = state.amostra;
    return state.amostra;
  };
  $("#tam-amostra")?.addEventListener("change", (e) => { if (+e.target.value >= 1) lerTam(); });
  $("#tam-amostra")?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ($("#b-mais") || $("#b-amostra"))?.click(); } });
  const classificar = async (body, msg) => refresh(await post(`/api/pergunta/${P.qid}/codificar`, body, msg, true));
  $("#b-amostra")?.addEventListener("click", () => {
    const n = lerTam(); if (!n || !confirmarVolume(n, "Classificar amostra")) return;
    classificar({ limite: n }, `A IA está classificando uma amostra de ${n}…`);
  });
  $("#b-codificar")?.addEventListener("click", () => {
    const n = P.respostas?.n_unicas;
    if (n > AVISO_VOLUME ? !confirmarVolume(n, "Classificar todas de uma vez") : !confirm(`Classificar todas as ${n} respostas agora? (Recomendado: testar numa amostra antes.)`)) return;
    classificar({}, "A IA está classificando as respostas…");
  });
  $("#b-mais")?.addEventListener("click", () => {
    const n = lerTam(); if (!n || !confirmarVolume(n, "Classificar mais")) return;
    classificar({ limite: n, restantes: true }, `A IA está classificando mais ${n} respostas…`);
  });
  $("#b-restantes")?.addEventListener("click", () => {
    if (!confirmarVolume(P.revisao?.n_faltantes, "Classificar as restantes")) return;
    classificar({ restantes: true }, "A IA está classificando as respostas restantes…");
  });
  $("#b-recod-com")?.addEventListener("click", async () => { const r = await post(`/api/pergunta/${P.qid}/recodificar`, { apenas_comentados: true }, "Reclassificando as respostas comentadas…", true); toast(`${r.recodificados} resposta(s) reclassificada(s)`); refresh(r); });
  $("#b-recod-tudo")?.addEventListener("click", async () => {
    const V = P.revisao, n = V ? V.n_codificadas - V.n_revisadas - (V.n_congeladas || 0) : 0;
    const msg = `Reclassificar com a IA as ${fmtN(n)} já classificadas que você ainda não conferiu? O que você corrigiu ou confirmou é mantido; as que ainda não foram classificadas não entram (para elas, use "Classificar as restantes").`;
    if (n > AVISO_VOLUME ? !confirmarVolume(n, "Reclassificar tudo") : !confirm(msg)) return;
    refresh(await post(`/api/pergunta/${P.qid}/recodificar`, { apenas_comentados: false }, "Reclassificando…", true));
  });
  $("#auto-limiar")?.addEventListener("change", (e) => (state.limiar = Math.min(1, Math.max(0.5, +e.target.value || 0.85))));
  $("#b-auto")?.addEventListener("click", async () => {
    const limiar = state.limiar ?? 0.85;
    if (!confirm(`Confirmar sozinho as respostas com confiança ≥ ${limiar.toFixed(2)} em que o auditor (outra IA) concordou?\n\nO que você já conferiu não muda. Dá para desfazer depois.`)) return;
    const r = await post(`/api/pergunta/${P.qid}/auto-aceitar`, { limiar }, "Aceitando as de alta confiança…");
    refresh(r); mostrarResultadoAuto(r.auto);
  });
  $("#b-desfazer-auto")?.addEventListener("click", async () => {
    if (!confirm("Desfazer todas as confirmações automáticas desta pergunta? (A auditoria continua guardada.)")) return;
    const r = await post(`/api/pergunta/${P.qid}/desfazer-auto`, {}, "Desfazendo…"); toast(`${r.alterados} confirmação(ões) automática(s) desfeita(s)`); refresh(r);
  });
  $("#b-auditar")?.addEventListener("click", abrirAuditoria);
  $("#b-janela")?.addEventListener("click", () => abrirJanelaCategorias());
  $("#b-saude-quadro-rev")?.addEventListener("click", () => abrirJanelaSaudeQuadro());
  $("#b-versoes")?.addEventListener("click", () => abrirJanelaVersoes());
  $("#b-so-congeladas")?.addEventListener("click", () => { state.filtro.situacao = "congelada"; state.mostrar = POR_PAGINA; state.congelar = false; manterScroll(render); });
  const filtrarParaAlteradas = () => {
    state.filtro.situacao = "alterada"; state.mostrar = POR_PAGINA; state.congelar = false;
    manterScroll(render);
    $("#tab-cod")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  $("#b-so-alteradas")?.addEventListener("click", filtrarParaAlteradas);
  $("#b-so-alteradas-revbar")?.addEventListener("click", filtrarParaAlteradas);
  $("#b-so-pendentes")?.addEventListener("click", () => {
    state.filtro.situacao = "pendente"; state.mostrar = POR_PAGINA; state.congelar = false;
    manterScroll(render);
    $("#tab-cod")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}
function mostrarResultadoAuto(a) {
  if (!a) return;
  const ficaram = Object.entries(a.ficaram || {}).map(([m, n]) => `<li>${esc(m)}: <b>${fmtN(n)}</b></li>`).join("");
  abrirJanela("Aceite automático", `<p><b>${fmtN(a.aceitas)} resposta(s) confirmadas sozinhas</b> (confiança ≥ ${Number(a.limiar).toFixed(2)}${a.exigir_auditoria ? " e auditor concordando" : ""}).</p>
    ${ficaram ? `<p>Ficaram para você conferir:</p><ul>${ficaram}</ul>` : "<p>Nenhuma ficou de fora.</p>"}
    ${a.ficaram && a.ficaram["ainda sem auditoria"] ? `<p class="small">As "sem auditoria" precisam passar antes por <b>🔎 Auditar com outra IA</b>.</p>` : ""}`);
}

// ---- janela de revisão por categoria: definição, exemplos, perfil de quem citou e confirmação em bloco
const fmt1 = (v, casas = 1) => (v == null ? "–" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }));
function linhaPerfil(rotulo, v, vb, casas, suf = "", titulo = "") {
  if (v == null) return "";
  const d = vb == null ? null : v - vb;
  const seta = d == null || Math.abs(d) < (casas ? 0.05 : 0.5) ? "" : d > 0 ? "▲" : "▼";
  return `<tr title="${esc(titulo)}"><td>${rotulo}</td><td class="num"><b>${fmt1(v, casas)}${suf}</b></td><td class="num small">${fmt1(vb, casas)}${suf}</td><td class="num small">${seta ? `${seta} ${fmt1(Math.abs(d), casas)}` : "≈"}</td></tr>`;
}
function cardCategoria(c, D, podeEditar, catsOpc) {
  const b = D.base || {}, p = c.perfil || {}, cfg = D.config || {};
  const perfil = D.classificada && c.n ? `
    <table class="perfil"><thead><tr><th></th><th class="num">quem citou</th><th class="num small">todos (base)</th><th class="num small">diferença</th></tr></thead><tbody>
      ${p.nps ? linhaPerfil("NPS", p.nps.nps, b.nps?.nps, 0, "", cfg.nps || "") + linhaPerfil("nota média (0–10)", p.nps.media, b.nps?.media, 1) + linhaPerfil("% detratores (0–6)", p.nps.detratores, b.nps?.detratores, 0, "%") : ""}
      ${linhaPerfil("satisfação geral (1–5)", p.satisfacao, b.satisfacao, 2, "", cfg.satisfacao || "")}
      ${cfg.retencao ? linhaPerfil(`% ${esc(cfg.retencao.toLowerCase())}`, p.retencao_risco, b.retencao_risco, 0, "%") : ""}
    </tbody></table>
    ${c.n < 10 ? `<div class="small warn-t">Base pequena (n=${c.n}): leia o perfil com cuidado.</div>` : ""}
    ${(c.atributos_piores || []).length ? `<div class="small"><b>Avaliam pior que a base:</b> ${c.atributos_piores.map((a) => `${esc(a.rotulo)} <b>${fmt1(a.media, 2)}</b> vs ${fmt1(a.media_base, 2)}`).join(" · ")}</div>` : ""}
    ${(c.grupos_acima || []).length ? `<div class="small"><b>${esc(cfg.grupo || "Grupo")} acima do esperado:</b> ${c.grupos_acima.map((g) => `${esc(g.nome)} (${g.n}; ${fmt1(g.pct)}% vs ${fmt1(g.pct_base)}%)`).join(" · ")}</div>` : ""}` : "";
  const exemplos = (c.exemplos || []).map((e) => {
    const t = typeof e === "string" ? e : e.texto, curto = t.length > 140 ? t.slice(0, 140) + "…" : t;
    return `<li title="${esc(t)}">${esc(curto)}${e.n > 1 ? ` <small>×${e.n}</small>` : ""}</li>`;
  }).join("");
  const isOutros = (c.codigo === 97 || String(c.codigo) === "97" || (c.nome || "").toLowerCase().includes("outros"));
  const satOutros = isOutros && D.classificada && (c.pct || 0) > 5.0 ? `<span class="pill warn" style="font-weight:600" title="Metodologia: 'Outros' acima de 5% da base requer avaliação e desmembramento">⚠️ Saturação: ${fmt1(c.pct)}% (>5%)</span>` : "";
  const pend = (c.pendentes || []).length;
  return `<div class="card-cat" data-cod="${c.codigo}">
    <div class="cc-cab"><span class="cc-cod">${c.codigo}</span>
      ${podeEditar && !c.fixa ? `<input class="inline cc-nome" value="${esc(c.nome)}">` : `<b>${esc(c.nome)}</b>`}
      ${satOutros}
      ${D.classificada ? `<span class="cc-n"><b>${fmtN(c.n || 0)}</b> <small>${c.pct != null ? fmt1(c.pct) + "%" : ""}</small></span>` : ""}</div>
    ${podeEditar && !c.fixa ? `<textarea class="inline cc-def" rows="2">${esc(c.definicao)}</textarea>` : `<div class="small">${esc(c.definicao)}</div>`}
    ${(c.keywords || []).length + (c.keywords_auto || []).length ? renderKeywords(c, true) : ""}
    ${exemplos ? `<ul class="cc-ex">${exemplos}</ul>` : ""}
    ${perfil}
    <div class="cc-acoes">
      ${D.classificada && pend ? `<button class="btn sm ok cc-conf" title="${esc((c.menor_confianca || []).map((m) => `${fmt1(m.confianca, 2)} · ${m.texto}`).join("\n"))}">✓ Confirmar ${pend} pendente${pend > 1 ? "s" : ""}</button>
      <button class="btn sm cc-conf-alta" type="button" title="Aceita pendentes desta categoria com confiança ≥ 0,80 em que o auditor concordou">⚡ Alta conf. (≥ 0,80)</button>` : D.classificada ? `<span class="small">nada a conferir</span>` : ""}
      ${c.com_sugestao ? `<span class="small" title="O auditor discordou: confira uma a uma (filtro 'auditor discordou')">🔎 ${c.com_sugestao} com sugestão do auditor ficam fora</span>` : ""}
      ${podeEditar && !c.fixa ? `<select class="sm cc-mesclar"><option value="">mesclar em…</option>${catsOpc(c.codigo)}</select>` : ""}
    </div>
    ${D.classificada && pend && (c.menor_confianca || []).length ? `<div class="small cc-menor">Menor confiança: ${c.menor_confianca.map((m) => `“${esc(m.texto.slice(0, 80))}${m.texto.length > 80 ? "…" : ""}” (${fmt1(m.confianca, 2)})`).join(" · ")}</div>` : ""}
  </div>`;
}
// ---- modal de fusão assistido por IA
async function abrirModalFusao(qid, origens, dest, onConcluido) {
  const dlg = $("#dlg-fusao");
  if (!dlg) return;
  const corpo = $("#fusao-corpo");
  const titulo = $("#fusao-titulo");

  const nomeCatLocal = (k) => {
    const P = state.P;
    const cat = P?.frame?.categorias?.find((c) => String(c.codigo) === String(k));
    return cat ? cat.nome : `Cat. ${k}`;
  };

  const origensArray = Array.isArray(origens) ? origens : [origens];
  const nomesOrig = origensArray.map(nomeCatLocal).join(", ");
  const nomeDest = nomeCatLocal(dest);

  titulo.textContent = `Mesclar categorias`;
  corpo.innerHTML = `
    <div class="fusao-meta-box">
      <b>Origem:</b> ${esc(nomesOrig)} <span class="seta">➔</span> <b>Destino:</b> ${esc(nomeDest)}
    </div>
    <div class="fusao-loading">
      <span class="spinner"></span> A IA está sugerindo a combinação de nome, definição e palavras-chave…
    </div>
  `;
  if (!dlg.open) dlg.showModal();

  $("#fusao-fechar").onclick = () => dlg.close();

  let prop;
  try {
    prop = await post(`/api/pergunta/${qid}/frame/sugerir-fusao`, { destino: dest, origens: origensArray });
  } catch (err) {
    toast(`Não foi possível obter sugestão da IA: ${err.message}`, true);
    prop = {
      nome_sugerido: `${nomeDest} e ${nomesOrig}`,
      definicao_sugerida: "",
      keywords_sugeridas: []
    };
  }

  const kwsStr = (prop.keywords_sugeridas || []).join(", ");

  corpo.innerHTML = `
    <div class="fusao-meta-box">
      <b>Origem:</b> ${esc(nomesOrig)} <span class="seta">➔</span> <b>Destino:</b> ${esc(nomeDest)}<br>
      <small style="color:var(--text-3)">Respostas afetadas das categorias envolvidas ficarão com status <b>alterada</b> para reconferência.</small>
    </div>

    <label class="campo">
      Nome da categoria unificada
      <input id="fusao-input-nome" type="text" placeholder="${esc(prop.nome_sugerido || '')}">
      <small class="help">Deixe em branco para aceitar a sugestão da IA: <b>${esc(prop.nome_sugerido || '')}</b></small>
    </label>

    <label class="campo">
      Definição
      <textarea id="fusao-input-def" rows="3">${esc(prop.definicao_sugerida || '')}</textarea>
      <small class="help">Delimite o escopo combinado das categorias unificadas.</small>
    </label>

    <label class="campo">
      Palavras-chave (separadas por vírgula)
      <input id="fusao-input-kws" type="text" value="${esc(kwsStr)}">
      <small class="help">Termos típicos para reconhecimento automático e sugestão.</small>
    </label>

    <div class="dlg-acoes">
      <button type="button" class="btn" id="fusao-btn-cancelar">Cancelar</button>
      <button type="button" class="btn primary" id="fusao-btn-confirmar">Confirmar mesclagem</button>
    </div>
  `;

  $("#fusao-btn-cancelar").onclick = () => dlg.close();

  const inputNome = $("#fusao-input-nome");
  const inputDef = $("#fusao-input-def");
  const inputKws = $("#fusao-input-kws");
  const btnConf = $("#fusao-btn-confirmar");

  btnConf.onclick = async () => {
    btnConf.disabled = true;
    btnConf.textContent = "Mesclando…";

    // Regra: se o usuário não mexer no input (deixar em branco), usa o placeholder sugerido pela IA
    const nomeFinal = (inputNome.value.trim()) || prop.nome_sugerido || nomeDest;
    const defFinal = inputDef.value.trim();
    const kwsFinal = inputKws.value.split(",").map((s) => s.trim()).filter(Boolean);

    try {
      const payload = {
        destino: dest,
        origens: origensArray,
        novo_nome: nomeFinal,
        nova_definicao: defFinal,
        novas_keywords: kwsFinal,
      };
      const r = await post(`/api/pergunta/${qid}/frame/fundir`, payload, "Mesclando categorias…");
      dlg.close();
      toast(`Categorias mescladas em "${nomeFinal}"`);
      if (onConcluido) await onConcluido(r);
    } catch (err) {
      toast(`Erro ao mesclar: ${err.message}`, true);
      btnConf.disabled = false;
      btnConf.textContent = "Confirmar mesclagem";
    }
  };
}

async function abrirJanelaCategorias() {
  const P = state.P, qid = P.qid;
  const D = await api(`/api/pergunta/${qid}/perfil`, {}, "Montando o perfil das categorias…");
  const F = P.frame, frameOk = F && F.status === "aprovado", locked = P.codificacao?.status === "aprovado";
  const podeEditar = !F?.fixo && !locked;
  const catsOpc = (excl) => optsCategorias(catsValidas(), { excluir: excl });
  const b = D.base || {};
  const cats = D.classificada ? [...D.categorias].sort((x, y) => (y.n || 0) - (x.n || 0)) : D.categorias;
  const catOutros = D.classificada ? cats.find((c) => (c.codigo === 97 || String(c.codigo) === "97" || (c.nome || "").toLowerCase().includes("outros")) && (c.pct || 0) > 5.0) : null;
  const alertaOutros = catOutros ? `
    <div class="box-instr" style="background:var(--warn-bg);border:1px solid var(--warn);margin-bottom:12px">
      ⚠️ <b>Atenção Metodológica:</b> A categoria "<b>${esc(catOutros.nome)}</b>" (código ${catOutros.codigo}) concentra <b>${fmt1(catOutros.pct)}%</b> das menções (${catOutros.n} respostas). O padrão analítico recomenda desmembrar categorias residuais que superam 5% da base. Avalie os exemplos abaixo para criar novas categorias antes de aprovar.
    </div>` : "";
  abrirJanela(`Categorias · ${qid}`, `
    ${alertaOutros}
    ${D.classificada ? `<div class="small cc-base">Perfil comparado com <b>todos que responderam ${esc(qid)}</b> (n=${fmtN(b.n)}${b.nps ? `; NPS ${fmt1(b.nps.nps, 0)}` : ""}${b.satisfacao != null ? `; satisfação ${fmt1(b.satisfacao, 2)}` : ""}) — não com o total da pesquisa. ▲▼ = acima/abaixo da base.</div>`
      : `<div class="info">Ainda não há respostas classificadas: aqui aparecem a definição e os exemplos que a IA propôs. Depois de classificar uma amostra, esta janela mostra também o <b>perfil de quem citou</b> cada categoria.</div>`}
    <div class="cards-cat">${cats.map((c) => cardCategoria(c, D, podeEditar, catsOpc)).join("")}</div>
    ${F && !frameOk ? `<div class="dlg-acoes"><button class="btn ok" type="button" id="jc-aprovar">✓ Aprovar categorias</button></div>` : ""}`);
  const depois = async (payload, msg) => {
    const scrollSalvo = $("#jan-corpo")?.scrollTop || 0;
    if (payload) refresh(payload);
    if (msg) toast(msg);
    await abrirJanelaCategorias();
    const novoCorpo = $("#jan-corpo");
    if (novoCorpo && scrollSalvo) novoCorpo.scrollTop = scrollSalvo;
  };
  document.querySelectorAll(".card-cat").forEach((card) => {
    const cod = card.dataset.cod, c = D.categorias.find((x) => String(x.codigo) === cod);
    card.querySelector(".cc-nome")?.addEventListener("change", async (e) => depois(await post(`/api/pergunta/${qid}/frame/categoria`, { codigo: cod, nome: e.target.value }), "Categoria renomeada"));
    card.querySelector(".cc-def")?.addEventListener("change", async (e) => { await post(`/api/pergunta/${qid}/frame/categoria`, { codigo: cod, definicao: e.target.value }); toast("Definição salva"); });
    card.querySelector(".cc-mesclar")?.addEventListener("change", async (e) => {
      const dest = e.target.value; if (!dest) return;
      e.target.value = "";
      await abrirModalFusao(qid, [cod], dest, async (r) => { await depois(r, "Categorias mescladas"); });
    });
    card.querySelector(".cc-conf")?.addEventListener("click", async () => {
      const menor = (c.menor_confianca || []).map((m) => `• ${m.texto.slice(0, 90)} (${fmt1(m.confianca, 2)})`).join("\n");
      if (!confirm(`Confirmar as ${c.pendentes.length} respostas a conferir de "${c.nome}"? Contam como conferidas por você.${menor ? `\n\nAs de menor confiança:\n${menor}` : ""}`)) return;
      const r = await post(`/api/pergunta/${qid}/validar`, { rids: c.pendentes, valor: true }, "Confirmando…");
      await depois(r, `${r.alterados} resposta(s) confirmada(s) em ${c.nome}`);
    });
    card.querySelector(".cc-conf-alta")?.addEventListener("click", async () => {
      const r = await post(`/api/pergunta/${qid}/auto-aceitar`, { limiar: 0.80, exigir_auditoria: true, categoria: +cod }, "Aceitando alta confiança…");
      const aceitas = r.auto?.aceitas || 0;
      await depois(r, `${aceitas} resposta(s) de alta confiança confirmada(s) em ${c.nome}`);
    });
  });
  $("#jc-aprovar")?.addEventListener("click", async () => { const r = await post(`/api/pergunta/${qid}/frame/aprovar`, {}, "Aprovando…"); $("#dlg-janela").close(); refresh(r); toast("Categorias aprovadas"); });
}

async function abrirJanelaSaudeQuadro() {
  const P = state.P, qid = P.qid;
  const res = await api(`/api/pergunta/${qid}/aprendizado`, {}, "Carregando diagnóstico de saúde do quadro…");
  const diag = res.diagnostico || {};
  const resumo = diag.resumo || {};
  const atencao = diag.categorias_atencao || [];
  const raras = diag.categorias_raras || [];
  const saudaveis = diag.categorias_saudaveis || [];
  const catsFrame = P.frame?.categorias || [];
  const opts = (excl) => optsCategorias(catsFrame, { excluir: excl });

  const placarHtml = `
    <div class="sq-placar">
      <div class="sq-stat"><span class="sq-val">${resumo.total_categorias || 0}</span><span class="sq-lbl">Categorias no quadro</span></div>
      <div class="sq-stat" style="border-color:color-mix(in srgb,var(--warn) 50%,var(--border))"><span class="sq-val" style="color:var(--warn)">${atencao.length}</span><span class="sq-lbl">Com pontos de atenção</span></div>
      <div class="sq-stat"><span class="sq-val">${raras.length}</span><span class="sq-lbl">Baixo volume (&lt; 1%)</span></div>
      <div class="sq-stat" style="border-color:color-mix(in srgb,var(--ok) 50%,var(--border))"><span class="sq-val" style="color:var(--ok)">${saudaveis.length}</span><span class="sq-lbl">Saudáveis</span></div>
    </div>
    <div class="sq-barra-topo">
      <div>
        <b>🧠 Aprendizado contínuo:</b> 
        <span class="small">${resumo.n_conferidas || 0} respostas conferidas por pessoas</span>
        ${resumo.revisoes_para_proximo_aprendizado ? `<span class="small">(faltam ${resumo.revisoes_para_proximo_aprendizado} revisões para a próxima rodada automática)</span>` : `<span class="small pill ok">pronto para aprender</span>`}
      </div>
      <button class="btn sm" id="sq-aprender">🧠 Aprender com a revisão agora</button>
    </div>
  `;

  let atencaoHtml = "";
  if (atencao.length) {
    atencaoHtml = `
      <h3 style="margin:16px 0 8px">⚠️ Categorias que precisam de ajuste (${atencao.length}) <span class="small">— confusões de fronteira, amplitude ou sobreposição de palavras</span></h3>
      <div class="sq-cards">
        ${atencao.map((c) => {
          return `
            <div class="sq-card" data-cod="${c.codigo}">
              <div class="sq-card-cab">
                <b>${c.codigo} · ${esc(c.nome)}</b>
                <span class="pill ${c.problemas.length > 1 ? "warn" : ""}">${c.problemas.length} alerta(s)</span>
                <span class="small">${c.n} respostas (${pct(c.n, resumo.total_respostas || 1)})</span>
                ${c.conf_media != null ? `<span class="small">Confiança média: <b>${fmt1(c.conf_media, 2)}</b></span>` : ""}
              </div>
              <div class="sq-card-corpo">
                <div class="sq-def-atual"><b>Definição atual:</b> <i>"${esc(c.definicao || "(sem definição cadastrada)")}"</i></div>
                <div class="sq-problemas">
                  ${c.problemas.map((p) => `
                    <div class="sq-prob-item">
                      <b>${esc(p.titulo)}</b>
                      <div>${esc(p.detalhe)}</div>
                    </div>
                  `).join("")}
                </div>
                <div class="sq-solucoes">
                  <div class="sq-sol-titulo">💡 Soluções Propostas — Aprove para aplicar na hora:</div>
                  <div class="sq-sol-linha">
                    ${c.solucoes.map((s) => {
                      if (s.tipo === "propor_definicao_ia") {
                        return `<button class="btn sm sq-btn-propor-ia" data-cod="${c.codigo}">${esc(s.rotulo)}</button>`;
                      }
                      if (s.tipo === "adicionar_exclusao") {
                        return `<button class="btn sm sq-btn-exclusao" data-cod="${c.codigo}" data-texto="${esc(s.texto_adicional)}">${esc(s.rotulo)}</button>`;
                      }
                      if (s.tipo === "remover_keyword") {
                        return `<button class="btn sm danger sq-btn-rem-kw" data-cod="${c.codigo}" data-kw="${esc(s.keyword)}">${esc(s.rotulo)}</button>`;
                      }
                      if (s.tipo === "adicionar_keywords") {
                        return `<button class="btn sm ok sq-btn-add-kws" data-cod="${c.codigo}" data-kws="${esc(s.keywords.join(','))}">✓ Adicionar palavras sugeridas</button>`;
                      }
                      if (s.tipo === "separar") {
                        return `<button class="btn sm sq-btn-separar" data-cod="${c.codigo}" data-nome="${esc(c.nome)}">${esc(s.rotulo)}</button>`;
                      }
                      if (s.tipo === "desmembrar_outros") {
                        return `<button class="btn sm sq-btn-outros">${esc(s.rotulo)}</button>`;
                      }
                      return "";
                    }).join("")}
                  </div>
                  <div class="sq-previa-def hidden" id="sq-previa-${c.codigo}"></div>
                </div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  } else {
    atencaoHtml = `<div class="info ok" style="margin:12px 0">✓ Nenhuma categoria com confusão de fronteira ou amplitude excessiva! O quadro está consistente.</div>`;
  }

  let rarasHtml = "";
  if (raras.length) {
    rarasHtml = `
      <h3 style="margin:20px 0 8px">📉 Categorias de Baixo Volume (${raras.length}) <span class="small">— menos de 1% das respostas; avalie mesclar ou excluir</span></h3>
      <table class="tab-raras">
        <thead>
          <tr>
            <th style="width:40px">Cód.</th>
            <th>Categoria</th>
            <th style="width:120px">Respostas</th>
            <th>Solução Proposta</th>
          </tr>
        </thead>
        <tbody>
          ${raras.map((r) => `
            <tr data-cod="${r.codigo}">
              <td><b>${r.codigo}</b></td>
              <td><b>${esc(r.nome)}</b></td>
              <td>${r.n} (${pct(r.n, resumo.total_respostas || 1)})</td>
              <td>
                <select class="sq-raras-mesclar sm" data-cod="${r.codigo}">
                  <option value="">mesclar em…</option>
                  ${opts(r.codigo)}
                </select>
                <button class="btn sm sq-btn-mesclar" data-cod="${r.codigo}">✓ Aprovar mesclagem</button>
                ${r.pode_excluir ? `<button class="btn sm danger sq-btn-excluir" data-cod="${r.codigo}">🗑️ Excluir</button>` : ""}
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  let saudaveisHtml = "";
  if (saudaveis.length) {
    saudaveisHtml = `
      <details class="sq-saudaveis">
        <summary>✓ <b>${saudaveis.length} categorias saudáveis</b> (sem alertas de sobreposição ou amplitude)</summary>
        <div class="sq-saudaveis-lista">
          ${saudaveis.map((s) => `<span class="pill ok">${s.codigo} · ${esc(s.nome)} (${s.n})</span>`).join("")}
        </div>
      </details>
    `;
  }

  abrirJanela(`Saúde do quadro · ${qid}`, `
    ${placarHtml}
    ${atencaoHtml}
    ${rarasHtml}
    ${saudaveisHtml}
  `);

  $("#sq-aprender")?.addEventListener("click", async () => {
    const r = await post(`/api/pergunta/${qid}/frame/aprender`, {}, "Aprendendo com a revisão…");
    const m = r.aprendizado?.mudancas?.length || 0;
    toast(m ? `Palavras-chave aprendidas atualizadas em ${m} categoria(s)` : (r.aprendizado?.motivo || "Nada novo para aprender ainda"));
    refresh(r);
    await abrirJanelaSaudeQuadro();
  });

  document.querySelectorAll(".sq-btn-propor-ia").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod;
      const previaEl = $(`#sq-previa-${cod}`);
      if (!previaEl) return;
      btn.disabled = true;
      btn.textContent = "⏳ Gerando proposta com IA…";
      try {
        const prop = await post(`/api/pergunta/${qid}/frame/propor-definicao`, { codigo: cod }, "A IA está formulando a definição…");
        previaEl.innerHTML = `
          <div class="sq-diff-box">
            <div><small style="color:var(--text-3)">DEFINIÇÃO ATUAL:</small><br><i>"${esc(prop.definicao_atual || '(vazia)')}"</i></div>
            <div class="sq-destaque-def"><small style="color:var(--ok);font-weight:700">DEFINIÇÃO PROPOSTA PELA IA:</small><br><b>${esc(prop.definicao_proposta)}</b></div>
            ${prop.justificativa ? `<div class="small">💡 <b>Por que esta redação:</b> ${esc(prop.justificativa)}</div>` : ""}
            <div class="sq-sol-linha" style="margin-top:6px">
              <button class="btn sm ok sq-btn-aprovar-def" data-cod="${cod}" data-def="${esc(prop.definicao_proposta)}">✓ Aprovar esta definição</button>
              <button class="btn sm ghost sq-btn-canc-def" data-cod="${cod}">Cancelar</button>
            </div>
          </div>
        `;
        previaEl.classList.remove("hidden");
        previaEl.querySelector(".sq-btn-canc-def")?.addEventListener("click", () => {
          previaEl.innerHTML = "";
          previaEl.classList.add("hidden");
        });
        previaEl.querySelector(".sq-btn-aprovar-def")?.addEventListener("click", async (e) => {
          const novaDef = e.target.dataset.def;
          const r = await post(`/api/pergunta/${qid}/frame/categoria`, { codigo: cod, definicao: novaDef }, "Salvando nova definição…");
          toast("Nova definição aprovada e salva no quadro!");
          refresh(r);
          await abrirJanelaSaudeQuadro();
        });
      } catch (err) {
        toast("Erro ao gerar proposta: " + (err.message || err), true);
      } finally {
        btn.disabled = false;
        btn.textContent = "✨ Propor nova definição com IA";
      }
    });
  });

  document.querySelectorAll(".sq-btn-exclusao").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod, texto = btn.dataset.texto;
      const cat = P.frame?.categorias?.find((c) => String(c.codigo) === String(cod));
      const defAtual = cat?.definicao || "";
      const novaDef = defAtual ? `${defAtual.replace(/\.*$/, "")}.${texto}` : texto.trim();
      const r = await post(`/api/pergunta/${qid}/frame/categoria`, { codigo: cod, definicao: novaDef }, "Adicionando ressalva…");
      toast("Ressalva adicionada à definição!");
      refresh(r);
      await abrirJanelaSaudeQuadro();
    });
  });

  document.querySelectorAll(".sq-btn-rem-kw").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod, kw = btn.dataset.kw;
      const r = await post(`/api/pergunta/${qid}/frame/keywords`, { codigo: cod, remover: [kw] }, "Removendo palavra ambígua…");
      toast(`Palavra-chave "${kw}" removida da categoria!`);
      refresh(r);
      await abrirJanelaSaudeQuadro();
    });
  });

  document.querySelectorAll(".sq-btn-add-kws").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod, kws = (btn.dataset.kws || "").split(",").filter(Boolean);
      const r = await post(`/api/pergunta/${qid}/frame/keywords`, { codigo: cod, adicionar: kws }, "Adicionando termos…");
      toast("Palavras-chave sugeridas adicionadas!");
      refresh(r);
      await abrirJanelaSaudeQuadro();
    });
  });

  document.querySelectorAll(".sq-btn-separar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const nome = btn.dataset.nome;
      $("#dlg-janela")?.close();
      const refino = $("#refino");
      if (refino) {
        refino.value = `A categoria "${nome}" está ampla demais: separe em subcategorias mais específicas preservando a precisão analítica.`;
        refino.scrollIntoView({ behavior: "smooth", block: "center" });
        refino.focus();
      }
    });
  });

  document.querySelectorAll(".sq-btn-outros").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("#dlg-janela")?.close();
      const refino = $("#refino");
      if (refino) {
        refino.value = "Identifique os temas mais recorrentes em Outros e proponha novas categorias para capturar essas respostas.";
        refino.scrollIntoView({ behavior: "smooth", block: "center" });
        refino.focus();
      }
    });
  });

  document.querySelectorAll(".sq-btn-mesclar").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod;
      const row = btn.closest("tr");
      const sel = row?.querySelector(".sq-raras-mesclar");
      const dest = sel?.value;
      if (!dest) return toast("Selecione a categoria de destino para mesclar", true);
      await abrirModalFusao(qid, [cod], dest, async (r) => {
        refresh(r);
        await abrirJanelaSaudeQuadro();
      });
    });
  });

  document.querySelectorAll(".sq-btn-excluir").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.cod;
      const c = P.frame?.categorias?.find((x) => String(x.codigo) === String(cod));
      if (!confirm(`Excluir a categoria vazia "${c?.nome}"?`)) return;
      const r = await api(`/api/pergunta/${qid}/frame/categoria/${cod}`, { method: "DELETE" }, "Excluindo…");
      toast("Categoria excluída!");
      refresh(r);
      await abrirJanelaSaudeQuadro();
    });
  });
}

// ---- auditoria por outra IA (segundo codificador)
function abrirAuditoria() {
  const P = state.P, ia = state.status.ia, provs = ia.provedores || {};
  // só provedores prontos: programa instalado (CLI), chave guardada, ou o simulador no modo teste
  const pronto = (k, p) => (p.cli ? p.disponivel : p.sem_chave ? ia.modo_teste : p.tem_chave);
  const opcoes = Object.entries(provs).filter(([k, p]) => pronto(k, p))
    .map(([k, p]) => `<option value="${k}">${esc(p.nome)}${k === ia.provedor ? " (o mesmo que classificou)" : ""}</option>`).join("");
  const dlg = abrirJanela("🔎 Auditar com outra IA", `
    <p>Um <b>segundo codificador</b> (outra IA) confere a classificação resposta por resposta. Quando ele discorda, a sugestão
    aparece na linha da resposta para você aceitar ou não. O ideal é usar um provedor ou modelo diferente do que classificou (${esc(provs[ia.provedor]?.nome || ia.provedor)} · ${esc(ia.modelo || "")}).</p>
    <label class="campo">Provedor do auditor <select id="au-prov">${opcoes}</select></label>
    <label class="campo">Modelo <select id="au-mod"></select></label>
    <label class="campo">O que auditar <select id="au-esc"><option value="pendentes">só as ainda não auditadas (a conferir)</option><option value="todas">todas as que você ainda não conferiu</option></select></label>
    <label><input type="checkbox" id="au-aceitar" checked> depois, aceitar sozinhas as de confiança ≥ ${(state.limiar ?? 0.85).toFixed(2)} em que o auditor concordou</label>
    <div class="dlg-acoes"><button class="btn primary" id="au-ok" type="button">🔎 Auditar</button></div>`);
  const selProv = $("#au-prov"), selMod = $("#au-mod");
  const outro = Object.keys(provs).find((k) => k !== ia.provedor && !provs[k].sem_chave && pronto(k, provs[k]));
  if (outro) selProv.value = outro;
  const encherModelos = () => { const p = provs[selProv.value] || {}; selMod.innerHTML = (p.modelos || [p.modelo]).filter(Boolean).map((m) => `<option value="${esc(m)}">${esc(m)}${m === p.modelo ? " (recomendado)" : ""}</option>`).join(""); };
  selProv.onchange = encherModelos; encherModelos();
  $("#au-ok").onclick = async () => {
    const body = { provedor: selProv.value, modelo: selMod.value, escopo: $("#au-esc").value, aceitar: $("#au-aceitar").checked, limiar: state.limiar ?? 0.85 };
    dlg.close();
    const r = await post(`/api/pergunta/${P.qid}/auditar`, body, "O auditor está conferindo a classificação…", true);
    refresh(r);
    const A = r.auditoria || {};
    abrirJanela("Auditoria concluída", `<p>Auditor: <b>${esc(A.por || "—")}</b>. ${fmtN(A.auditadas || 0)} resposta(s) conferidas:
      <b>${fmtN(A.concorda || 0)}</b> concordam e <b>${fmtN(A.discorda || 0)}</b> discordam.${A.lotes_com_erro ? ` ${A.lotes_com_erro} lote(s) deram erro (rode de novo depois).` : ""}</p>
      ${htmlGanhoAuditoria(A.ganho)}
      ${A.parado_usuario ? `<p class="small">⏹ Parada a seu pedido: o que já foi auditado está salvo; o resto continua sem auditoria.</p>` : ""}
      ${A.auto ? `<p><b>${fmtN(A.auto.aceitas)}</b> aceitas sozinhas (confiança alta + auditor concordando).</p>` : ""}
      <p class="small">As discordâncias aparecem na tabela com <b>🔎 auditor sugere…</b>. Filtre por <b>auditor discordou</b> e use o botão ou a tecla <kbd>S</kbd> para aceitar a sugestão.</p>`);
  };
}
// PEND-24: versões guardadas da classificação e do quadro; restaurar também guarda a versão de hoje (dá para desfazer)
async function abrirJanelaVersoes() {
  const P = state.P, V = await api(`/api/pergunta/${P.qid}/versoes`, {}, "Lendo as versões guardadas…");
  const R = P.revisao || {};
  const nomes = { "codificacao.json": "Classificação das respostas", "frame.json": "Quadro de categorias" };
  const quando = (iso) => new Date(iso).toLocaleString("pt-BR");
  const bloco = (arq) => {
    const lista = V[arq] || [];
    const linhas = lista.map((v, k) => `<tr><td>${esc(quando(v.gravado_em))}</td><td>${esc(v.motivo || "—")}</td>
      <td class="num">${v.n_itens != null ? `${fmtN(v.n_itens)} resp. · ${fmtN(v.n_humano)} conferidas` : `${fmtN(v.n_categorias)} categorias`}</td>
      <td><button class="btn" data-arq="${arq}" data-k="${k}">↶ Restaurar</button></td></tr>`).join("");
    return `<h4>${nomes[arq]}</h4>${lista.length ? `<table class="tab"><thead><tr><th>Quando</th><th>Antes de quê</th><th>Conteúdo</th><th></th></tr></thead><tbody>${linhas}</tbody></table>` : `<p class="small">Nenhuma versão guardada ainda.</p>`}`;
  };
  const dlg = abrirJanela(`🕘 Versões de ${P.qid}`, `
    <p>Antes de cada operação em massa (classificar, auditar, mesclar, apagar, aprovar) e a cada 15 min de revisão, o Tabulador guarda a versão anterior.
    Hoje: <b>${fmtN(R.n_codificadas || 0)}</b> respostas classificadas, <b>${fmtN(R.n_revisadas || 0)}</b> conferidas por pessoa.
    Restaurar também guarda a versão de hoje, então dá para voltar atrás.</p>${bloco("codificacao.json")}${bloco("frame.json")}`);
  dlg.querySelectorAll("button[data-arq]").forEach((b) => b.onclick = async () => {
    const v = V[b.dataset.arq][+b.dataset.k];
    const perda = v.n_humano < (R.n_revisadas || 0) ? "\nAs conferências feitas depois dela serão perdidas (a versão de hoje fica guardada)." : "";
    const delta = v.n_itens != null ? `\n\nHoje: ${R.n_revisadas || 0} conferidas · versão: ${v.n_humano} conferidas.${perda}` : "";
    if (!confirm(`Restaurar "${nomes[b.dataset.arq]}" de ${quando(v.gravado_em)}?${delta}`)) return;
    dlg.close();
    refresh(await post(`/api/pergunta/${P.qid}/restaurar`, { arquivo: b.dataset.arq, gravado_em: v.gravado_em }, "Restaurando a versão…"));
    toast("Versão restaurada");
  });
}
// PEND-23: o que a auditoria trouxe. "Passou pelo auditor" não é "está certa": só a amostra de controle (PEND-32) mede o erro real.
function htmlGanhoAuditoria(g) {
  if (!g) return "";
  const d = g.passaram_depois - g.passaram_antes;
  const cc = g.conf_media_concorda, cd = g.conf_media_discorda;
  const calib = cc == null || cd == null ? "" : (cc - cd < 0.1
    ? `<p class="small">⚠ Confiança média da IA: ${cc.toFixed(2)} onde o auditor concordou × ${cd.toFixed(2)} onde discordou. A confiança da IA não está separando acerto de erro.</p>`
    : `<p class="small">Confiança média da IA: ${cc.toFixed(2)} onde o auditor concordou × ${cd.toFixed(2)} onde discordou.</p>`);
  return `<p>Entre as <b>${fmtN(g.alta)}</b> com confiança ≥ ${g.limiar.toFixed(2)}: <b>${fmtN(g.passaram_antes)}</b> tinham passado pelo auditor antes → <b>${fmtN(g.passaram_depois)}</b> passaram agora
    (confiança alta e outra IA concordou) · <b>${d >= 0 ? "+" : ""}${fmtN(d)}</b>.</p>${calib}
    <p class="small">"Passou pelo auditor" não garante que está certa: dois modelos podem errar juntos.</p>`;
}
// botão de aprovar fica na revbar-sticky (PEND-15), sempre à mão e visível ao rolar a tabela
function renderAprovarBtn() {
  const P = state.P, C = P.codificacao, V = P.revisao;
  if (!C) return "";
  if (C.status === "aprovado") {
    return `<span class="pill ok" style="font-weight:600;padding:5px 10px" title="A classificação desta pergunta já foi aprovada e gravada nos resultados">✓ Aprovada nos resultados</span>`;
  }
  return `<button class="btn ok" id="b-aprovar-cod" ${V.n_faltantes ? `disabled title="Classifique as restantes antes de aprovar"` : ""}>✓ Aprovar e gravar nos resultados</button>`;
}
function bindAprovarBar() {
  const P = state.P; if (!P.codificacao) return;
  $("#b-aprovar-cod")?.addEventListener("click", async () => {
    const V = P.revisao, nCong = V.n_congeladas || 0, naoConf = V.n_codificadas - V.n_revisadas - nCong;
    if (!confirm(`Aprovar a classificação?${P.n_alertas ? `\n• ${P.n_alertas} resposta(s) com alerta` : ""}${naoConf ? `\n• ${naoConf} resposta(s) não conferidas por você (ficam como a IA classificou)` : ""}${nCong ? `\n• ❄ ${nCong} resposta(s) congeladas (saem com a categoria da IA, sem conferência; descongele antes se quiser revisar)` : ""}`)) return;
    refresh(await post(`/api/pergunta/${P.qid}/aprovar`, {}, "Gravando nos resultados…")); toast("Classificação aprovada");
  });
}

// ---------------------------------------------------------------- tabela de classificação
// na tela do grupo cada linha tem a pergunta de origem (r._q) e a trava vale pela classificação DESSA pergunta
const emGrupo = () => !!state.P?._cods;
const travada = (r) => (emGrupo() ? state.P._cods[r._q]?.status === "aprovado" : state.P.codificacao?.status === "aprovado");
const temSugestao = (r) => r.revisao === "pendente" && r.auditoria?.ok === false && r.auditoria.primaria != null && r.auditoria.primaria !== r.primaria;
function situacaoOk(r, s) {
  if (!s) return true;
  if (s === "nao") return r.primaria == null;
  if (s === "alterada") return r.revisao === "alterada";
  if (s === "auto") return r.revisao === "confirmada" && r.validado_por === "auto";
  if (s === "humano") return r.revisao === "confirmada" && r.validado_por !== "auto";
  if (s === "discorda") return temSugestao(r);
  return r.revisao === s;
}
function filtrarItens() {
  // depois de confirmar/corrigir uma linha a ordem fica CONGELADA (nada some do filtro nem troca de
  // lugar, exceto a linha recém-confirmada, que vai para o fim); só reordena/refiltra quando o
  // pesquisador muda filtro/ordenação ou recarrega
  if (state.congelar && state.ordemFixa) {
    const por = new Map(state.P.itens.map((r) => [r.rid, r]));
    return state.ordemFixa.map((rid) => por.get(rid)).filter(Boolean);
  }
  const f = state.filtro, q = f.q.toLowerCase();
  let rows = state.P.itens.filter((r) =>
    (!f.origem || r._q === f.origem) &&
    (!q || (r.texto + " " + (r.justificativa || "")).toLowerCase().includes(q)) &&
    (!f.cat || String(r.primaria) === f.cat || String(r.secundaria) === f.cat) &&
    (!f.alertas || (r.alertas && r.alertas !== "não codificado")) &&
    (!f.comentarios || r.comentario) &&
    situacaoOk(r, f.situacao));
  const conf = (r) => (r.primaria == null ? 9 : r.revisao !== "pendente" ? 2 + (r.confianca ?? 0) : r.confianca ?? 0);
  const faixaConf = (r) => Math.floor(conf(r) * 10);  // agrupa em faixas de 10% para poder desempatar por categoria
  const k = f.ordem;
  const conferida = (r) => (r.revisao === "confirmada" || r.revisao === "corrigida" || r.revisao === "congelada" ? 1 : 0);  // conferidas e congeladas sempre no fim
  rows.sort((a, b) => conferida(a) - conferida(b) ||
    (k === "conf" ? faixaConf(a) - faixaConf(b) || (a.primaria ?? 999) - (b.primaria ?? 999) || conf(a) - conf(b) || b.n - a.n
    : k === "n" ? b.n - a.n
    : (a.primaria ?? 999) - (b.primaria ?? 999) || b.n - a.n));
  state.ordemFixa = rows.map((r) => r.rid);
  return rows;
}
function renderCodificacao() {
  const P = state.P, cats = catsValidas(), n = P.respostas?.n_respondeu || 0, f = state.filtro, locked = P.codificacao.status === "aprovado", V = P.revisao || {};
  const ordem = [...cats].map((c) => ({ c, m: (P.contagens[c.codigo]?.primaria || 0) + (P.contagens[c.codigo]?.secundaria || 0) })).sort((a, b) => b.m - a.m);
  const maxm = Math.max(1, ...ordem.map((o) => o.m));
  const chart = ordem.map(({ c, m }) => `<div class="row"><div class="n" title="${esc(c.nome)}">${esc(c.nome)}</div><div class="bar"><i style="width:${(100 * m) / maxm}%"></i><span>${m} · ${pct(m, n)}</span></div></div>`).join("");
  const optCat = (sel, vazio) => (vazio ? `<option value="">${esc(vazio)}</option>` : "") + optsCategorias(cats, { sel });
  const todas = filtrarItens(), vis = todas.slice(0, state.mostrar);
  // sub-filtro por categoria (visível ao ordenar por confiança): conta ignorando o filtro de categoria em si
  const chipsCat = (() => {
    if (f.ordem !== "conf") return "";
    const q = f.q.toLowerCase(), conta = new Map();
    P.itens.forEach((r) => {
      if (f.origem && r._q !== f.origem) return;
      if (q && !(r.texto + " " + (r.justificativa || "")).toLowerCase().includes(q)) return;
      if (f.alertas && !(r.alertas && r.alertas !== "não codificado")) return;
      if (f.comentarios && !r.comentario) return;
      if (!situacaoOk(r, f.situacao)) return;
      if (r.primaria != null) conta.set(r.primaria, (conta.get(r.primaria) || 0) + 1);
    });
    const chips = cats.filter((c) => conta.get(c.codigo)).map((c) =>
      `<button type="button" class="chip-cat${String(c.codigo) === f.cat ? " on" : ""}" data-cat="${c.codigo}">${esc(c.nome)} <b>${conta.get(c.codigo)}</b></button>`).join("");
    return chips ? `<div class="subfiltro">Refinar por categoria: ${chips}${f.cat ? `<button type="button" class="chip-cat limpar" id="c-cat-limpar">✕ limpar</button>` : ""}</div>` : "";
  })();
  const painelDiscordancias = (() => {
    if (f.situacao !== "discorda") return "";
    const disc = P.itens.filter(temSugestao);
    if (!disc.length) return "";
    const grupos = new Map();
    for (const r of disc) {
      const chave = `${r.primaria}->${r.auditoria.primaria}`;
      if (!grupos.has(chave)) {
        grupos.set(chave, {
          deCod: r.primaria,
          paraCod: r.auditoria.primaria,
          deNome: nomeCat(r.primaria) || String(r.primaria),
          paraNome: nomeCat(r.auditoria.primaria) || String(r.auditoria.primaria),
          rids: []
        });
      }
      grupos.get(chave).rids.push(r.rid);
    }
    const cards = [...grupos.values()].map((g) => `
      <div class="card-sug-grupo" style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 12px;background:var(--surface-2);border-radius:8px;margin-bottom:6px;font-size:13px">
        <div>
          De: <b>${g.deCod}. ${esc(g.deNome)}</b> ➔ Sugestão: <b style="color:var(--accent)">${g.paraCod}. ${esc(g.paraNome)}</b>
          <span class="small muted">(${g.rids.length} resposta${g.rids.length > 1 ? "s" : ""})</span>
        </div>
        <button type="button" class="btn sm ok b-aceitar-grupo" data-paracod="${g.paraCod}" data-rids="${g.rids.join(',')}">✓ Aceitar todas (${g.rids.length})</button>
      </div>`).join("");
    return `<div class="box-instr" style="margin:10px 0"><b>Discordâncias do auditor agrupadas</b><div style="margin-top:8px">${cards}</div></div>`;
  })();
  const rows = vis.map((r) => {
    const nc = r.primaria == null;
    const cls = [r.alertas && !nc ? "alerta" : "", r.revisao === "alterada" ? "alterada" : "", r.revisao === "corrigida" ? "humano" : "", r.revisao === "confirmada" ? "confirmada" : "", r.revisao === "congelada" ? "congelada" : "", r.comentario_pendente ? "pendente" : "", nc ? "naocod" : ""].join(" ");
    const origem = nc ? '<span class="pill">não classificada</span>'
      : r.revisao === "congelada" ? `<span class="pill cong" title="Congelada por ${esc(r.congelada?.por || "alguém")} em ${esc(String(r.congelada?.em || "").slice(0, 16).replace("T", " "))}: nem a conferir nem confirmada">❄ congelada</span>`
      : r.revisao === "alterada" ? `<span class="pill warn" title="${esc(r.alterada_motivo || 'Categoria alterada — reconferir')}">⚠️ alterada</span>`
      : r.revisao === "corrigida" ? `<span class="pill human" title="${r.corrigido_de_nome ? "A IA tinha posto: " + esc(r.corrigido_de_nome) : ""}">✎ você</span>`
      : r.revisao === "confirmada" ? (r.validado_por === "auto" ? `<span class="pill ok auto" title="Confirmada sozinha: confiança alta e o auditor concordou">⚡ auto</span>` : '<span class="pill ok">✓ conferida</span>')
      : r.ia_original_nome ? `<span class="pill acc" title="O auditor corrigiu; a IA tinha posto: ${esc(r.ia_original_nome)}">revisor</span>`
      : r.origem === "regra" ? '<span class="pill">regra</span>' : r.origem === "llm+comentario" ? '<span class="pill acc">IA + comentário</span>' : r.origem === "erro" ? '<span class="pill warn">erro</span>' : '<span class="pill">IA</span>';
    // justificativa: sugestões já adotadas (supervisor.py) guardam o texto do revisor; mostra rotulado
    const just = r.justificativa ? (r.ia_original_nome ? `<small>revisor: ${esc(r.justificativa.replace(/^\[revisor [^:]*: ?/, "").replace(/\] IA tinha: .*$/, ""))} · a IA tinha posto: ${esc(r.ia_original_nome)}</small>` : `<small>IA: ${esc(r.justificativa)}</small>`) : "";
    const sugestao = !travada(r) && temSugestao(r) ? `<div class="sugestao">🔎 auditor sugere: <b>${esc(r.sugestao_nome || r.auditoria.primaria)}</b>${r.sugestao_sec_nome ? ` + ${esc(r.sugestao_sec_nome)}` : ""}${r.auditoria.nota ? ` — ${esc(r.auditoria.nota)}` : ""} <button class="btn sm c-sug" title="Aceitar a sugestão do auditor (tecla S)">aceitar sugestão</button></div>` : "";
    const motivoAlt = r.revisao === "alterada" && r.alterada_motivo ? `<br><small style="color:var(--warn);font-weight:600">⚠️ Reconferir: ${esc(r.alterada_motivo)}</small>` : "";
    const btnFrz = nc || travada(r) ? "" : r.revisao === "congelada" ? `<button class="btn sm c-frz on" title="Descongelar (tecla F): volta a ser a conferir">❄</button>`
      : r.revisao === "pendente" || r.revisao === "alterada" ? `<button class="btn sm c-frz" title="Congelar (tecla F): nem confirmar nem mexer agora; a categoria fica travada até você descongelar">❄</button>` : "";
    const btnOk = nc || travada(r) || r.revisao === "congelada" ? "" : r.revisao === "alterada" ? `<button class="btn sm c-ok alterada" title="Reconfirmar resposta após alteração da categoria">✓</button>` : r.revisao === "corrigida" ? "" : r.revisao === "confirmada" ? `<button class="btn sm c-ok on" title="Desfazer confirmação">✓</button>` : `<button class="btn sm c-ok" title="A IA acertou — confirmar">✓</button>`;
    return `<tr class="${cls}" data-rid="${r.rid}" tabindex="0">
      <td><div class="ok-acoes">${btnOk}${btnFrz}</div></td>
      ${emGrupo() ? `<td><span class="pill" title="Pergunta de origem da resposta">${esc(r._q)}</span></td>` : ""}
      <td>${origem}</td>
      <td><div class="txt-resp${r.texto.length > 280 ? " longa" : ""}" title="${r.texto.length > 280 ? "clique para ver a resposta inteira" : ""}">${esc(r.texto)}</div>${just}${sugestao}${motivoAlt}${r.alertas && !nc ? `<br><span class="pill warn">${esc(r.alertas)}</span>` : ""}${r.corrigido_de_nome ? `<br><small>a IA tinha posto: ${esc(r.corrigido_de_nome)}</small>` : ""}</td>
      <td class="num">${r.n}</td>
      <td><select class="cat c-prim">${nc ? `<option value="" selected>— escolha —</option>` : ""}${optCat(r.primaria, null)}</select></td>
      <td><select class="cat c-sec" ${nc ? "disabled" : ""}>${optCat(r.secundaria, "— nenhuma —")}</select></td>
      <td class="num">${r.confianca == null || nc ? "" : Number(r.confianca).toFixed(2)}</td>
      <td><textarea class="inline c-com" rows="1" ${nc ? "disabled" : ""} placeholder="O que está errado? (a IA reclassifica)">${esc(r.comentario || "")}</textarea>${r.comentario && !r.comentario_pendente ? `<small>já aplicado</small>` : ""}</td>
    </tr>`;
  }).join("");
  const pendVis = vis.filter((r) => r.revisao === "pendente" || r.revisao === "alterada").length;
  return `
    <div class="chart">${chart}</div>
    <div class="tools">
      ${emGrupo() ? `<select id="c-origem"><option value="">todas as questões</option>${Object.keys(P._cods).concat(P._Ps.filter((p) => !P._cods[p.qid]).map((p) => p.qid)).sort().map((q) => `<option value="${esc(q)}" ${f.origem === q ? "selected" : ""}>${esc(q)}</option>`).join("")}</select>` : ""}
      <input id="c-q" placeholder="buscar texto…" value="${esc(f.q)}">
      <select id="c-sit">
        <option value="">todas as situações</option>
        <option value="alterada" ${f.situacao === "alterada" ? "selected" : ""}>⚠️ alteradas para reconferir${V.n_alteradas ? ` (${V.n_alteradas})` : ""}</option>
        <option value="pendente" ${f.situacao === "pendente" ? "selected" : ""}>a conferir</option>
        <option value="confirmada" ${f.situacao === "confirmada" ? "selected" : ""}>confirmadas ✓ (todas)</option>
        <option value="humano" ${f.situacao === "humano" ? "selected" : ""}>confirmadas por pessoas</option>
        <option value="auto" ${f.situacao === "auto" ? "selected" : ""}>confirmadas automaticamente ⚡</option>
        <option value="discorda" ${f.situacao === "discorda" ? "selected" : ""}>auditor discordou 🔎</option>
        <option value="corrigida" ${f.situacao === "corrigida" ? "selected" : ""}>corrigidas por você</option>
        <option value="congelada" ${f.situacao === "congelada" ? "selected" : ""}>❄ congeladas${V.n_congeladas ? ` (${V.n_congeladas})` : ""}</option>
        <option value="nao" ${f.situacao === "nao" ? "selected" : ""}>não classificadas</option>
      </select>
      <select id="c-cat"><option value="">todas as categorias</option>${optsCategorias(cats, { sel: +f.cat || null })}</select>
      <label><input type="checkbox" id="c-al" ${f.alertas ? "checked" : ""}> só alertas</label>
      <label><input type="checkbox" id="c-com" ${f.comentarios ? "checked" : ""}> só comentadas</label>
      <select id="c-ord"><option value="conf" ${f.ordem === "conf" ? "selected" : ""}>ordenar: menor confiança</option><option value="n" ${f.ordem === "n" ? "selected" : ""}>ordenar: mais frequentes</option><option value="cat" ${f.ordem === "cat" ? "selected" : ""}>ordenar: categoria</option></select>
      <span class="small">${vis.length} de ${todas.length} respostas${todas.length !== P.itens.length ? ` (filtradas de ${P.itens.length})` : ""}</span>
      ${!locked && pendVis ? `<button class="btn sm" id="c-ok-todas" title="Confirma as respostas 'a conferir/reconferir' mostradas nesta página">✓ Confirmar as ${pendVis} mostradas</button>` : ""}
    </div>
    ${chipsCat}
    ${painelDiscordancias}
    <table id="tab-cod"><thead><tr><th style="width:44px" title="Confirmar que a IA acertou">OK</th>${emGrupo() ? `<th style="width:70px" title="Questão de origem">Questão</th>` : ""}<th style="width:96px">Situação</th><th>Resposta <small>(e justificativa da IA)</small></th><th class="num" style="width:40px">n</th><th style="width:18%">Categoria principal</th><th style="width:16%">Secundária</th><th class="num" style="width:54px">Conf.</th><th style="width:19%">Comentário para a IA</th></tr></thead><tbody>${rows}</tbody></table>
    ${todas.length > vis.length ? `<div class="tools"><button class="btn" id="c-mais">Mostrar mais ${Math.min(POR_PAGINA, todas.length - vis.length)}</button><span class="small">${todas.length - vis.length} restantes</span></div>` : ""}
    <div class="small atalhos">⌨ <b>Atalhos</b> (clique numa linha primeiro): <kbd>↑</kbd>/<kbd>↓</kbd> ou <kbd>J</kbd>/<kbd>K</kbd> navegar · <kbd>Enter</kbd> confirmar ✓ e ir para a próxima · <kbd>0</kbd>–<kbd>99</kbd> código da categoria · <kbd>C</kbd> comentar (<kbd>Ctrl+Enter</kbd> salva) · <kbd>S</kbd> aceitar sugestão do auditor · <kbd>F</kbd> congelar/descongelar ❄ (nem a conferir, nem confirmada).</div>
    <div class="small">Mudar a categoria vale na hora (fica marcada como sua). ✓ = a IA acertou. Um comentário não muda nada sozinho: vira instrução obrigatória quando você clica em <b>Reclassificar comentadas</b>.</div>`;
}
function proximaLinha(tr, passo) {
  let t = tr;
  do { t = passo > 0 ? t?.nextElementSibling : t?.previousElementSibling; } while (t && t.classList.contains("hid"));
  if (t) t.scrollIntoView({ block: "nearest" });
  return t;
}
function bindCodificacao() {
  const P = state.P; if (!P.codificacao) return;
  state.congelar = false;  // próxima renderização (filtro, ordenação, recarga) volta a ordenar
  const rerender = () => manterScroll(render);
  // re-renderiza mantendo a ordem; a linha `ancora` fica onde estava a linha `rid` na tela
  const rerenderNaLinha = (rid, ancora = rid) => {
    const antes = document.querySelector(`#tab-cod tr[data-rid="${rid}"]`)?.getBoundingClientRect().top;
    state.congelar = true; manterScroll(render);
    const depois = document.querySelector(`#tab-cod tr[data-rid="${ancora}"]`)?.getBoundingClientRect().top;
    if (antes != null && depois != null) window.scrollBy(0, depois - antes);
  };
  document.querySelectorAll("#tab-cod .txt-resp.longa").forEach((d) => (d.onclick = () => d.classList.toggle("aberta")));
  const mudaFiltro = (k, v) => { state.filtro[k] = v; state.mostrar = POR_PAGINA; rerender(); };
  let tq; $("#c-q").oninput = (e) => { clearTimeout(tq); tq = setTimeout(() => { mudaFiltro("q", e.target.value); const i = $("#c-q"); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 350); };
  $("#c-origem")?.addEventListener("change", (e) => mudaFiltro("origem", e.target.value));
  $("#c-sit").onchange = (e) => mudaFiltro("situacao", e.target.value);
  // a ação de uma linha vai para a pergunta dona dela (no grupo, o rid da tela é composto: _rid é o da pergunta)
  const alvo = (rid) => { const it = state.P.itens.find((i) => i.rid === rid); return { q: it?._q || P.qid, rid: it?._rid ?? rid }; };
  $("#c-cat").onchange = (e) => mudaFiltro("cat", e.target.value);
  $("#c-al").onchange = (e) => mudaFiltro("alertas", e.target.checked);
  $("#c-com").onchange = (e) => mudaFiltro("comentarios", e.target.checked);
  $("#c-ord").onchange = (e) => mudaFiltro("ordem", e.target.value);
  document.querySelectorAll(".chip-cat[data-cat]").forEach((b) => (b.onclick = () => mudaFiltro("cat", state.filtro.cat === b.dataset.cat ? "" : b.dataset.cat)));
  $("#c-cat-limpar")?.addEventListener("click", () => mudaFiltro("cat", ""));
  $("#c-mais")?.addEventListener("click", () => { state.mostrar += POR_PAGINA; state.congelar = true; rerender(); });
  $("#c-ok-todas")?.addEventListener("click", async () => {
    const rids = [...document.querySelectorAll("#tab-cod tbody tr")].map((tr) => +tr.dataset.rid).filter((rid) => {
      const sit = state.P.itens.find((i) => i.rid === rid)?.revisao;
      return sit === "pendente" || sit === "alterada";
    });
    const porQ = {};
    for (const rid of rids) { const a = alvo(rid); (porQ[a.q] ||= []).push(a.rid); }
    let r, n = 0;
    for (const [q, rs] of Object.entries(porQ)) { r = await post(`/api/pergunta/${q}/validar`, { rids: rs, valor: true }, "Confirmando…"); n += r.alterados; }
    toast(`${n} resposta(s) confirmada(s)`); refresh(r);
  });
  document.querySelectorAll(".b-aceitar-grupo").forEach((btn) => {
    btn.onclick = async () => {
      const rids = btn.dataset.rids.split(",").map(Number);
      const paraCod = +btn.dataset.paracod;
      btn.disabled = true;
      btn.textContent = "Gravando…";
      for (const rid of rids) {
        const item = state.P.itens.find((i) => i.rid === rid);
        const a = alvo(rid);
        const res = await post(`/api/pergunta/${a.q}/item/${a.rid}`, {
          primaria: paraCod,
          secundaria: item?.auditoria?.secundaria ?? null,
          validado: true
        });
        aplicarItem(item, res.item);
      }
      recalcular();
      toast(`${rids.length} sugestão(ões) aceita(s) em lote`);
      manterScroll(render);
    };
  });
  let numBuf = "", numTimer = null;
  for (const tr of $("#tab-cod tbody").rows) {
    const rid = +tr.dataset.rid, r = state.P.itens.find((i) => i.rid === rid);
    const prim = tr.querySelector(".c-prim"), sec = tr.querySelector(".c-sec"), com = tr.querySelector(".c-com"), ok = tr.querySelector(".c-ok");
    if (travada(r)) { prim.disabled = sec.disabled = com.disabled = true; continue; }
    const cong = r.revisao === "congelada";
    if (cong) prim.disabled = sec.disabled = com.disabled = true;  // categoria travada até descongelar
    const congelar = async (valor) => {
      const seguinte = valor ? proximaLinha(tr, 1)?.dataset.rid : null;
      const a = alvo(rid);
      const res = await post(`/api/pergunta/${a.q}/item/${a.rid}/congelar`, { congelada: valor });
      aplicarItem(r, res.item); recalcular();
      if (valor && state.ordemFixa) state.ordemFixa = [...state.ordemFixa.filter((x) => x !== rid), rid];  // vai para o fim, como as conferidas
      rerenderNaLinha(rid, seguinte ? +seguinte : rid);
      toast(valor ? "Resposta congelada ❄ (nem a conferir, nem confirmada)" : "Resposta descongelada");
      document.querySelector(`#tab-cod tr[data-rid="${seguinte || rid}"]`)?.focus({ preventScroll: true });
    };
    tr.querySelector(".c-frz")?.addEventListener("click", () => congelar(!cong));
    const salvar = async (body, msg, proxima = false) => {
      const antes = r.revisao, seguinte = proximaLinha(tr, 1)?.dataset.rid;
      tr.classList.add("just-confirmed");
      const a = alvo(rid);
      const res = await post(`/api/pergunta/${a.q}/item/${a.rid}`, body);
      aplicarItem(r, res.item); recalcular();
      // recém-confirmada vai para o fim e a seguinte sobe para o lugar dela (o mouse não precisa se mexer)
      if (r.revisao === "confirmada" && antes !== "confirmada" && seguinte && state.ordemFixa) {
        state.ordemFixa = [...state.ordemFixa.filter((x) => x !== rid), rid];
        rerenderNaLinha(rid, +seguinte); toast(msg);
        document.querySelector(`#tab-cod tr[data-rid="${seguinte}"]`)?.focus({ preventScroll: true });
        return;
      }
      rerenderNaLinha(rid); toast(msg);
      // devolve o foco à tabela para continuar pelo teclado
      const atual = document.querySelector(`#tab-cod tr[data-rid="${rid}"]`);
      (proxima ? proximaLinha(atual, 1) : atual)?.focus({ preventScroll: false });
    };
    tr.onkeydown = (e) => {
      if (e.target !== tr) return;  // digitando num campo: não interfere
      const keyLow = e.key.toLowerCase();
      if (e.key === "ArrowDown" || keyLow === "j") { e.preventDefault(); proximaLinha(tr, 1)?.focus(); }
      else if (e.key === "ArrowUp" || keyLow === "k") { e.preventDefault(); proximaLinha(tr, -1)?.focus(); }
      else if (e.key === "Enter" && r.primaria != null) {
        e.preventDefault();
        if (r.revisao === "pendente" || r.revisao === "alterada") salvar({ validado: true }, "Confirmada ✓", true);
        else proximaLinha(tr, 1)?.focus();
      } else if (keyLow === "f" && r.primaria != null && (cong || r.revisao === "pendente" || r.revisao === "alterada")) { e.preventDefault(); congelar(!cong); }
      else if (cong && (keyLow === "c" || keyLow === "s" || /^[0-9]$/.test(e.key))) { e.preventDefault(); toast("Resposta congelada ❄: descongele (tecla F) para mexer nela.", true); }
      else if (keyLow === "c" && !com.disabled) { e.preventDefault(); com.focus(); }
      else if (keyLow === "s" && temSugestao(r)) { e.preventDefault(); aceitarSugestao(); }
      else if (/^[0-9]$/.test(e.key)) {
        e.preventDefault();
        clearTimeout(numTimer);
        numBuf += e.key;
        numTimer = setTimeout(() => {
          const cod = +numBuf;
          numBuf = "";
          const cat = catsValidas().find((c) => c.codigo === cod);
          if (cat && cat.codigo !== r.primaria) { salvar({ primaria: cat.codigo }, `Categoria principal: ${cat.codigo} · ${cat.nome}`); }
          else if (!cat) { toast(`Categoria ${cod} não encontrada`, true); }
        }, 360);
      }
    };
    com.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { com.blur(); tr.focus(); }
      else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault(); com.blur();
        salvar({ comentario: com.value }, com.value.trim() ? "Comentário salvo" : "Comentário removido");
        tr.focus();
      }
    });
    prim.onchange = () => prim.value && salvar({ primaria: prim.value }, "Categoria principal alterada");
    sec.onchange = () => salvar({ secundaria: sec.value || null }, "Categoria secundária alterada");
    com.onchange = () => salvar({ comentario: com.value }, com.value.trim() ? "Comentário salvo — clique em 'Reclassificar comentadas' para a IA aplicar" : "Comentário removido");
    com.addEventListener("focus", () => { com.rows = 3; }); com.addEventListener("blur", () => { com.rows = 1; });
    ok?.addEventListener("click", () => salvar({ validado: r.revisao !== "confirmada" }, r.revisao === "confirmada" ? "Confirmação desfeita" : "Confirmada ✓"));
    // aceitar a sugestão do auditor = correção feita por você (vai para o fim, como as conferidas)
    const aceitarSugestao = () => salvar({ primaria: r.auditoria.primaria, secundaria: r.auditoria.secundaria ?? null },
      `Sugestão do auditor aceita: ${r.sugestao_nome || r.auditoria.primaria}`, true);
    tr.querySelector(".c-sug")?.addEventListener("click", aceitarSugestao);
  }
  // Auto-foco na primeira linha pendente se nenhuma estiver focada
  if (!document.activeElement || document.activeElement === document.body) {
    const pend = document.querySelector("#tab-cod tbody tr:not(.confirmada):not(.hid)");
    if (pend) pend.focus({ preventScroll: true });
  }
}


// ---------------------------------------------------------------- grupos de categorias
// Renderiza o banner que aparece no topo da página da pergunta quando ela pertence a um grupo.
function renderGrupoBanner(dados) {
  if (!dados.grupo) return '';
  const { nome, rotulo, membros } = dados.grupo;
  const lista = (membros || []).map((qid) => {
    const ativo = qid === dados.qid ? ' class="grupo-membro-atual"' : '';
    return `<span${ativo}>${esc(qid)}</span>`;
  }).join(' · ');
  return `
    <div class="grupo-banner" data-grupo="${esc(nome)}">
      <span class="grupo-banner-icon">🔗</span>
      <div class="grupo-banner-info">
        <strong>${esc(rotulo)}</strong>
        <div class="grupo-banner-membros">${lista}</div>
        ${dados.grupo.tem_quadro ? "" : `<div class="grupo-banner-membros">O grupo ainda não tem quadro de categorias: esta pergunta segue com o quadro dela.</div>`}
      </div>
      <a class="grupo-btn-editar" href="#grupo/${esc(nome)}">Abrir o grupo</a>
    </div>`;
}

// ---------------------------------------------------------------- página do grupo
// Um grupo é UM quadro de categorias e UMA tabela de revisão com as respostas de todas as perguntas
// (coluna "Questão"). Cada pergunta continua com a própria classificação e aprova o quadro e a
// classificação por conta própria; o grupo fecha quando todas estão concluídas.
async function carregarGrupo(nome) {
  const G = await api(`/api/grupo/${encodeURIComponent(nome)}`);
  const Ps = await Promise.all(G.perguntas.map((q) => api(`/api/pergunta/${q.qid}`)));
  const itens = [], cods = {};
  Ps.forEach((Pq, i) => {
    if (Pq.codificacao) cods[Pq.qid] = Pq.codificacao;
    for (const r of Pq.itens || []) itens.push({ ...r, _q: Pq.qid, _rid: r.rid, rid: (i + 1) * 1e6 + r.rid });
  });
  state.P = {
    qid: G.perguntas[0].qid, rotulo: G.rotulo, frame: G.frame, itens, _G: G, _Ps: Ps, _cods: cods,
    respostas: { n_respondeu: Ps.reduce((a, p) => a + (p.respostas?.n_respondeu || 0), 0), n_unicas: Ps.reduce((a, p) => a + (p.respostas?.n_unicas || 0), 0) },
    codificacao: Object.keys(cods).length ? { status: Ps.every((p) => p.codificacao?.status === "aprovado") ? "aprovado" : "rascunho" } : null,
    pode_desfazer_refino: G.pode_desfazer_refino, avisos_atributo: G.avisos_atributo, saude: G.saude,
    grupo: { nome: G.nome, rotulo: G.rotulo, membros: G.perguntas.map((q) => q.qid), tem_quadro: !!G.frame },
  };
  prepararItens(); recalcular();
}
async function abrirGrupo(nome) {
  if (state.grupo !== nome) { state.filtro = filtroInicial(); state.mostrar = POR_PAGINA; }
  state.view = "grupo"; state.grupo = nome; state.qid = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando o grupo…</div>`;
  await carregarGrupo(nome);
  render(); window.scrollTo(0, 0);
}
async function refreshGrupo(payload) {
  await carregarGrupo(state.grupo);
  manterScroll(render); carregarStatus();
  avisosDoPayload(payload);
}
function cardMembroGrupo(Pq, a) {
  const C = Pq.codificacao, V = Pq.revisao, F = state.P.frame, q = Pq.qid;
  const faltam = V ? V.n_faltantes : 0, tot = V ? V.n_unicas : Pq.respostas?.n_unicas || 0;
  const maxTam = (C ? faltam : Pq.respostas?.n_unicas) || "";
  const tam = `<input class="tam-amostra g-tam" type="number" min="1" ${maxTam ? `max="${maxTam}"` : ""} value="${maxTam ? Math.min(state.amostra, maxTam) : state.amostra}" title="Quantas respostas mandar para a IA">`;
  let acoes;
  if (!a.quadro_aprovado) acoes = `<button class="btn ok g-aprovar-quadro" ${F ? "" : "disabled title='Gere as categorias do grupo primeiro'"}>✓ Aprovar categorias para ${esc(q)}</button>`;
  else if (!C) acoes = `<button class="btn primary g-amostra">✨ Classificar amostra</button>${tam}<span class="small">respostas</span><button class="btn g-todas">Todas de uma vez</button>`;
  else if (C.status === "aprovado") acoes = `<span class="pill ok">✓ Classificação aprovada</span><button class="btn g-reabrir">Reabrir para correções</button>`;
  else acoes = `${faltam ? `<button class="btn primary g-restantes">Classificar as restantes (${faltam})</button>` : ""}
    <button class="btn g-recod" ${Pq.n_comentarios_pendentes ? "" : "disabled"}>✨ Reclassificar comentadas (${Pq.n_comentarios_pendentes || 0})</button>
    <button class="btn ok g-aprovar-cod" ${faltam ? `disabled title="Classifique as restantes antes de aprovar"` : ""}>✓ Aprovar classificação</button>`;
  return `<div class="card-q-grupo" data-q="${esc(q)}">
    <div class="cab"><b>${esc(q)}</b> ${esc(Pq.rotulo)}
      <span class="pill ${a.quadro_aprovado ? "ok" : "warn"}">categorias ${a.quadro_aprovado ? "aprovadas" : "a aprovar"}</span>
      <span class="pill ${C?.status === "aprovado" ? "ok" : ""}">${C ? (C.status === "aprovado" ? "concluída" : "classificação em revisão") : "sem classificação"}</span></div>
    <div class="small">${V ? `${fmtN(V.n_revisadas)} de ${fmtN(tot)} respostas conferidas · ${fmtN(V.n_codificadas)} classificadas` : `${fmtN(tot)} respostas únicas`} ·
      <a href="#${esc(q)}">abrir a pergunta (auditoria, aceite automático, revisão por categoria)</a></div>
    <div class="tools">${acoes}</div></div>`;
}
function renderGrupo() {
  const P = state.P, G = P._G, F = P.frame, V = P.revisao, R = P.respostas;
  const porQ = Object.fromEntries(G.andamento.map((a) => [a.qid, a]));
  const cobertura = G.cobertura
    ? Object.entries(G.cobertura.perguntas).map(([q, c]) => `<b>${esc(q)}</b>: ${fmtN(c.lidas)} de ${fmtN(c.unicas)}`).join(" · ")
    : "";
  const totRev = V ? V.n_unicas : 0, nRev = V ? V.n_revisadas : 0, pctRev = totRev ? Math.round((100 * nRev) / totRev) : 0;
  $("main").innerHTML = `
    <div class="q-cab">
      <div class="q-cab-txt">
        <div class="small"><a href="#painel">← Painel geral</a> · <a href="#grupos">Gerenciar grupos</a></div>
        <h1>🔗 ${esc(G.rotulo)} <small>${esc(P.grupo.membros.join(" + "))}</small> <span class="pill warn" style="font-size:12px;vertical-align:middle" title="A lógica dos grupos ainda vai mudar (PEND-38)">EM DESENVOLVIMENTO</span></h1>
        <div>${G.fechado ? `<span class="pill ok" style="font-weight:600;padding:5px 10px">✓ Grupo fechado: todas as perguntas concluídas</span>`
          : `<span class="pill warn">Grupo em andamento — ${G.andamento.filter((a) => a.classificacao === "aprovado").length} de ${G.andamento.length} perguntas concluídas</span>`}</div>
      </div>
      ${totRev ? `<div class="sticky-num" title="${fmtN(nRev)} de ${fmtN(totRev)} respostas conferidas por pessoas">
        <div class="n">${fmtN(nRev)}<i> / ${fmtN(totRev)}</i></div><div class="lab">revisadas / total</div><div class="bar"><i style="width:${pctRev}%"></i></div></div>` : ""}
    </div>
    <div class="info">Um quadro de categorias para todas as perguntas do grupo. Cada pergunta aprova as categorias e a classificação <b>por conta própria</b>; o grupo fecha quando todas concluem.${G.instrucoes_frame ? `<br><b>Instruções do grupo para a IA:</b> ${esc(G.instrucoes_frame)} <span class="small">(editar em <a href="#grupos">Grupos</a>)</span>` : ""}</div>

    <h2>Categorias do grupo
      ${F ? `<span class="pill">${esc(String(F.categorias.filter((c) => !c.fixa).length))} categorias</span>` : ""}
      <span class="acoes"><button class="btn ${F ? "" : "primary"}" id="b-g-induzir">✨ ${F ? "Gerar do zero (grupo)" : "Gerar categorias do grupo"}</button></span>
    </h2>
    ${cobertura ? `<div class="info">📊 <b>Respostas lidas pela IA</b> (únicas): ${cobertura}${G.cobertura.amostra ? ` — <b>amostra</b> (limite de ${fmtN(G.cobertura.limite)}): cada pergunta entrou com cota mínima e as respostas repetidas foram incluídas.` : " — a IA leu todas as respostas de todas as perguntas."}</div>` : ""}
    ${F ? renderFrame() : `<div class="info">A IA lê as respostas de <b>todas as perguntas do grupo</b> e propõe uma lista fechada de categorias (uma ideia por categoria). Depois você ajusta e cada pergunta aprova.</div>`}
    ${renderSaude()}

    <h2>Perguntas do grupo</h2>
    <div class="cards-q-grupo">${P._Ps.map((Pq) => cardMembroGrupo(Pq, porQ[Pq.qid])).join("")}</div>

    <h2 id="area-revisao">Revisão das respostas <small>todas as perguntas, uma tabela só</small></h2>
    ${P.codificacao ? renderCodificacao() : `<div class="info">Aprove as categorias em cada pergunta e classifique uma amostra para liberar a revisão.</div>`}
  `;
  bindFrame(); bindGrupo(); bindCodificacao();
  medirAlturasFixas(); observarCabecalho();
}
function bindGrupo() {
  const P = state.P, G = P._G;
  $("#b-g-induzir")?.addEventListener("click", async () => {
    if (P.frame && !confirm("Gerar do zero substitui as categorias do grupo (e as aprovações). Para ajustes pontuais, use 'Pedir ajuste à IA'. Continuar?")) return;
    refresh(await post(`/api/grupo/${encodeURIComponent(G.nome)}/frame/induzir`, {}, "Gerando categorias do grupo…", true));
  });
  const lerTam = (card) => {
    const campo = card.querySelector(".g-tam"), n = Math.floor(+campo.value), max = +campo.max || Infinity;
    if (!(n >= 1)) { toast("Digite quantas respostas mandar para a IA (1 ou mais).", true); campo.focus(); return null; }
    state.amostra = Math.min(n, max); return state.amostra;
  };
  document.querySelectorAll(".card-q-grupo").forEach((card) => {
    const q = card.dataset.q, rota = (c) => `/api/pergunta/${q}/${c}`;
    const Pq = P._Ps.find((p) => p.qid === q);
    card.querySelector(".g-aprovar-quadro")?.addEventListener("click", async () => refresh(await post(rota("frame/aprovar"), {}, "Aprovando…")));
    card.querySelector(".g-amostra")?.addEventListener("click", () => {
      const n = lerTam(card); if (!n || !confirmarVolume(n, `Classificar amostra de ${q}`)) return;
      post(rota("codificar"), { limite: n }, `A IA está classificando uma amostra de ${n} (${q})…`, true).then(refresh);
    });
    card.querySelector(".g-todas")?.addEventListener("click", () => {
      const n = Pq.respostas?.n_unicas;
      if (!confirm(`Classificar todas as ${n} respostas de ${q} agora? (Recomendado: testar numa amostra antes.)`)) return;
      post(rota("codificar"), {}, `A IA está classificando ${q}…`, true).then(refresh);
    });
    card.querySelector(".g-restantes")?.addEventListener("click", () => {
      if (!confirmarVolume(Pq.revisao?.n_faltantes, `Classificar as restantes de ${q}`)) return;
      post(rota("codificar"), { restantes: true }, `A IA está classificando as restantes (${q})…`, true).then(refresh);
    });
    card.querySelector(".g-recod")?.addEventListener("click", async () => {
      const r = await post(rota("recodificar"), { apenas_comentados: true }, "Reclassificando as comentadas…", true);
      toast(`${r.recodificados} resposta(s) reclassificada(s)`); refresh(r);
    });
    card.querySelector(".g-aprovar-cod")?.addEventListener("click", async () => {
      const V = Pq.revisao, naoConf = V.n_codificadas - V.n_revisadas;
      if (!confirm(`Aprovar a classificação de ${q}?${naoConf ? `\n• ${naoConf} resposta(s) não conferidas por você (ficam como a IA classificou)` : ""}`)) return;
      refresh(await post(rota("aprovar"), {}, "Gravando nos resultados…")); toast(`Classificação de ${q} aprovada`);
    });
    card.querySelector(".g-reabrir")?.addEventListener("click", async () => refresh(await post(rota("reabrir"), {}, "Reabrindo…")));
  });
}

// ---------------------------------------------------------------- aba Grupos de perguntas
// Perguntas de um grupo dividem o MESMO quadro de categorias (ex.: Q32 + Q33). Aqui o grupo é criado,
// editado e desfeito à mão. Antes de gravar, o servidor diz o que a mudança faz com o trabalho já feito
// (avisos de nível "alto" pedem confirmação) — nada é gravado sem a pessoa ver isso.
const pctBR = (f) => (100 * f).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";
function cardGrupo(g, D) {
  // g = { nome, rotulo, instrucoes_frame, membros:[{qid,...}], frame } — ou { nome: null, ... } para um grupo novo
  const marcadas = new Set((g.membros || []).map((m) => m.qid));
  const caixas = D.perguntas.map((q) => {
    const outro = q.grupo && q.grupo !== g.nome ? D.grupos.find((x) => x.nome === q.grupo) : null;
    return `<label class="gr-q-lin${outro ? " ocupada" : ""}">
      <input type="checkbox" class="gr-q" value="${esc(q.qid)}" ${marcadas.has(q.qid) ? "checked" : ""} ${outro ? "disabled" : ""}>
      <b>${esc(q.qid)}</b> ${esc(q.rotulo)}${outro ? ` <span class="small">— já no grupo “${esc(outro.rotulo)}”</span>` : ""}
    </label>`;
  }).join("");
  const andamento = (g.membros || []).map((m) => `<span class="pill">${esc(m.qid)}: ${fmtN(m.n_codificadas)} classificadas · ${fmtN(m.n_revisadas)} conferidas</span>`).join(" ");
  const quadro = !g.nome ? "" : g.frame
    ? `<span class="pill ${g.frame.status === "aprovado" ? "ok" : "warn"}">quadro do grupo: ${esc(g.frame.status)} · ${g.frame.n_categorias} categorias</span>`
    : `<span class="pill">quadro do grupo ainda não gerado — gere em qualquer pergunta do grupo</span>`;
  return `<div class="gr-card" data-nome="${esc(g.nome || "")}">
    <div class="gr-cab"><b>${g.nome ? "🔗 " + esc(g.rotulo) : "➕ Novo grupo"}</b> ${quadro}</div>
    ${andamento ? `<div class="gr-and">${andamento}</div>` : ""}
    <label class="gr-lab">Nome do grupo<input class="gr-rotulo" value="${esc(g.rotulo || "")}" placeholder="Ex.: Motivo para trocar de escola"></label>
    <div class="gr-lab">Perguntas do grupo <span class="small">(marque 2 ou mais; só aparecem livres as que não estão em outro grupo)</span></div>
    <div class="gr-qs">${caixas}</div>
    <label class="gr-lab">Instruções para a IA montar as categorias do grupo <span class="small">(opcional)</span>
      <textarea class="gr-instr" rows="3">${esc(g.instrucoes_frame || "")}</textarea></label>
    <div class="gr-avisos"></div>
    <div class="gr-acoes">
      <button class="btn primary gr-salvar">${g.nome ? "Salvar alterações" : "Criar grupo"}</button>
      ${g.nome ? `<button class="btn gr-dissolver">Dissolver grupo</button>` : ""}
    </div>
  </div>`;
}
function avisosGrupo(card, r, aoConfirmar, rotuloBotao) {
  const caixa = card.querySelector(".gr-avisos");
  caixa.innerHTML = `<div class="aviso"><b>Antes de continuar, veja o que isso muda:</b>
    <ul>${r.avisos.map((a) => `<li class="gr-av-${a.nivel}">${esc(a.msg)}</li>`).join("")}</ul>
    <button class="btn primary sm gr-confirmar">${rotuloBotao}</button> <button class="btn sm gr-cancelar">Cancelar</button></div>`;
  caixa.querySelector(".gr-confirmar").onclick = aoConfirmar;
  caixa.querySelector(".gr-cancelar").onclick = () => (caixa.innerHTML = "");
}
async function renderGrupos() {
  state.view = "grupos"; state.qid = null; state.P = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando grupos…</div>`;
  const D = await api("/api/grupos");
  const sugestoes = D.sugestoes.map((s, i) => `<div class="gr-sug">
      <span><b>${s.perguntas.map(esc).join(" + ")}</b> — ${s.rotulos.map(esc).join(" / ")}
      <span class="small">· ${s.em_comum ? `só ${s.em_comum} ${s.em_comum === 1 ? "pessoa respondeu" : "pessoas responderam"} as duas (${pctBR(s.pct)})` : "ninguém respondeu as duas"}</span></span>
      <button class="btn sm" data-sug="${i}">Criar grupo com estas</button></div>`).join("");
  $("#main").innerHTML = `
    <h1>Grupos de perguntas <span class="pill warn" style="font-size:12px;vertical-align:middle">EM DESENVOLVIMENTO</span></h1>
    <div class="aviso">🚧 <b>Em desenvolvimento.</b> A lógica dos grupos (quadro único, aprovação por pergunta) ainda vai mudar — a ideia é ter categorias base do grupo mais categorias próprias de cada pergunta (PEND-38). Use com cuidado e evite montar trabalho grande em cima dela por enquanto.</div>
    <div class="info">Um grupo junta perguntas que se complementam — quem responde uma não responde a outra (por exemplo, nota baixa × nota alta) — para que dividam
      <b>o mesmo quadro de categorias</b>. Cada pergunta continua sendo classificada e conferida separadamente. Mexer num grupo que já tem trabalho feito mostra um aviso antes de gravar.</div>
    ${sugestoes ? `<h2>Sugestões <small>pares de perguntas que quase ninguém respondeu juntas</small></h2><div class="gr-sugs">${sugestoes}</div>` : ""}
    <h2>Grupos do projeto <small>${D.grupos.length}</small></h2>
    <div id="gr-lista">${D.grupos.map((g) => cardGrupo(g, D)).join("") || '<div class="small muted">Nenhum grupo ainda.</div>'}</div>
    <h2>Novo grupo</h2>
    <div id="gr-novo">${cardGrupo({ nome: null, rotulo: "", instrucoes_frame: "", membros: [] }, D)}</div>`;

  const ler = (card) => ({
    nome: card.dataset.nome || null,
    rotulo: card.querySelector(".gr-rotulo").value.trim(),
    instrucoes_frame: card.querySelector(".gr-instr").value,
    perguntas: [...card.querySelectorAll(".gr-q:checked")].map((c) => c.value),
  });
  const salvar = async (card, confirmado) => {
    const r = await post("/api/grupos/salvar", { ...ler(card), confirmado }, "Salvando o grupo…");
    if (r.precisa_confirmar) return avisosGrupo(card, r, () => salvar(card, true), "Entendi, aplicar mesmo assim");
    toast((r.avisos || []).length ? "Grupo salvo — veja os avisos na página das perguntas" : "Grupo salvo");
    await carregarStatus(); renderGrupos();
  };
  const dissolver = async (card, confirmado) => {
    const r = await post(`/api/grupos/${encodeURIComponent(card.dataset.nome)}/dissolver`, { confirmado }, "Desfazendo o grupo…");
    if (r.precisa_confirmar) return avisosGrupo(card, r, () => dissolver(card, true), "Entendi, dissolver mesmo assim");
    toast("Grupo dissolvido — a pasta dele foi guardada em grupos/_dissolvidos");
    await carregarStatus(); renderGrupos();
  };
  document.querySelectorAll(".gr-card").forEach((card) => {
    card.querySelector(".gr-salvar").onclick = () => salvar(card, false);
    const d = card.querySelector(".gr-dissolver");
    if (d) d.onclick = () => dissolver(card, false);
  });
  document.querySelectorAll("[data-sug]").forEach((b) => (b.onclick = () => {
    const s = D.sugestoes[+b.dataset.sug], novo = $("#gr-novo .gr-card");
    novo.querySelectorAll(".gr-q").forEach((c) => (c.checked = s.perguntas.includes(c.value)));
    novo.querySelector(".gr-rotulo").value = s.rotulos.join(" / ");
    novo.scrollIntoView({ behavior: "smooth", block: "center" });
    novo.querySelector(".gr-rotulo").focus();
  }));
}

// ---------------------------------------------------------------- resultados
const linhaArquivo = (R, tipo, titulo, desc) => {
  const r = R[tipo]; if (!r) return "";
  return `<tr><td><b>${titulo}</b><br><small>${desc}</small></td><td>${r.existe ? `atualizado ${esc(r.atualizado_em)}` : '<span class="small">ainda não gerado</span>'}</td>
    <td class="acoes">${tipo !== "base" ? `<button class="btn sm" data-gerar="${tipo}">${r.existe ? "↻ Atualizar" : "Gerar"}</button>` : ""} ${r.existe ? `<a class="btn sm primary" href="/arquivo/${tipo}">⬇ Baixar</a>` : ""}</td></tr>`;
};
function painelCruzamento(D) {
  const vars = D.variaveis || [];
  if (state.cruzSelecionadas == null) state.cruzSelecionadas = new Set(D.padrao || []);
  const chips = vars.map((v) =>
    `<label><input type="checkbox" class="cruz-var" value="${esc(v.chave)}" ${state.cruzSelecionadas.has(v.chave) ? "checked" : ""}> ${esc(v.rotulo)}</label>`).join("");
  return `<div class="box-instr" id="cruz-picker">
    <b>Variáveis de cruzamento</b> <span class="small">— o que entra nas tabelas de "Cruzamentos" (aba Geral e uma aba por pergunta)</span>
    <div class="tools">${chips || '<span class="small">nenhuma variável de cruzamento configurada neste projeto</span>'}</div>
  </div>`;
}
function painelGeral(G) {
  const temas = G.temas || [], trechos = G.trechos || [];
  const max = Math.max(1, ...temas.map((t) => t.mencoes));
  const narrativa = G.narrativa
    ? `<p>${esc(G.narrativa)}</p><div class="small">Resumo gerado em ${esc(G.narrativa_gerada_em || "")} · <button class="btn sm" id="g-atualizar">↻ Atualizar resumo</button></div>`
    : `<div class="info">Ainda não há um resumo geral do projeto. <button class="btn primary sm" id="g-gerar">✨ Gerar resumo com IA</button></div>`;
  const chart = temas.length ? `<div class="legenda"><span><i></i>menções, somando todas as perguntas abertas aprovadas</span></div><div class="chart">${temas.map((t) =>
    `<div class="row"><div class="n" title="${esc(t.pergunta)}">${esc(t.nome)} <small>(${esc(t.pergunta)})</small></div><div class="bar"><i style="width:${(100 * t.mencoes) / max}%"></i><span>${t.mencoes}</span></div></div>`).join("")}</div>` : "";
  const listaTrechos = trechos.length ? `<div class="small" style="margin-top:8px"><b>O que as pessoas escreveram:</b></div>${trechos.map((t) =>
    `<div class="small">"${esc(t.texto)}" <i>— ${esc(t.pergunta)}</i></div>`).join("")}` : "";
  return `<div class="res-q">${narrativa}${chart}${listaTrechos}</div>`;
}
async function renderResultados() {
  state.view = "resultados"; state.qid = null; state.P = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando resultados…</div>`;
  const [D, VC, G] = await Promise.all([api("/api/resultados"), api("/api/variaveis-cruzamento"), api("/api/resumo-geral")]);
  const R = D.arquivos, Q = D.perguntas;
  const aprov = Q.filter((q) => q.codificacao === "aprovado");
  const soma = (k) => Q.reduce((a, q) => a + (q[k] || 0), 0);
  const aval = Q.filter((q) => q.acerto_ia != null && q.n_avaliadas_ia);
  const acertoMedio = aval.length ? aval.reduce((a, q) => a + q.acerto_ia * q.n_avaliadas_ia, 0) / aval.reduce((a, q) => a + q.n_avaliadas_ia, 0) : null;
  $("#main").innerHTML = `
    <h1>Resultados <small>${esc(D.projeto)}</small></h1>
    <div class="tiles">
      <div class="tile grande"><div class="l">Perguntas aprovadas</div><div class="v">${aprov.length}<small style="font-size:18px"> de ${Q.length}</small></div><div class="small">só as aprovadas entram nos arquivos</div></div>
      <div class="tile grande"><div class="l">Respostas classificadas</div><div class="v">${fmtN(soma("n_codificadas"))}</div><div class="small">respostas diferentes, somando as perguntas</div></div>
      <div class="tile grande"><div class="l">Conferidas por pessoas</div><div class="v">${fmtN(soma("n_revisadas"))}</div><div class="small">${fmtN(soma("n_confirmadas"))} confirmadas · ${fmtN(soma("n_corrigidas"))} corrigidas</div></div>
      <div class="tile grande"><div class="l">Acerto da IA</div><div class="v">${acertoMedio == null ? "–" : Math.round(100 * acertoMedio) + "%"}</div><div class="small">nas respostas que alguém conferiu</div></div>
    </div>
    <h2>Arquivos para baixar <span class="acoes"><button class="btn primary" id="r-todos">↻ Atualizar todos</button><button class="btn" data-acao="pasta">📂 Abrir pasta</button></span></h2>
    <div class="info">Os arquivos usam apenas as perguntas <b>aprovadas</b>. Depois de aprovar ou corrigir algo, clique em “Atualizar todos”.</div>
    ${painelCruzamento(VC)}
    <table class="res"><tbody>
      ${linhaArquivo(R, "planilha", "Planilha final categorizada", "a planilha original com as colunas de categoria preenchidas (e a secundária ao lado)")}
      ${linhaArquivo(R, "codebook", "Codebook", "todas as variáveis, valores e as categorias de cada pergunta aberta")}
      ${linhaArquivo(R, "cruzamentos", "Cruzamentos (tabelas)", "aba Geral com todas as variáveis + uma aba por pergunta, cruzadas com as variáveis escolhidas acima")}
      ${linhaArquivo(R, "base", "Base processada", "uma linha por respondente, com os códigos das categorias")}
    </tbody></table>
    <h2>Visão geral do projeto</h2>
    ${painelGeral(G)}`;
  document.querySelector("[data-acao=pasta]").onclick = () => post("/api/abrir-pasta");
  $("#r-todos").onclick = async () => { await post("/api/gerar-todos", {}, "Gerando todos os resultados…"); toast("Arquivos atualizados — clique em Baixar."); renderResultados(); carregarStatus(); };
  document.querySelectorAll(".cruz-var").forEach((cb) => (cb.onchange = () => {
    if (cb.checked) state.cruzSelecionadas.add(cb.value); else state.cruzSelecionadas.delete(cb.value);
  }));
  document.querySelectorAll("[data-gerar]").forEach((btn) => (btn.onclick = async () => {
    const body = btn.dataset.gerar === "cruzamentos" ? { banners: [...state.cruzSelecionadas] } : {};
    await post(`/api/gerar/${btn.dataset.gerar}`, body, "Gerando o arquivo…"); toast("Pronto! Clique em Baixar."); renderResultados();
  }));
  $("#g-gerar")?.addEventListener("click", async () => { await post("/api/resumo-geral/gerar", {}, "Gerando resumo com IA…"); toast("Resumo gerado"); renderResultados(); });
  $("#g-atualizar")?.addEventListener("click", async () => {
    if (!confirm("Gerar um novo resumo? O atual será substituído.")) return;
    await post("/api/resumo-geral/gerar", {}, "Atualizando resumo…"); toast("Resumo atualizado"); renderResultados();
  });
}

// ---------------------------------------------------------------- gerenciar projeto (zona de perigo)
// Confirmação forte: a pessoa digita uma palavra (ou o nome do projeto) para liberar o botão.
function confirmarPerigo({ titulo, texto, palavra, botao = "Apagar", extra = "" }) {
  return new Promise((resolve) => {
    const dlg = $("#dlg-perigo");
    $("#pg-titulo").textContent = titulo; $("#pg-texto").innerHTML = texto; $("#pg-extra").innerHTML = extra;
    $("#pg-palavra").textContent = palavra; $("#pg-input").value = ""; $("#pg-ok").textContent = botao; $("#pg-ok").disabled = true;
    $("#pg-input").oninput = () => ($("#pg-ok").disabled = $("#pg-input").value.trim().toLowerCase() !== palavra.toLowerCase());
    dlg.onclose = () => resolve(dlg.returnValue === "ok" ? { ok: true, marcado: !!$("#pg-extra input[type=checkbox]")?.checked } : null);
    dlg.returnValue = ""; dlg.showModal(); $("#pg-input").focus();
  });
}
async function renderGerenciar() {
  state.view = "gerenciar"; state.qid = null; state.P = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando…</div>`;
  const G = await api("/api/perigo"), P = G.projeto;
  const comAlgo = G.perguntas.filter((q) => q.frame || q.codificacao);
  const opts = (filtro) => G.perguntas.filter(filtro).map((q) => `<option value="${esc(q.qid)}">${esc(q.qid)} · ${esc(q.rotulo)}${q.codificacao ? ` (${q.n_codificadas} classificadas)` : q.frame ? " (só categorias)" : ""}</option>`).join("");
  $("#main").innerHTML = `
    <h1>Gerenciar projeto <small>${esc(P.nome)}</small></h1>
    ${G.modo_teste ? `<div class="aviso">🧪 Modo teste ligado: as ações abaixo valem só para os dados de <b>teste</b> (${esc(P.saida)}).</div>` : ""}
    <table class="res"><tbody>
      <tr><td><b>Pasta do projeto</b><br><small>planilha-fonte e configuração (nunca é apagada por aqui)</small></td><td colspan="2"><code>${esc(P.pasta)}</code></td></tr>
      <tr><td><b>Pasta de resultados</b><br><small>categorias, classificações, arquivos gerados</small></td><td><code>${esc(P.saida)}</code></td><td class="acoes"><button class="btn sm" data-acao="pasta">📂 Abrir</button></td></tr>
      <tr><td><b>Lixeira</b><br><small>tudo o que for apagado aqui vai para ela e pode ser recuperado</small></td><td><code>${esc(G.lixeira)}</code> <small>(${G.n_lixeira} item(ns))</small></td><td></td></tr>
    </tbody></table>

    <h2>Base e planilha</h2>
    <div class="info">Ação usada quando chega base nova (mais entrevistas) ou quando a planilha-fonte é corrigida — por isso fica aqui, e não no topo da tela.</div>
    <div class="perigo-zona"><div class="cab">Atualizar a base</div>
      <div class="perigo-item"><div class="d"><b>↻ Recarregar planilha</b><small>Relê a planilha-fonte e reconstrói a base. O que já foi classificado e conferido continua nas mesmas respostas (casamento pelo texto); perguntas aprovadas que ganharem respostas novas voltam para revisão.</small></div>
        <button class="btn" id="gz-load">Recarregar planilha</button></div>
    </div>

    <h2 style="color:var(--danger)">⚠ Zona de perigo</h2>
    <div class="perigo-zona"><div class="cab">Categorias e classificações</div>
      <div class="perigo-item"><div class="d"><b>Apagar a classificação de uma pergunta</b><small>Mantém as categorias (aprovadas). As respostas voltam a “não classificadas”, inclusive o que foi conferido por pessoas. Sai da base e dos resultados.</small></div>
        <select id="pz-q1">${opts((q) => q.codificacao) || "<option value=''>nenhuma pergunta classificada</option>"}</select>
        <button class="btn perigo-out" id="pz-b1" ${G.perguntas.some((q) => q.codificacao) ? "" : "disabled"}>Apagar classificação</button></div>
      <div class="perigo-item"><div class="d"><b>Apagar categorias e classificação de uma pergunta</b><small>A pergunta volta ao início (“gerar categorias com IA”). As instruções escritas para a IA são mantidas.</small></div>
        <select id="pz-q2">${opts((q) => q.frame || q.codificacao) || "<option value=''>nenhuma pergunta com categorias</option>"}</select>
        <button class="btn perigo-out" id="pz-b2" ${comAlgo.length ? "" : "disabled"}>Apagar categorias</button></div>
      <div class="perigo-item"><div class="d"><b>Recomeçar todas as perguntas</b><small>Apaga categorias e classificações de <b>todas</b> as ${G.perguntas.length} perguntas (${comAlgo.length} com trabalho feito). A base lida da planilha é mantida.</small></div>
        <button class="btn perigo" id="pz-b3" ${comAlgo.length ? "" : "disabled"}>Recomeçar tudo</button></div>
    </div>
    <div class="perigo-zona"><div class="cab">Projeto</div>
      <div class="perigo-item"><div class="d"><b>⧉ Criar uma cópia deste projeto</b><small>Duplica a pasta (configuração e planilha) com outro nome e cadastra na lista. Você escolhe se leva junto as categorias e classificações já feitas. O original não muda.</small></div>
        <button class="btn" id="pz-copia">Criar cópia</button></div>
      <div class="perigo-item"><div class="d"><b>Excluir este projeto do Tabulador</b><small>Tira “${esc(P.nome)}” da lista de projetos. A pasta do projeto e a planilha não são apagadas (dá para cadastrar de novo). Opcionalmente, move a pasta de resultados para <code>…_excluido_&lt;data&gt;</code>.</small></div>
        <button class="btn perigo" id="pz-b4" ${G.n_projetos > 1 ? "" : 'disabled title="É o único projeto: crie outro antes"'}>Excluir projeto</button></div>
    </div>`;
  document.querySelector("[data-acao=pasta]").onclick = () => post("/api/abrir-pasta");
  $("#gz-load").onclick = recarregarPlanilha;  // veio do topo: ação de base, usada de vez em quando
  const apagar = async (qids, o_que, rotulo) => {
    const r = await post("/api/perigo/pergunta", { qids, o_que }, "Apagando…");
    toast(r.lixeira ? `${rotulo} — movido para a lixeira` : "Nada para apagar");
    await carregarStatus(); renderGerenciar();
  };
  const nomeQ = (qid) => { const q = G.perguntas.find((x) => x.qid === qid); return q ? `${q.qid} · ${q.rotulo}` : qid; };
  $("#pz-b1").onclick = async () => {
    const qid = $("#pz-q1").value; if (!qid) return;
    if (await confirmarPerigo({ titulo: "Apagar classificação", texto: `Apagar a classificação de <b>${esc(nomeQ(qid))}</b>? As categorias ficam; as respostas voltam a “não classificadas”, inclusive as conferidas. Os arquivos vão para a lixeira.`, palavra: "APAGAR" }))
      apagar([qid], "classificacao", "Classificação apagada");
  };
  $("#pz-b2").onclick = async () => {
    const qid = $("#pz-q2").value; if (!qid) return;
    if (await confirmarPerigo({ titulo: "Apagar categorias e classificação", texto: `A pergunta <b>${esc(nomeQ(qid))}</b> volta ao início: categorias e classificação vão para a lixeira.`, palavra: "APAGAR" }))
      apagar([qid], "tudo", "Categorias e classificação apagadas");
  };
  $("#pz-b3").onclick = async () => {
    if (await confirmarPerigo({ titulo: "Recomeçar todas as perguntas", texto: `Categorias e classificações de <b>todas as ${G.perguntas.length} perguntas</b> de “${esc(P.nome)}” vão para a lixeira.`, palavra: "RECOMEÇAR", botao: "Recomeçar tudo" }))
      apagar("todas", "tudo", "Todas as perguntas recomeçadas");
  };
  $("#pz-copia").onclick = async () => {
    const dlg = $("#dlg-janela");
    abrirJanela("Criar cópia do projeto", `<div class="small-t">Cópia de “<b>${esc(P.nome)}</b>”.</div>
      <label class="campo">Nome da cópia <input id="cp-nome" autocomplete="off" value="${esc(P.nome)} (cópia)"></label>
      <label><input type="checkbox" id="cp-res"> Copiar também categorias e classificações já feitas</label>
      <div class="small muted">Sem isto, a cópia começa limpa: é só recarregar a planilha.</div>
      <div class="dlg-acoes"><button class="btn primary" id="cp-ok">Criar cópia</button></div>`);
    $("#cp-ok").onclick = async () => {
      const nome = $("#cp-nome").value.trim(); if (!nome) return;
      const j = await post("/api/projeto/copiar", { slug: P.slug, nome, copiar_resultados: $("#cp-res").checked }, "Copiando o projeto…");
      dlg.close(); toast(`Cópia “${j.nome}” criada`); await carregarStatus(); renderGerenciar();
    };
  };
  $("#pz-b4").onclick = async () => {
    const r = await confirmarPerigo({ titulo: "Excluir projeto", palavra: P.nome, botao: "Excluir projeto",
      texto: `“<b>${esc(P.nome)}</b>” sai da lista de projetos. A pasta do projeto (<code>${esc(P.pasta)}</code>) e a planilha <b>não</b> são apagadas.`,
      extra: `<label><input type="checkbox" id="pg-res"> Mover também a pasta de resultados para <code>…_excluido_&lt;data&gt;</code> (recuperável)</label>` });
    if (!r) return;
    const j = await post("/api/perigo/projeto", { slug: P.slug, confirmacao: P.nome, apagar_resultados: r.marcado }, "Excluindo o projeto…");
    toast(`Projeto excluído${j.resultados_movidos.length ? " — resultados movidos para " + j.resultados_movidos[0] : ""}`);
    state.qid = null; await carregarStatus(); irPara(null); renderPainel();
  };
}

// ---------------------------------------------------------------- topo: projeto, IA, planilha
// janela grande reaproveitável (resumo da base nova, aprovação por categoria…)
function abrirJanela(titulo, html) {
  const dlg = $("#dlg-janela");
  $("#jan-titulo").textContent = titulo; $("#jan-corpo").innerHTML = html;
  if (!dlg.open) dlg.showModal();
  return dlg;
}
async function recarregarPlanilha() {
  if (!confirm("Reler a planilha-fonte (por exemplo, uma versão nova da base)?\n\nO que já foi classificado e conferido continua valendo para as mesmas respostas. Respostas novas ficam para classificar, e perguntas aprovadas que ganharem respostas novas voltam para revisão.")) return;
  const r = await post("/api/load", {}, "Lendo a planilha…");
  await carregarStatus(); rota();
  const Q = Object.entries(r.perguntas || {});
  const dif = r.n_anterior == null ? "" : ` (antes: ${fmtN(r.n_anterior)}; ${r.n - r.n_anterior >= 0 ? "+" : ""}${fmtN(r.n - r.n_anterior)})`;
  const linhas = Q.map(([qid, m]) => `<tr><td><b>${esc(qid)}</b></td><td class="num">${fmtN(m.respondentes_novos)}</td><td class="num">${fmtN(m.unicas_novas)}</td>
    <td class="num">${m.sem_classificacao ? `<b>${fmtN(m.sem_classificacao)}</b>` : "0"}</td><td class="num">${fmtN(m.unicas_removidas)}</td>
    <td>${m.reaberta ? '<span class="pill warn">voltou para revisão</span>' : m.sem_classificacao ? '<span class="pill">classificar as novas</span>' : '<span class="pill ok">em dia</span>'}</td></tr>`).join("");
  abrirJanela("Base atualizada", `
    <p><b>${fmtN(r.n)} respondentes</b> na planilha${dif}. O que já tinha sido classificado e conferido continua nas mesmas respostas;
    respostas iguais a textos já classificados herdam a categoria sozinhas.</p>
    ${Q.length ? `<table class="mudancas"><thead><tr><th>Pergunta</th><th class="num">Respondentes novos</th><th class="num">Respostas diferentes novas</th><th class="num">Sem classificação</th><th class="num">Removidas</th><th></th></tr></thead><tbody>${linhas}</tbody></table>
    <p class="small">Para classificar as novas, abra a pergunta e use <b>Classificar as restantes</b>. Respostas removidas da base saem da classificação (ficam guardadas no arquivo, em "removidos").</p>` : ""}`);
}
// ---- modal "Configurar IA" (provedores compatíveis com a API da OpenAI)
function preencherProvedor(prov, inicial) {
  const ia = state.status.ia, P = ia.provedores[prov] || {}, atual = prov === ia.provedor;
  $("#ia-estado").innerHTML = P.cli
    ? (P.disponivel
      ? `💻 Usa o programa instalado neste computador, com o login/assinatura de quem usa — <b>sem chave</b>. É mais lento que a API (cada chamada abre o programa, ~5–10 s) e roda no máximo 2 chamadas ao mesmo tempo. As respostas vão para o provedor do programa, como numa conversa normal. Modelo "padrao" = o padrão do programa.`
      : `⚠ Este programa não foi encontrado neste computador. Instale-o e faça login nele antes (link ao lado).`)
    : P.sem_chave
    ? `🧪 Não usa chave nem internet: as categorias e classificações são <b>simuladas</b>, para testar o app sem custo. Os resultados vão para uma pasta separada.`
    : P.tem_chave
    ? `✓ Já existe uma chave guardada para este provedor. Cole outra só se quiser trocar.`
    : `⚠ Nenhuma chave guardada para este provedor — cole a chave para usá-lo.`;
  $("#ia-chave").closest("label").classList.toggle("hidden", !!P.sem_chave);
  $("#ia-modelo").closest("label").classList.toggle("hidden", !!P.sem_chave && !P.cli);
  $("#ia-chave-dica").textContent = P.chave_prefixo ? `(começa com ${P.chave_prefixo}…)` : "";
  $("#ia-link").classList.toggle("hidden", !P.link); $("#ia-link").href = P.link || "#";
  preencherModelos(P, atual && inicial ? ia.modelo : P.modelo || "");
  $("#ia-url").value = atual && inicial ? ia.base_url : P.base_url || "";
  $("#ia-url-campo").classList.toggle("hidden", prov !== "personalizado" && !(atual && inicial && ia.base_url && ia.base_url !== (P.base_url || "")));
  $("#ia-teste-res").textContent = ""; $("#ia-teste-detalhe").innerHTML = "";
}
// lista fixa de modelos do provedor + "outro…" (campo livre, para um modelo que não está na lista)
const OUTRO_MODELO = "__outro";
function preencherModelos(P, valor) {
  const lista = P.modelos || [], sel = $("#ia-modelo-sel");
  sel.innerHTML = lista.map((m) => `<option value="${esc(m)}">${m === "padrao" ? "padrão do programa" : esc(m)}${m === P.modelo ? " (recomendado)" : ""}</option>`).join("")
    + `<option value="${OUTRO_MODELO}">outro…</option>`;
  sel.value = lista.length && (!valor || lista.includes(valor)) ? valor || lista[0] : OUTRO_MODELO;
  $("#ia-modelo").value = sel.value === OUTRO_MODELO ? valor || "" : sel.value;
  $("#ia-modelo").classList.toggle("hidden", sel.value !== OUTRO_MODELO);
}
$("#ia-modelo-sel").onchange = (e) => {
  const outro = e.target.value === OUTRO_MODELO, campo = $("#ia-modelo");
  campo.classList.toggle("hidden", !outro);
  if (outro) { campo.value = ""; campo.focus(); } else campo.value = e.target.value;
};
function abrirIA() {
  const ia = state.status.ia;
  $("#ia-provedor").innerHTML = Object.entries(ia.provedores).map(([k, p]) => `<option value="${k}" ${k === ia.provedor ? "selected" : ""} ${p.disponivel === false ? "disabled" : ""}>${esc(p.nome)}${p.disponivel === false ? " (não instalado)" : p.tem_chave && !p.cli ? " ✓" : ""}</option>`).join("");
  $("#ia-chave").value = ""; preencherProvedor(ia.provedor, true);
  $("#dlg-ia").showModal();
}
$("#ia-provedor").onchange = (e) => preencherProvedor(e.target.value, false);
function lerFormIA() {
  const provedor = $("#ia-provedor").value, P = state.status.ia.provedores[provedor];
  const chave = $("#ia-chave").value.trim(), modelo = $("#ia-modelo").value.trim(), base_url = $("#ia-url").value.trim();
  if (!chave && !P.tem_chave) throw new Error("Cole a chave deste provedor.");
  if (!modelo) throw new Error("Informe o modelo.");
  if (provedor === "personalizado" && !base_url) throw new Error("Informe o endereço da API.");
  if (chave && P.chave_prefixo && !chave.startsWith(P.chave_prefixo) && !confirm(`Chaves deste provedor costumam começar com "${P.chave_prefixo}". Usar mesmo assim?`)) throw new Error("cancelado");
  return { provedor, chave, modelo, base_url };
}
async function salvarIA() {
  const form = lerFormIA();
  const r = form.provedor === "simulado"
    ? await post("/api/modo-teste", { ativo: true })  // guarda o provedor atual para restaurar ao sair
    : await post("/api/config", form);
  state.status.ia = { ...state.status.ia, ...r }; $("#ia-chave").value = "";
  return r;
}
$("#form-ia").addEventListener("submit", async (e) => {
  if (e.submitter?.value !== "ok") return;
  e.preventDefault();
  try { await salvarIA(); } catch (err) { if (err.message !== "cancelado") toast(err.message, true); return; }
  $("#dlg-ia").close(); toast("Configuração da IA salva"); state.qid = null; await carregarStatus(); rota();  // modo teste troca a pasta: recarrega a tela
});
$("#ia-testar").onclick = async () => {
  const res = $("#ia-teste-res"), det = $("#ia-teste-detalhe"), btn = $("#ia-testar");
  try { await salvarIA(); } catch (err) { if (err.message !== "cancelado") toast(err.message, true); return; }
  res.textContent = "⏳ testando… (programas instalados levam ~5–10 s)"; det.innerHTML = ""; btn.disabled = true;
  let r;
  try { r = await post("/api/config/testar", {}); }
  catch (err) {  // o servidor nem respondeu (ou devolveu erro fora do padrão)
    r = { ok: false, erro: err.message, explicacao: "O teste não chegou a rodar: " + err.message,
          solucao: "Confira se a janela do Tabulador continua aberta; se não, abra-o pelo atalho e recarregue a página." };
  } finally { btn.disabled = false; }
  await carregarStatus(); preencherProvedor($("#ia-provedor").value, true);  // limpa o resultado; é preenchido logo abaixo
  mostrarTesteIA(r);
};
function mostrarTesteIA(r) {
  const res = $("#ia-teste-res"), det = $("#ia-teste-detalhe");
  const quem = `${esc(r.provedor_nome || r.provedor || "")} · modelo <b>${esc(r.modelo || "?")}</b>`;
  if (r.ok) {
    res.innerHTML = `<span class="pill ok">✓ funcionou (${esc(r.modelo)} · ${r.segundos} s)</span>`;
    det.innerHTML = `<div class="teste-ia ok"><div>✅ <b>Conexão confirmada.</b> A IA respondeu corretamente em ${r.segundos} s. Pode salvar.</div><small>${quem}</small></div>`;
    return;
  }
  res.innerHTML = '<span class="pill warn">✗ falhou</span>';
  det.innerHTML = `<div class="teste-ia falhou">
    <div>❌ <b>O teste falhou.</b> <small>${quem}${r.segundos != null ? ` · ${r.segundos} s` : ""}</small></div>
    <div><b>O que aconteceu:</b> ${esc(r.explicacao || r.erro || "erro desconhecido")}</div>
    <div><b>Como resolver:</b> ${esc(r.solucao || "Confira a configuração e teste de novo.")}</div>
    ${r.erro ? `<details><summary>Mensagem original</summary><pre>${esc(r.erro)}</pre></details>` : ""}</div>`;
}

// ---------------------------------------------------------------- consumo da IA
const fmtN = (n) => (n == null ? "–" : Number(n).toLocaleString("pt-BR"));
const fmtUSD = (v) => (v == null ? "–" : "US$ " + Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: v < 1 ? 4 : 2 }));
const fmtBRL = (v) => (v == null ? "–" : Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }));
const fmtTempo = (s) => (s < 90 ? `${Math.round(s)} s` : s < 5400 ? `${(s / 60).toFixed(1).replace(".", ",")} min` : `${(s / 3600).toFixed(1).replace(".", ",")} h`);
// número grande e legível: 159.972 -> "160 mil"; 1.284.000 -> "1,3 mi"
const fmtCompacto = (n) => {
  if (n == null) return "–";
  const um = (v, suf) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: v < 10 ? 1 : 0 })} ${suf}`;
  if (n >= 1e6) return um(n / 1e6, "mi");
  if (n >= 1e3) return um(n / 1e3, "mil");
  return fmtN(n);
};
const USO_MODOS = { pergunta: "Por pergunta", modelo: "Por modelo", dia: "Por dia" };
function usoModo() { try { return localStorage.getItem("uso-modo") || "pergunta"; } catch { return "pergunta"; } }

// linhas do gráfico conforme o modo; mais de 8 itens: o resto vira "Outros"
function usoLinhas(U, modo) {
  let L;
  if (modo === "modelo") L = U.por_modelo.map((r) => ({ ...r, rotulo: r.modelo }));
  else if (modo === "dia") L = [...U.por_dia].reverse().map((r) => ({ ...r, rotulo: r.dia }));
  else L = U.por_pergunta.map((r) => ({ ...r, rotulo: r.pergunta === "—" ? r.operacao : `${r.pergunta} · ${r.operacao}` }));
  L = L.filter((r) => r.total > 0);
  if (modo !== "dia" && L.length > 8) {
    const resto = L.slice(7), soma = (k) => resto.reduce((s, r) => s + (r[k] || 0), 0);
    L = [...L.slice(0, 7), { rotulo: `Outros (${resto.length})`, total: soma("total"), chamadas: soma("chamadas"), prompt: soma("prompt"),
                              completion: soma("completion"), usd: soma("usd"), brl: soma("brl"), erros: soma("erros") }];
  }
  return L;
}

function desenharGraficoUso(U, modo) {
  const alvo = $("#u-grafico"), L = usoLinhas(U, modo), max = Math.max(1, ...L.map((r) => r.total));
  $("#u-grafico-titulo").textContent = `Tokens ${USO_MODOS[modo].toLowerCase()}`;
  const tip = $("#u-tip");  // o tooltip é reaproveitado entre os redesenhos
  tip.classList.add("hidden");
  alvo.replaceChildren(tip);
  if (!L.length) { alvo.insertAdjacentHTML("afterbegin", `<div class="small">Nenhuma chamada registrada ainda.</div>`); return; }
  for (const r of L) {
    const linha = document.createElement("div");
    linha.className = "u-barra"; linha.tabIndex = 0;
    const nome = document.createElement("span"); nome.className = "n"; nome.textContent = r.rotulo; nome.title = r.rotulo;
    const trilho = document.createElement("span"); trilho.className = "t";
    const barra = document.createElement("i"); barra.style.width = `${Math.max(0.6, (100 * r.total) / max)}%`;
    trilho.appendChild(barra);
    const valor = document.createElement("span"); valor.className = "v"; valor.textContent = fmtCompacto(r.total);
    linha.append(nome, trilho, valor);
    const mostrar = (x, y) => {
      tip.replaceChildren();
      const v = document.createElement("b"); v.textContent = `${fmtN(r.total)} tokens`;
      const n = document.createElement("div"); n.className = "tn"; n.textContent = r.rotulo;
      const d = document.createElement("div"); d.className = "td";
      d.textContent = `${fmtN(r.chamadas)} chamada${r.chamadas === 1 ? "" : "s"} · ${fmtN(r.prompt)} entrada · ${fmtN(r.completion)} saída · ${fmtBRL(r.brl)}`;
      tip.append(v, n, d);
      tip.classList.remove("hidden");
      const caixa = alvo.getBoundingClientRect();
      tip.style.left = `${Math.min(x - caixa.left + 12, caixa.width - tip.offsetWidth)}px`;
      tip.style.top = `${y - caixa.top + 14}px`;
    };
    linha.addEventListener("pointermove", (e) => mostrar(e.clientX, e.clientY));
    linha.addEventListener("focus", () => { const b = linha.getBoundingClientRect(); mostrar(b.left + b.width / 3, b.bottom - 6); });
    linha.addEventListener("pointerleave", () => tip.classList.add("hidden"));
    linha.addEventListener("blur", () => tip.classList.add("hidden"));
    alvo.insertBefore(linha, tip);
  }
}

// ---- consumo ao longo do tempo (gráfico de linha com períodos, como o de uma ação)
const USO_PERIODOS = { "24h": "24 horas", "7d": "7 dias", "30d": "30 dias", "90d": "3 meses", tudo: "Tudo" };
const USO_METRICAS = { total: "Tokens", brl: "Custo (R$)", chamadas: "Chamadas" };
const lerPref = (k, pad, ok) => { try { const v = localStorage.getItem(k); return v && ok[v] ? v : pad; } catch { return pad; } };
const gravarPref = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sem armazenamento: só não lembra */ } };
const USO_CAMPOS = ["chamadas", "ok", "erros", "prompt", "completion", "total", "sem_preco", "cls", "segundos", "usd"];
const usoZero = () => Object.fromEntries(USO_CAMPOS.map((k) => [k, 0]));
const usoSoma = (acc, r) => { for (const k of USO_CAMPOS) acc[k] += r[k] || 0; return acc; };
const dataHora = (h) => new Date(+h.slice(0, 4), +h.slice(5, 7) - 1, +h.slice(8, 10), +h.slice(11, 13));
const inicioDia = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
const somaDias = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
const fmtDia = (d) => d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });

// agrupa a série por hora (24 h) ou por dia/semana (demais períodos) e soma o período anterior equivalente
function usoJanela(U, per) {
  const serie = U.serie_hora.map((r) => ({ ...r, t: dataHora(r.h) })), agora = new Date();
  let passo, ini, n;
  if (per === "24h") {
    passo = (d, k) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours() + k);
    const h = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate(), agora.getHours());
    n = 24; ini = passo(h, -23);
  } else {
    const hoje = inicioDia(agora);
    const dias = per === "tudo" ? (serie.length ? Math.round((hoje - inicioDia(serie[0].t)) / 864e5) + 1 : 1) : { "7d": 7, "30d": 30, "90d": 90 }[per];
    const sem = dias > 120;  // muito tempo: pontos semanais
    passo = (d, k) => somaDias(d, k * (sem ? 7 : 1));
    n = sem ? Math.ceil(dias / 7) : dias; ini = passo(somaDias(hoje, 1), -n);
  }
  const pontos = Array.from({ length: n }, (_, i) => ({ ini: passo(ini, i), fim: passo(ini, i + 1), ...usoZero() }));
  const fim = passo(ini, n), antIni = per === "tudo" ? null : passo(ini, -n), ant = usoZero();
  let i = 0;
  for (const r of serie) {
    if (r.t >= ini && r.t < fim) { while (pontos[i + 1] && r.t >= pontos[i + 1].ini) i++; usoSoma(pontos[i], r); }
    else if (antIni && r.t >= antIni && r.t < ini) usoSoma(ant, r);
  }
  const tot = pontos.reduce(usoSoma, usoZero());
  const rot = (p) => per === "24h" ? `${String(p.ini.getHours()).padStart(2, "0")}h` : fmtDia(p.ini);
  const rotLongo = (p) => per === "24h" ? `${fmtDia(p.ini)} das ${rot(p)} às ${String(p.fim.getHours()).padStart(2, "0")}h`
    : (p.fim - p.ini > 2 * 864e5 ? `semana de ${fmtDia(p.ini)} a ${fmtDia(somaDias(p.fim, -1))}` : p.ini.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" }));
  return { pontos: pontos.map((p) => ({ ...p, rot: rot(p), rotLongo: rotLongo(p) })), tot, ant: antIni ? ant : null,
           unidade: per === "24h" ? "hora" : pontos.length && pontos[0].fim - pontos[0].ini > 2 * 864e5 ? "semana" : "dia" };
}

const valorMetrica = (p, met, cambio) => (met === "brl" ? p.usd * cambio : p[met]);
const fmtMetrica = (v, met) => (met === "brl" ? fmtBRL(v) : met === "total" ? fmtCompacto(v) : fmtN(v));
function escalaBonita(max) {  // topo do eixo e 4 divisões "redondas"
  if (max <= 0) return { topo: 1, passo: 0.25 };
  const bruto = max / 4, mag = 10 ** Math.floor(Math.log10(bruto)), n = bruto / mag;
  const passo = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * mag;
  return { topo: passo * Math.ceil(max / passo), passo };
}

function desenharLinhaUso(U, J, met) {
  const alvo = $("#u-linha"), tip = $("#u-ltip"), NS = "http://www.w3.org/2000/svg";
  const el = (tag, at = {}) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(at)) e.setAttribute(k, v); return e; };
  const P = J.pontos, vals = P.map((p) => valorMetrica(p, met, U.cambio));
  const W = Math.max(280, alvo.clientWidth), H = 230, m = { l: 52, r: 14, t: 14, b: 28 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
  const { topo, passo } = escalaBonita(Math.max(...vals));
  const x = (i) => m.l + (P.length === 1 ? iw / 2 : (i * iw) / (P.length - 1)), y = (v) => m.t + ih - (v / topo) * ih;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", tabindex: 0,
    "aria-label": `${USO_METRICAS[met]} por ${J.unidade}: ${P.length} pontos; use as setas para percorrer` });
  const defs = el("defs"), grad = el("linearGradient", { id: "u-area-g", x1: 0, x2: 0, y1: 0, y2: 1 });
  grad.append(el("stop", { offset: "0%", class: "u-area-a" }), el("stop", { offset: "100%", class: "u-area-b" }));
  defs.append(grad); svg.append(defs);
  for (let v = 0; v <= topo + 1e-9; v += passo) {  // grade recessiva + rótulos do eixo
    svg.append(el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), class: v === 0 ? "u-base" : "u-grade" }));
    const t = el("text", { x: m.l - 8, y: y(v) + 4, class: "u-eixo", "text-anchor": "end" }); t.textContent = fmtMetrica(v, met); svg.append(t);
  }
  const cada = Math.max(1, Math.ceil(P.length / Math.max(2, Math.floor(iw / 70))));
  P.forEach((p, i) => { if (i % cada === 0 || i === P.length - 1) {
    const t = el("text", { x: x(i), y: H - 8, class: "u-eixo", "text-anchor": i === 0 ? "start" : i === P.length - 1 ? "end" : "middle" });
    t.textContent = p.rot; svg.append(t);
  } });
  const linha = P.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(vals[i]).toFixed(1)}`).join("");
  svg.append(el("path", { d: `${linha}L${x(P.length - 1)},${y(0)}L${x(0)},${y(0)}Z`, class: "u-area" }), el("path", { d: linha, class: "u-traco" }));
  const iUlt = vals.findLastIndex((v) => v > 0);  // destaca o último ponto com uso
  if (iUlt >= 0) svg.append(el("circle", { cx: x(iUlt), cy: y(vals[iUlt]), r: 4, class: "u-ponto" }));
  const mira = el("line", { y1: m.t, y2: m.t + ih, class: "u-mira hidden" }), foco = el("circle", { r: 5, class: "u-ponto u-foco hidden" });
  svg.append(mira, foco);
  alvo.replaceChildren(svg, tip);
  let atual = -1;
  const mostrar = (i) => {
    atual = i; const p = P[i];
    mira.setAttribute("x1", x(i)); mira.setAttribute("x2", x(i)); foco.setAttribute("cx", x(i)); foco.setAttribute("cy", y(vals[i]));
    mira.classList.remove("hidden"); foco.classList.remove("hidden");
    tip.replaceChildren();
    const v = document.createElement("b"); v.textContent = met === "brl" ? fmtBRL(vals[i]) : `${fmtN(vals[i])} ${met === "total" ? "tokens" : vals[i] === 1 ? "chamada" : "chamadas"}`;
    const n = document.createElement("div"); n.className = "tn"; n.textContent = p.rotLongo;
    const d = document.createElement("div"); d.className = "td";
    d.textContent = p.chamadas ? `${fmtN(p.chamadas)} chamada${p.chamadas === 1 ? "" : "s"} · ${fmtCompacto(p.total)} tokens · ${fmtBRL(p.usd * U.cambio)}${p.erros ? ` · ${p.erros} erro${p.erros > 1 ? "s" : ""}` : ""}` : "sem uso da IA";
    tip.append(v, n, d); tip.classList.remove("hidden");
    const esq = x(i) + 12 + tip.offsetWidth > W ? x(i) - 12 - tip.offsetWidth : x(i) + 12;
    tip.style.left = `${Math.max(0, esq)}px`; tip.style.top = `${Math.max(0, Math.min(y(vals[i]) - 20, H - tip.offsetHeight))}px`;
  };
  const esconder = () => { atual = -1; tip.classList.add("hidden"); mira.classList.add("hidden"); foco.classList.add("hidden"); };
  svg.addEventListener("pointermove", (e) => {
    const b = svg.getBoundingClientRect(), px = ((e.clientX - b.left) * W) / b.width;
    mostrar(Math.max(0, Math.min(P.length - 1, Math.round(P.length === 1 ? 0 : ((px - m.l) * (P.length - 1)) / iw))));
  });
  svg.addEventListener("pointerleave", esconder); svg.addEventListener("blur", esconder);
  svg.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault(); mostrar(Math.max(0, Math.min(P.length - 1, (atual < 0 ? P.length : atual) + (e.key === "ArrowRight" ? 1 : -1))));
  });
}

// ---- eficiência e conquistas (usa as perguntas de /api/resultados)
function usoEficiencia(U, R) {
  const tudo = U.serie_hora.reduce(usoSoma, usoZero()), Q = R ? R.perguntas : [];
  const soma = (k) => Q.reduce((a, q) => a + (q[k] || 0), 0);
  // quem conferiu (de usage.py): pessoas separadas do aceite automático e das sugestões do auditor
  const CF_ = Object.values(U.conferencia || {}).reduce((a, c) => { for (const [k, v] of Object.entries(c)) a[k] = (a[k] || 0) + v; return a; }, {});
  const auto = CF_.confirmadas_auto || 0, adotadas = CF_.sugestoes_adotadas || 0, auditadas = CF_.auditadas || 0;
  const cod = soma("n_codificadas"), aprov = Q.filter((q) => q.codificacao === "aprovado").length;
  const rev = U.conferencia ? (CF_.confirmadas_humano || 0) + (CF_.corrigidas_humano || 0) : soma("n_revisadas");
  const aval = soma("n_avaliadas_ia"), acerto = aval ? Q.reduce((a, q) => a + (q.acerto_ia || 0) * (q.n_avaliadas_ia || 0), 0) / aval : null;
  const medalha = (v, ouro, prata, menorMelhor = false) => v == null ? null
    : (menorMelhor ? v <= ouro : v >= ouro) ? { ic: "🥇", nome: "ouro", cls: "ouro" } : (menorMelhor ? v <= prata : v >= prata) ? { ic: "🥈", nome: "prata", cls: "prata" } : { ic: "🥉", nome: "bronze", cls: "bronze" };
  const aprovadas = new Set(Q.filter((q) => q.codificacao === "aprovado").map((q) => q.qid));
  const tokAprov = U.por_pergunta.filter((r) => aprovadas.has(r.pergunta)).reduce((a, r) => a + r.total, 0);
  const tokResp = cod && tudo.cls ? tudo.cls / cod : null, mil = cod ? (1000 * tudo.usd * U.cambio) / cod : null;
  const cards = [
    { ic: "🎯", t: "Acerto da IA", v: acerto == null ? "–" : `${Math.round(100 * acerto)}%`, d: aval ? `nas ${fmtN(aval)} respostas conferidas por pessoas` : "confira algumas respostas para medir", m: aval >= 10 ? medalha(acerto, 0.9, 0.75) : null },
    { ic: "🔤", t: "Tokens por resposta", v: tokResp == null ? "–" : fmtN(Math.round(tokResp)), d: "gastos classificando, por resposta classificada · menor é melhor", m: medalha(tokResp, 150, 400, true) },
    { ic: "💰", t: "Custo por 1.000 respostas", v: mil == null ? "–" : fmtBRL(mil), d: "custo total da IA ÷ respostas classificadas", m: null },
    { ic: "🏁", t: "Tokens por pergunta aprovada", v: aprov ? fmtCompacto(tokAprov / aprov) : "–", d: aprov ? `${aprov} pergunta${aprov > 1 ? "s" : ""} aprovada${aprov > 1 ? "s" : ""}` : "nenhuma pergunta aprovada ainda", m: null },
    { ic: "👀", t: "Conferência humana", v: cod ? pct(rev, cod) : "–", d: `${fmtN(rev)} de ${fmtN(cod)} classificadas conferidas por pessoas (sem as automáticas)`, m: cod ? medalha(rev / cod, 0.3, 0.1) : null },
    { ic: "⚡", t: "Supervisão por IA", v: fmtN(auto), d: `confirmadas sozinhas (confiança alta + auditor concordou) · ${fmtN(auditadas)} auditadas · ${fmtN(adotadas)} sugestões do auditor adotadas`, m: null },
  ];
  const semana = usoJanela(U, "7d").tot;
  const conquistas = [
    { ic: "🚀", t: "Decolagem", d: "primeira chamada à IA", v: Math.min(tudo.chamadas, 1), de: 1 },
    { ic: "📚", t: "Mil respostas", d: "1.000 respostas classificadas", v: Math.min(cod, 1000), de: 1000 },
    { ic: "🔍", t: "Olho clínico", d: "100 respostas conferidas por pessoas", v: Math.min(rev, 100), de: 100 },
    { ic: "🎯", t: "Na mosca", d: "IA com 90% de acerto (mín. 30 conferidas)", v: aval >= 30 ? Math.min(acerto / 0.9, 1) : 0, de: 1, txt: aval >= 30 ? `${Math.round(100 * acerto)}% de 90%` : `${aval} de 30 conferidas` },
    { ic: "🏁", t: "Primeira aprovada", d: "uma pergunta aprovada", v: Math.min(aprov, 1), de: 1 },
    { ic: "🏆", t: "Projeto fechado", d: "todas as perguntas aprovadas", v: aprov, de: Math.max(1, Q.length) },
    { ic: "🧹", t: "Semana limpa", d: "7 dias com uso e sem nenhum erro", v: semana.chamadas && !semana.erros ? 1 : 0, de: 1, txt: semana.erros ? `${semana.erros} erro(s) nos últimos 7 dias` : semana.chamadas ? "" : "sem uso nos últimos 7 dias" },
  ];
  // XP: cada resposta classificada vale 1, cada conferida 5 e cada pergunta aprovada 100
  const xp = cod + 5 * rev + 100 * aprov, nivel = Math.floor(Math.sqrt(xp / 50)) + 1;
  const base = 50 * (nivel - 1) ** 2, prox = 50 * nivel ** 2;
  return { cards, conquistas, xp, nivel, base, prox, temPerguntas: !!R };
}

function htmlEficiencia(E) {
  const card = (c) => `<div class="u-ef"><div class="u-ef-ic" aria-hidden="true">${c.ic}</div><div class="u-ef-c">
      <div class="l">${esc(c.t)}</div><div class="v">${esc(c.v)}${c.m ? ` <span class="u-medalha ${c.m.cls}" title="nível ${c.m.nome}">${c.m.ic} ${c.m.nome}</span>` : ""}</div>
      <div class="d">${esc(c.d)}</div></div></div>`;
  const conq = (c) => {
    const feito = c.v >= c.de;
    return `<li class="u-cq ${feito ? "feito" : ""}" title="${esc(c.d)}"><span class="ic" aria-hidden="true">${c.ic}</span>
      <div><b>${esc(c.t)}</b> ${feito ? '<span class="u-ok">✓ conquistada</span>' : ""}<small>${esc(c.d)}</small>
      ${feito ? "" : `<div class="prog"><i style="width:${(100 * c.v) / c.de}%"></i></div><small class="u-cq-p">${esc(c.txt ?? `${fmtN(Math.floor(c.v))} de ${fmtN(c.de)}`)}</small>`}</div></li>`;
  };
  const feitas = E.conquistas.filter((c) => c.v >= c.de).length;
  return `
    <section class="u-sec">
      <div class="u-sec-cab"><h2>Eficiência <small>desde o início do projeto</small></h2>
        <div class="u-nivel" title="XP: +1 por resposta classificada, +5 por conferida, +100 por pergunta aprovada">
          <span class="u-nivel-n">Nível ${E.nivel}</span><div class="prog"><i style="width:${(100 * (E.xp - E.base)) / (E.prox - E.base)}%"></i></div>
          <small>${fmtN(E.xp)} XP · faltam ${fmtN(E.prox - E.xp)} para o nível ${E.nivel + 1}</small></div></div>
      ${E.temPerguntas ? "" : `<div class="small">Não consegui ler as perguntas do projeto; os números por resposta não aparecem.</div>`}
      <div class="u-efs">${E.cards.map(card).join("")}</div>
    </section>
    <section class="u-sec">
      <div class="u-sec-cab"><h2>Conquistas <small>${feitas} de ${E.conquistas.length}</small></h2></div>
      <ul class="u-cqs">${E.conquistas.map(conq).join("")}</ul>
    </section>`;
}

async function renderUsage() {
  state.view = "usage"; state.qid = null; state.P = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando consumo…</div>`;
  const [U, R] = await Promise.all([api("/api/usage?ultimas=200"), api("/api/resultados").catch(() => null)]);
  const T = U.total, modo = usoModo();
  let per = lerPref("uso-periodo", "7d", USO_PERIODOS), met = lerPref("uso-metrica", "total", USO_METRICAS);
  const linha = (r, primeira) => `<tr><td>${primeira}</td><td class="num">${fmtN(r.chamadas)}${r.erros ? ` <small class="warn-t">(${r.erros} erro${r.erros > 1 ? "s" : ""})</small>` : ""}</td><td class="num">${fmtN(r.prompt)}</td><td class="num">${fmtN(r.completion)}</td><td class="num"><b>${fmtN(r.total)}</b></td><td class="num">${fmtTempo(r.segundos)}</td><td class="num">${fmtUSD(r.usd)}</td><td class="num">${fmtBRL(r.brl)}</td></tr>`;
  const cab = (p) => `<thead><tr><th>${p}</th><th class="num">Chamadas</th><th class="num">Tokens entrada</th><th class="num">Tokens saída</th><th class="num">Total</th><th class="num">Tempo</th><th class="num">Custo (US$)</th><th class="num">Custo (R$)</th></tr></thead>`;
  const vazio = `<tr><td colspan="8" class="small">—</td></tr>`;
  const L = U.limite_diario, seg = (id, opcoes, on) => `<div class="seg" role="tablist" id="${id}">${Object.entries(opcoes).map(([k, v]) => `<button class="${k === on ? "on" : ""}" data-k="${k}" role="tab" aria-selected="${k === on}">${v}</button>`).join("")}</div>`;
  const energia = L.limite
    ? `<div class="u-energia" title="${esc(L.nome_provedor)} · limite diário estimado do plano gratuito">
         <div class="l">⚡ Energia do dia <small>${esc(L.nome_provedor.split(" (")[0])}</small></div>
         <div class="u-bat ${L.pct >= 80 ? "baixa" : ""}"><i style="width:${Math.max(0, 100 - L.pct)}%"></i></div>
         <small>${fmtN(L.usado_hoje)} de ${fmtN(L.limite)} chamadas hoje · restam ${fmtN(Math.max(0, L.limite - L.usado_hoje))}</small></div>`
    : `<div class="u-energia"><div class="l">⚡ Energia do dia <small>${esc(L.nome_provedor.split(" (")[0])}</small></div><small>${fmtN(L.usado_hoje)} chamada${L.usado_hoje === 1 ? "" : "s"} hoje · sem limite diário conhecido</small></div>`;
  $("#main").innerHTML = `
    <div class="small"><a href="#painel">← Painel geral</a></div>
    <h1>Consumo da IA <small>${esc(U.projeto)}</small></h1>
    <div class="u-filtros">
      ${seg("u-per", USO_PERIODOS, per)}
      ${seg("u-met", USO_METRICAS, met)}
      <button class="btn ghost" id="u-atualizar">↻ Atualizar</button>
    </div>
    <section class="u-hero">
      <div class="u-num" id="u-num"></div>
      <div class="u-graf">
        <div class="u-graf-cab" id="u-linha-titulo"></div>
        <div class="u-linha" id="u-linha"><div id="u-ltip" class="u-tip hidden" role="tooltip"></div></div>
        ${energia}
      </div>
    </section>
    ${htmlEficiencia(usoEficiencia(U, R))}
    <section class="u-sec">
      <div class="u-sec-cab"><h2 id="u-grafico-titulo"></h2><small class="small">desde o início · ${T.chamadas ? `${esc(T.primeira)} → ${esc(T.ultima)}` : "nenhuma chamada registrada ainda"}</small>
        <div class="seg" role="tablist" id="u-modo">${Object.entries(USO_MODOS).map(([k, v]) => `<button class="${k === modo ? "on" : ""}" data-modo="${k}" role="tab" aria-selected="${k === modo}">${v}</button>`).join("")}</div></div>
      <div class="u-grafico" id="u-grafico"><div id="u-tip" class="u-tip hidden" role="tooltip"></div></div>
    </section>
    <details class="u-detalhes">
      <summary>Tabelas detalhadas</summary>
      <h2>Por modelo</h2>
      <table class="usage">${cab("Modelo")}<tbody>${U.por_modelo.map((r) => linha(r, `<b>${esc(r.modelo)}</b>${r.preco ? `<br><small>US$ ${r.preco[0]} / ${r.preco[1]} por 1M tokens (entrada / saída)</small>` : "<br><small>sem preço de referência</small>"}`)).join("") || vazio}</tbody></table>
      <h2>Por pergunta e operação</h2>
      <table class="usage">${cab("Pergunta · operação")}<tbody>${U.por_pergunta.map((r) => linha(r, `<b>${esc(r.pergunta)}</b> · ${esc(r.operacao)}`)).join("") || vazio}</tbody></table>
      <h2>Por dia</h2>
      <table class="usage">${cab("Dia")}<tbody>${U.por_dia.map((r) => linha(r, `<b>${esc(r.dia)}</b>`)).join("") || vazio}</tbody></table>
      <h2>Chamadas recentes <small>(últimas ${U.ultimas.length})</small></h2>
      <div class="scroll-y"><table class="usage"><thead><tr><th>Quando</th><th>Pergunta · operação</th><th>Modelo</th><th class="num">Entrada</th><th class="num">Saída</th><th class="num">Tempo</th><th class="num">Custo (US$)</th><th>Situação</th></tr></thead><tbody>
        ${U.ultimas.map((c) => `<tr><td class="num">${esc(c.quando)}</td><td>${esc(c.pergunta)} · ${esc(c.operacao)}</td><td>${esc(c.modelo)}${c.provedor !== "openai" ? ` <small>(${esc(c.provedor)})</small>` : ""}</td><td class="num">${fmtN(c.prompt)}</td><td class="num">${fmtN(c.completion)}</td><td class="num">${c.segundos.toFixed(1).replace(".", ",")} s</td><td class="num">${fmtUSD(c.usd)}</td><td>${c.ok ? '<span class="pill ok">ok</span>' : `<span class="pill warn" title="${esc(c.erro || "")}">erro</span>`}</td></tr>`).join("") || vazio}
      </tbody></table></div>
    </details>`;

  // o período escolhido vale para os números do topo e para o gráfico de linha
  const desenharPeriodo = () => {
    const J = usoJanela(U, per), t = J.tot, outros = Math.max(0, t.total - t.prompt - t.completion), p = (v) => (t.total ? (100 * v) / t.total : 0);
    const dif = J.ant && J.ant.total ? (100 * (t.total - J.ant.total)) / J.ant.total : null;
    const delta = !J.ant ? "" : dif == null ? (t.total ? `<span class="u-delta">novo neste período</span>` : "")
      : `<span class="u-delta ${dif >= 0 ? "sobe" : "desce"}">${dif >= 0 ? "▲" : "▼"} ${Math.abs(dif).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}% vs. ${USO_PERIODOS[per]} anteriores</span>`;
    $("#u-num").innerHTML = `
      <div class="l">Tokens usados · ${per === "tudo" ? "desde o início" : `últimos ${USO_PERIODOS[per]}`}</div>
      <div class="big" title="${fmtN(t.total)} tokens">${fmtCompacto(t.total)}</div>
      <div class="exato">${fmtN(t.total)} tokens · ${fmtN(t.chamadas)} chamadas ${delta}</div>
      <div class="u-split" title="entrada ${fmtN(t.prompt)} · saída ${fmtN(t.completion)}${outros ? ` · raciocínio/cache ${fmtN(outros)}` : ""}">
        <i class="e" style="width:${p(t.prompt)}%"></i><i class="s" style="width:${p(t.completion)}%"></i>${outros ? `<i class="o" style="width:${p(outros)}%"></i>` : ""}</div>
      <div class="u-split-leg"><span><i class="e"></i><b>${fmtCompacto(t.prompt)}</b> entrada</span><span><i class="s"></i><b>${fmtCompacto(t.completion)}</b> saída</span>${outros ? `<span title="tokens que o provedor soma ao total além de entrada e saída (raciocínio do modelo, leitura de cache)"><i class="o"></i><b>${fmtCompacto(outros)}</b> raciocínio/cache</span>` : ""}</div>
      <dl class="u-mini">
        <div><dt>Custo estimado</dt><dd>${fmtBRL(t.usd * U.cambio)}</dd>
          <small class="u-param">US$ 1 = R$ ${U.cambio.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} · preços de referência em <code>usage.py</code>${t.sem_preco ? ` · ${t.sem_preco} chamada${t.sem_preco > 1 ? "s" : ""} sem preço` : ""}</small></div>
        <div><dt>Tempo de IA</dt><dd>${fmtTempo(t.segundos)}</dd></div>
        <div><dt>Sucesso</dt><dd>${t.chamadas ? Math.round((100 * t.ok) / t.chamadas) + "%" : "–"}</dd></div>
      </dl>`;
    $("#u-linha-titulo").textContent = `${USO_METRICAS[met]} por ${J.unidade}`;
    desenharLinhaUso(U, J, met);
  };
  desenharPeriodo();
  desenharGraficoUso(U, modo);
  const ligarSeg = (id, aoEscolher) => document.querySelectorAll(`#${id} button`).forEach((b) => (b.onclick = () => {
    document.querySelectorAll(`#${id} button`).forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-selected", x === b); });
    aoEscolher(b.dataset.k || b.dataset.modo);
  }));
  ligarSeg("u-per", (k) => { per = k; gravarPref("uso-periodo", k); desenharPeriodo(); });
  ligarSeg("u-met", (k) => { met = k; gravarPref("uso-metrica", k); desenharPeriodo(); });
  ligarSeg("u-modo", (k) => { gravarPref("uso-modo", k); desenharGraficoUso(U, k); });
  let tr; window.onresize = () => { clearTimeout(tr); tr = setTimeout(() => state.view === "usage" && $("#u-linha") && desenharLinhaUso(U, usoJanela(U, per), met), 150); };
  $("#u-atualizar").onclick = renderUsage;
}

// alturas reais dos cabeçalhos fixos (topo, q-cab e revbar): mantêm sticky sincronizado sem sobreposição
let roCab = null;
function medirAlturasFixas() {
  const topEl = $(".top");
  if (topEl) document.documentElement.style.setProperty("--topo", topEl.offsetHeight + "px");
  const qEl = $(".q-cab");
  if (qEl) document.documentElement.style.setProperty("--qcab-h", qEl.offsetHeight + "px");
  else document.documentElement.style.removeProperty("--qcab-h");
  const revEl = $(".revbar-sticky");
  if (revEl) document.documentElement.style.setProperty("--revbar-h", revEl.offsetHeight + "px");
  else document.documentElement.style.removeProperty("--revbar-h");
}
function observarCabecalho() {
  if (roCab) { roCab.disconnect(); roCab = null; }
  const qEl = $(".q-cab");
  if (qEl && window.ResizeObserver) {
    roCab = new ResizeObserver(() => medirAlturasFixas());
    roCab.observe(qEl);
  }
}
function medirTopo() { medirAlturasFixas(); }
window.addEventListener("resize", medirAlturasFixas);

// ---- modo teste (IA simulada)
function aplicarModoTeste() {
  const ia = state.status.ia, on = !!ia.modo_teste;
  document.body.classList.toggle("modo-teste", on);
  $("#faixa-teste").classList.toggle("hidden", !on);
  $("#faixa-pasta").textContent = ia.saida || "";
  $("#btn-teste").classList.toggle("on", on);
  $("#btn-teste").textContent = on ? "🧪 Modo teste: LIGADO" : "🧪 Modo teste";
}
async function alternarTeste(ativo) {
  if (ativo && !confirm("Ligar o modo teste?\n\n• A IA é substituída por valores SIMULADOS (sem internet e sem custo).\n• Tudo o que você fizer vai para uma pasta separada (…_teste); os resultados reais não são alterados.\n• Para voltar, clique em 'Sair do modo teste'.")) return;
  await post("/api/modo-teste", { ativo }, ativo ? "Ligando o modo teste…" : "Saindo do modo teste…");
  toast(ativo ? "Modo teste ligado — resultados simulados" : "Modo teste desligado — de volta à IA real");
  state.qid = null; await carregarStatus(); rota();
}
$("#btn-teste").onclick = async () => {
  const antes = !!state.status.ia.modo_teste;
  await alternarTeste(!antes);
  if (!!state.status.ia.modo_teste !== antes) $("#dlg-ia").close();  // a tela toda recarrega: fecha a janela
};
$("#teste-sair").onclick = () => alternarTeste(false);
$("#teste-limpar").onclick = async () => {
  if (!confirm("Apagar todos os dados do MODO TESTE deste projeto (categorias, classificações e resultados simulados)?\nOs resultados reais não são afetados.")) return;
  await post("/api/modo-teste/limpar", {}, "Apagando dados de teste…"); toast("Dados de teste apagados");
  state.qid = null; await carregarStatus(); irPara(null); renderPainel();
};
$("#btn-ia").onclick = abrirIA;
$("#li-painel").onclick = () => irPara(null);
$("#li-grupos").onclick = () => { if (location.hash === "#grupos") renderGrupos(); else location.hash = "grupos"; };
$("#li-usage").onclick = () => { if (location.hash === "#usage") renderUsage(); else location.hash = "usage"; };
$("#li-resultados").onclick = () => { if (location.hash === "#resultados") renderResultados(); else location.hash = "resultados"; };
$("#li-gerenciar").onclick = () => { if (location.hash === "#gerenciar") renderGerenciar(); else location.hash = "gerenciar"; };
// ---- topo: menu do projeto (trocar de projeto / novo projeto ficam aqui dentro)
function fecharPainelProjeto() { $("#proj").classList.remove("aberto"); $("#proj-panel").classList.add("hidden"); }
function alternarPainelProjeto() {
  const aberto = !$("#proj-panel").classList.contains("hidden");
  $("#proj").classList.toggle("aberto", !aberto);
  $("#proj-panel").classList.toggle("hidden", aberto);
}
async function trocarProjeto(slug) {
  if (!slug || slug === state.status.projeto.slug) return;
  await post("/api/projeto", { slug }, "Trocando de projeto…");
  // nada do projeto antigo pode sobreviver: heartbeat de presença da pergunta, pergunta aberta, filtros, rascunho de novo projeto
  pararPresenca();
  Object.assign(state, { qid: null, P: null, view: "painel", filtro: filtroInicial(), mostrar: POR_PAGINA, novo: null, grupo: null });
  await carregarStatus();
  // abas gerais ficam onde estão; a rota antiga (#Q4, #grupo/x) pode não existir no projeto novo e vai ao painel
  if (["#usage", "#resultados", "#gerenciar", "#painel", ""].includes(location.hash)) rota(); else irPara(null);
  presencaProjTick();
}
$("#proj-btn").onclick = (e) => { e.stopPropagation(); alternarPainelProjeto(); };
$("#proj-panel").onclick = (e) => e.stopPropagation();  // clique dentro do cartão não fecha
document.addEventListener("click", () => { if (!$("#proj-panel").classList.contains("hidden")) fecharPainelProjeto(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharPainelProjeto(); });

// ---------------------------------------------------------------- novo projeto (assistente)
// O rascunho vem do servidor, feito sem IA a partir da planilha. Aqui a pessoa só revisa: tipos,
// rótulos, o que categorizar, contexto e conferência do pedido. Criar exige validação sem erros.
const TIPOS_NOVO = { meta: "controle (id, data…)", unica: "fechada (escolha única)", numerica: "número", aberta: "aberta (texto)", pii: "🔒 dado pessoal", ignorar: "ignorar" };
const normNome = (s) => String(s).replace(/[–—]/g, "-").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
const ehCat = (c) => /.+_CAT2?$/.test(c);
function specDe(col) { return state.novo.projeto.PERGUNTAS.find((p) => (p.coluna || p.id) === col); }
function tipoDe(c) {
  const s = specDe(c.coluna);
  if (s) return s.tipo;
  return (state.novo.projeto.PII_MATCH || []).includes(normNome(c.coluna)) ? "pii" : "ignorar";
}
function novoId(col) {
  const usados = new Set(state.novo.projeto.PERGUNTAS.map((p) => p.id));
  let base = /^[A-Za-z][A-Za-z0-9_]*$/.test(col) ? col : col.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "").toUpperCase().slice(0, 30);
  if (!/^[A-Za-z]/.test(base)) base = "V_" + base;
  let id = base, i = 2;
  while (usados.has(id)) id = `${base}_${i++}`;
  return id;
}
function mudarTipo(c, tipo) {
  const P = state.novo.projeto, antigo = specDe(c.coluna), n = normNome(c.coluna);
  if (tipo === "unica" && !c.valores) { toast("Esta coluna tem valores diferentes demais para ser uma fechada.", true); return false; }
  P.PERGUNTAS = P.PERGUNTAS.filter((p) => p !== antigo);
  P.PII_MATCH = (P.PII_MATCH || []).filter((x) => x !== n);
  if (tipo === "pii") P.PII_MATCH.push(n);
  if (["meta", "unica", "numerica", "aberta"].includes(tipo)) {
    const s = { id: antigo ? antigo.id : novoId(c.coluna), tipo, rotulo: (antigo && antigo.rotulo) || c.enunciado || c.coluna };
    if (s.id !== c.coluna) s.coluna = c.coluna;
    if (tipo === "unica") s.niveis = c.valores.map((v) => v[0]);
    if (tipo === "aberta") { s.codificar = false; if (antigo && antigo.base) s.base = antigo.base; }
    if (tipo === "numerica" && antigo && antigo.nps) s.nps = true;
    P.PERGUNTAS.push(s);
    const ordem = state.novo.colunas.map((x) => x.coluna);
    P.PERGUNTAS.sort((a, b) => ordem.indexOf(a.coluna || a.id) - ordem.indexOf(b.coluna || b.id));
  }
  return true;
}
function corDe(col) { const c = state.novo.colunas.find((x) => x.coluna === col); return c ? c.cor : null; }
function amostraCor(cor) {
  if (!cor || cor === state.novo.cor_maioria) return "";
  const css = /^FF[0-9A-F]{6}$/.test(cor) ? "#" + cor.slice(2) : "var(--accent-2)";
  return `<span class="cor" style="background:${css}" title="cabeçalho destacado na planilha"></span>`;
}
function descFiltro(base) {
  if (!base || base === "todos") return "todos os respondentes";
  const r = (state.novo.projeto.FILTROS || {})[base];
  return r ? r.descricao || base : `⚠ filtro ${base} não existe`;
}

function renderNovo() {
  state.view = "novo"; state.qid = null; state.P = null; renderSidebar();
  const N = state.novo;
  const viaSkill = `
    <details class="via-skill">
      <summary>🤖 Prefere criar com uma IA? Veja como funciona a skill <code>novo-projeto</code></summary>
      <p>O mesmo projeto pode ser criado conversando com o Claude Code, o Codex ou o Antigravity, abertos na pasta
      <code>tabulador</code>. A IA segue o roteiro de <code>.claude/skills/novo-projeto/SKILL.md</code>
      (o <code>AGENTS.md</code> aponta para ele), com as mesmas travas deste assistente.</p>
      <ol>
        <li><b>Perfil da planilha</b> (<code>python -m novo_projeto.cli perfil &lt;planilha&gt;</code>): lê tipos, opções, dados pessoais e as colunas <code>_CAT</code> destacadas, sem IA. Se a planilha for SurveyMonkey (cabeçalho duplo), a IA para e avisa que esse formato é configurado à mão.</li>
        <li><b>Perguntas obrigatórias a você</b>, antes de gerar qualquer coisa: nome, cliente e pasta; quem pediu a categorização e por qual canal; quais abertas foram pedidas; contexto da pesquisa; regras de pulo do questionário. O que você não souber fica como "não informado", e a IA não pode inventar.</li>
        <li><b>Rascunho sem IA</b> (<code>rascunho</code>): copia a planilha para a pasta do projeto e cria o <code>projeto.json</code>, com a lista "Confira" (a mesma que este assistente mostra no passo 2).</li>
        <li><b>Completar o projeto.json</b>: a IA só escreve contexto, rótulos, instruções e a conferência do pedido. Opções, filtros, dados pessoais e tipos vêm dos dados e só mudam se você confirmar.</li>
        <li><b>Validar</b> (<code>validar</code>) até aparecer "✅ Projeto válido". A IA mostra todos os avisos e anota a sua decisão.</li>
        <li><b>Registrar</b> (<code>registrar</code>) e ler a base. O projeto aparece no seletor do topo.</li>
        <li><b>Relatório final</b>: abertas que serão categorizadas, filtros para confirmar e avisos aceitos.</li>
      </ol>
      <p>Pedido para colar na IA:</p>
      <pre class="pedido-skill">Crie um projeto novo no Tabulador com a planilha &lt;caminho da planilha.xlsx&gt;, seguindo a skill novo-projeto.</pre>
      <p class="small">Regra da skill: <b>dados vêm do código; intenção vem da pessoa; a IA não inventa nenhum dos dois.</b></p>
    </details>`;
  const passo1 = `
    <h2>1. Planilha</h2>
    <div class="info">A planilha precisa ter <b>uma linha de cabeçalho e uma coluna por pergunta</b> (como a do SESI). Ela é copiada para a pasta do projeto e nunca é alterada. Nada é enviado para a IA nesta etapa.</div>
    <div class="form-novo">
      <label class="campo">Nome do projeto <input id="nv-nome" value="${esc(N ? N.projeto.NOME : "")}" placeholder="ex.: SESI Minas — Satisfação 2026"></label>
      <label class="campo">Cliente <input id="nv-cliente" value="${esc(N ? N.projeto.CLIENTE : "")}" placeholder="(opcional)"></label>
      <label class="campo">Pasta do projeto <input id="nv-pasta" value="${esc(N ? N.pasta : "")}" placeholder="padrão: jumppi\\<Nome>_cat"></label>
      <label class="campo">Planilha (.xlsx) <input type="file" id="nv-arquivo" accept=".xlsx,.xlsm"></label>
      <div><button class="btn primary" id="nv-ler">${N ? "Ler outra planilha" : "Ler planilha"}</button></div>
    </div>
    ${N ? `<div class="small">Lida: <b>${N.n_linhas}</b> linhas · pasta <code>${esc(N.pasta)}</code> · aba
      <select id="nv-aba">${N.abas.map((a) => `<option ${a === N.aba ? "selected" : ""}>${esc(a)}</option>`).join("")}</select></div>` : ""}`;
  if (!N) { $("#main").innerHTML = `<h1>Novo projeto</h1>${viaSkill}${passo1}`; ligarNovo(); return; }

  const P = N.projeto;
  const notas = (P._notas || []).map((n) => `<li>${esc(n)}</li>`).join("");
  const linhas = N.colunas.filter((c) => !ehCat(c.coluna)).map((c) => {
    const tipo = tipoDe(c), s = specDe(c.coluna), cat = N.colunas.find((x) => x.coluna === c.coluna + "_CAT");
    const opcoes = Object.entries(TIPOS_NOVO).map(([k, v]) => `<option value="${k}" ${k === tipo ? "selected" : ""}>${v}</option>`).join("");
    let det = `${c.n} preenchidas`;
    if (tipo === "unica" && s) det += ` · <span title="${esc((s.niveis || []).join("\n"))}">${(s.niveis || []).length} opções</span>`;
    if (tipo === "numerica" && c.min != null) det += ` · ${c.min}–${c.max}${s && s.nps ? " · NPS" : ""}`;
    if (tipo === "aberta" && s) det += `<br>Quem recebeu: <select data-base="${esc(c.coluna)}"><option value="todos">todos os respondentes</option>${Object.entries(P.FILTROS || {}).map(([k, r]) => `<option value="${esc(k)}" ${s.base === k ? "selected" : ""}>${esc(r.descricao || k)}</option>`).join("")}</select>`;
    if (c.pii) det += ` · <span class="pill warn">parece dado pessoal (${esc(c.pii)})</span>`;
    return `<tr class="${tipo === "ignorar" || tipo === "pii" ? "apagada" : ""}">
      <td><b>${esc(c.coluna)}</b>${c.enunciado ? `<br><small>${esc(c.enunciado.split(" — ").pop().slice(0, 90))}</small>` : ""}</td>
      <td>${cat ? `${esc(cat.coluna)} ${amostraCor(cat.cor)}` : ""}</td>
      <td><select data-tipo="${esc(c.coluna)}">${opcoes}</select></td>
      <td>${s ? `<input class="inline" data-rotulo="${esc(c.coluna)}" value="${esc(s.rotulo)}">` : ""}</td>
      <td class="small">${det}</td>
      <td>${tipo === "aberta" && s ? `<label><input type="checkbox" data-cod="${esc(c.coluna)}" ${s.codificar ? "checked" : ""}> categorizar</label>` : ""}</td></tr>`;
  }).join("");
  const abertas = P.PERGUNTAS.filter((p) => p.tipo === "aberta");
  const marcadas = abertas.filter((p) => p.codificar);
  const C = P.CONFERENCIA || (P.CONFERENCIA = {});
  if (!C.data) C.data = new Date().toISOString().slice(0, 10);
  const pedidas = new Set(C.abertas_pedidas || []);
  const V = N.validacao;
  $("#main").innerHTML = `
    <h1>Novo projeto <small>${esc(P.NOME)}</small></h1>
    ${viaSkill}
    ${passo1}
    <h2>2. Colunas <small>o rascunho foi montado a partir dos dados — confira</small></h2>
    ${notas ? `<div class="aviso"><b>Para conferir:</b><ul class="notas">${notas}</ul></div>` : ""}
    <div class="info">As opções das fechadas são copiadas da planilha exatamente como estão (mesmo com erro de digitação), para nenhuma resposta se perder. Colunas marcadas como <b>dado pessoal</b> ou <b>ignorar</b> não entram na base nem vão para a IA. Os filtros ("quem recebeu") foram deduzidos de quem respondeu; quem respondeu nunca fica de fora.</div>
    <table class="novo"><thead><tr><th>Coluna na planilha</th><th>Coluna de categoria</th><th>Tipo</th><th>Rótulo</th><th>Detalhes</th><th>Categorizar?</th></tr></thead><tbody>${linhas}</tbody></table>

    <h2>3. Contexto para a IA</h2>
    <label class="campo">Descrição da pesquisa (vai em todos os pedidos à IA: quem respondeu, objetivo, temas)
      <textarea id="nv-contexto" rows="4" placeholder="ex.: Pesquisa de satisfação com pais e responsáveis de alunos das escolas…">${esc(P.CONTEXTO_PROJETO || "")}</textarea></label>
    <div class="box-instr">
      <label class="campo">Anotações para a IA sugerir o texto (opcional)<textarea id="nv-notas" rows="2" placeholder="o que você sabe do projeto: cliente, público, objetivo…">${esc(N.notas || "")}</textarea></label>
      <button class="btn" id="nv-sugerir">✨ Sugerir contexto, rótulos e instruções com IA</button>
      <span class="small">Usa a IA configurada em ⚙ (inclusive o Claude Code do computador). Envia os enunciados e até 12 respostas de exemplo de cada aberta marcada. Você revisa tudo antes de criar.</span>
    </div>
    ${marcadas.length ? `<h3>Instruções por pergunta (opcional)</h3>${marcadas.map((p) => `<label class="campo"><b>${esc(p.id)}</b> · ${esc(p.rotulo)}
      <textarea rows="2" data-instr="${esc(p.id)}" placeholder="que tipo de categoria criar (ex.: PONTOS A MELHORAR, temáticas, nomes curtos)">${esc(p.instrucoes_frame || "")}</textarea></label>`).join("")}` : ""}

    <h2>4. Conferência do pedido</h2>
    <div class="info">Confirme com quem pediu <b>quais abertas devem ser categorizadas</b>. É o que evita categorizar uma pergunta que não foi pedida (ou esquecer uma). Se a lista abaixo for diferente das marcadas em "Categorizar?", a validação avisa.</div>
    <div class="form-novo">
      <label class="campo">Quem confirmou <input id="nv-resp" value="${esc(C.responsavel || "")}" placeholder="nome"></label>
      <label class="campo">Data <input type="date" id="nv-data" value="${esc(C.data)}"></label>
      <label class="campo">De onde veio o pedido <input id="nv-origem" value="${esc(C.origem_pedido || "")}" placeholder="e-mail, reunião, planilha marcada em amarelo…"></label>
    </div>
    <div class="pedidas">${abertas.map((p) => {
      const cat = (P.SAIDA_PLANILHA && P.SAIDA_PLANILHA.colunas || {})[p.id] || (p.coluna || p.id) + "_CAT";
      return `<label><input type="checkbox" data-pedida="${esc(p.id)}" ${pedidas.has(p.id) ? "checked" : ""}> <b>${esc(p.id)}</b> ${esc(p.rotulo)} ${amostraCor(corDe(cat))}</label>`;
    }).join("") || '<span class="small">Nenhuma coluna marcada como aberta.</span>'}</div>

    <h2>5. Validar e criar</h2>
    <div class="tools">
      <label>Nome curto (sem espaços) <input id="nv-slug" value="${esc(N.slug || "")}" placeholder="automático"></label>
      <button class="btn" id="nv-validar">Validar</button>
      <button class="btn primary" id="nv-criar" ${V && V.valido ? "" : "disabled"} title="Disponível depois de uma validação sem erros">Criar projeto</button>
    </div>
    ${V ? `<div class="validacao">${V.valido ? '<div class="pill ok">✓ Projeto válido</div>' : `<div class="pill warn">${V.erros.length} erro(s) — corrija e valide de novo</div>`}
      <ul>${V.erros.map((e) => `<li class="erro">❌ ${esc(e)}</li>`).join("")}${V.avisos.map((a) => `<li class="av">⚠ ${esc(a)}</li>`).join("")}${V.ok.map((o) => `<li class="small">✓ ${esc(o)}</li>`).join("")}</ul></div>` : ""}`;
  ligarNovo();
}

function lerCamposNovo() {
  const P = state.novo.projeto;
  P.CONTEXTO_PROJETO = $("#nv-contexto").value.trim();
  state.novo.notas = $("#nv-notas").value;
  state.novo.slug = $("#nv-slug").value.trim();
  P.CONFERENCIA = { responsavel: $("#nv-resp").value.trim(), data: $("#nv-data").value, origem_pedido: $("#nv-origem").value.trim(),
    abertas_pedidas: [...document.querySelectorAll("[data-pedida]")].filter((x) => x.checked).map((x) => x.dataset.pedida) };
}
function invalidarNovo() { if (state.novo) { state.novo.validacao = null; const b = $("#nv-criar"); if (b) b.disabled = true; } }
function redesenharNovo() { if (state.novo && $("#nv-contexto")) lerCamposNovo(); manterScroll(renderNovo); }

function ligarNovo() {
  $("#nv-ler").onclick = async () => {
    const f = $("#nv-arquivo").files[0], nome = $("#nv-nome").value.trim();
    if (!nome) return toast("Informe o nome do projeto.", true);
    if (!f) return toast("Escolha a planilha (.xlsx).", true);
    const enviar = async (substituir) => {
      const fd = new FormData();
      fd.append("planilha", f); fd.append("nome", nome); fd.append("cliente", $("#nv-cliente").value.trim());
      fd.append("pasta", $("#nv-pasta").value.trim()); if (substituir) fd.append("substituir", "1");
      busy("Lendo a planilha e montando o rascunho… (pode levar até 1 minuto)");
      try { return await fetch("/api/novo/iniciar", { method: "POST", body: fd }); } finally { idle(); }
    };
    let r = await enviar(false), j = await r.json();
    if (r.status === 409 && confirm(j.erro + "\n\nSubstituir o projeto.json dessa pasta pelo rascunho novo?")) { r = await enviar(true); j = await r.json(); }
    if (!r.ok) return toast("Erro: " + j.erro, true);
    state.novo = { ...j, validacao: null, notas: "", slug: "" }; renderNovo(); toast("Rascunho pronto — confira as colunas.");
  };
  if (!state.novo) return;
  $("#nv-aba") && ($("#nv-aba").onchange = async (e) => {
    if (!confirm("Reler usando outra aba refaz o rascunho (as edições desta tela se perdem). Continuar?")) { e.target.value = state.novo.aba; return; }
    const j = await post("/api/novo/aba", { pasta: state.novo.pasta, aba: e.target.value }, "Relendo a planilha…");
    state.novo = { ...j, validacao: null, notas: "", slug: "" }; renderNovo();
  });
  document.querySelectorAll("[data-tipo]").forEach((el) => (el.onchange = () => {
    const c = state.novo.colunas.find((x) => x.coluna === el.dataset.tipo);
    if (mudarTipo(c, el.value)) { invalidarNovo(); redesenharNovo(); } else el.value = tipoDe(c);
  }));
  document.querySelectorAll("[data-rotulo]").forEach((el) => (el.onchange = () => { specDe(el.dataset.rotulo).rotulo = el.value.trim(); invalidarNovo(); }));
  document.querySelectorAll("[data-base]").forEach((el) => (el.onchange = () => { const s = specDe(el.dataset.base); if (el.value === "todos") delete s.base; else s.base = el.value; invalidarNovo(); }));
  document.querySelectorAll("[data-cod]").forEach((el) => (el.onchange = () => { specDe(el.dataset.cod).codificar = el.checked; invalidarNovo(); redesenharNovo(); }));
  document.querySelectorAll("[data-instr]").forEach((el) => (el.onchange = () => { state.novo.projeto.PERGUNTAS.find((p) => p.id === el.dataset.instr).instrucoes_frame = el.value.trim(); invalidarNovo(); }));
  ["#nv-contexto", "#nv-resp", "#nv-data", "#nv-origem"].forEach((s) => ($(s).oninput = invalidarNovo));
  document.querySelectorAll("[data-pedida]").forEach((el) => (el.onchange = invalidarNovo));
  $("#nv-sugerir").onclick = async () => {
    lerCamposNovo();
    const r = await post("/api/novo/sugerir", { pasta: state.novo.pasta, projeto: state.novo.projeto, notas: state.novo.notas }, "A IA está sugerindo textos… (pode levar até 1 minuto)");
    const P = state.novo.projeto;
    if (r.contexto && (!P.CONTEXTO_PROJETO || confirm("Substituir a descrição da pesquisa pela sugestão da IA?\n\n" + r.contexto))) P.CONTEXTO_PROJETO = r.contexto;
    for (const x of r.rotulos || []) { const s = P.PERGUNTAS.find((p) => p.id === x.id); if (s && x.rotulo) s.rotulo = x.rotulo; }
    for (const x of r.instrucoes || []) { const s = P.PERGUNTAS.find((p) => p.id === x.id && p.codificar); if (s && x.instrucoes && !s.instrucoes_frame) s.instrucoes_frame = x.instrucoes; }
    invalidarNovo(); manterScroll(renderNovo); toast("Sugestões aplicadas — revise os textos antes de criar.");
  };
  $("#nv-validar").onclick = async () => {
    lerCamposNovo();
    state.novo.validacao = await post("/api/novo/validar", { pasta: state.novo.pasta, projeto: state.novo.projeto }, "Validando (lendo a planilha como o tabulador vai ler)…");
    manterScroll(renderNovo);
  };
  $("#nv-criar").onclick = async () => {
    lerCamposNovo();
    const r = await post("/api/novo/criar", { pasta: state.novo.pasta, projeto: state.novo.projeto, slug: state.novo.slug }, "Criando o projeto e lendo a planilha…");
    state.novo = null; toast(`Projeto criado (${r.slug}).`); await carregarStatus(); irPara(null); renderPainel();
  };
}
$("#btn-novo").onclick = () => { fecharPainelProjeto(); if (location.hash === "#novo") renderNovo(); else location.hash = "novo"; };

// ---------------------------------------------------------------- rotas / boot
function rota() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (state.qid && h !== state.qid) pararPresenca();
  if (h === "novo") { renderNovo(); medirAlturasFixas(); observarCabecalho(); }
  else if (h === "grupos") { renderGrupos(); medirAlturasFixas(); observarCabecalho(); }
  else if (h === "usage") { renderUsage(); medirAlturasFixas(); observarCabecalho(); }
  else if (h === "resultados") { renderResultados(); medirAlturasFixas(); observarCabecalho(); }
  else if (h === "gerenciar") { renderGerenciar(); medirAlturasFixas(); observarCabecalho(); }
  else if (h.startsWith("grupo/") && state.status.perguntas.some((s) => s.grupo?.nome === h.slice(6))) abrirGrupo(h.slice(6));
  else if (h && h !== "painel" && state.status.perguntas.some((s) => s.qid === h)) abrir(h);
  else { renderPainel(); medirAlturasFixas(); observarCabecalho(); }
}
window.addEventListener("hashchange", rota);
// programa atualizado/reiniciado com a página aberta: avisa para recarregar (senão botões novos falham)
let versaoPagina = null;
setInterval(async () => {
  try {
    const v = (await (await fetch("/api/versao")).json()).versao;
    if (versaoPagina && v !== versaoPagina && !document.querySelector("#aviso-versao")) {
      const d = document.createElement("div");
      d.id = "aviso-versao"; d.className = "faixa-teste";
      d.innerHTML = `🔄 O programa foi atualizado. <span class="acoes"><button class="btn sm primary">Recarregar a página</button></span>`;
      d.querySelector("button").onclick = () => location.reload();
      document.querySelector(".top").after(d);
    }
    versaoPagina = versaoPagina || v;
  } catch (e) { /* servidor fechado: o navegador mostra erro nas ações */ }
}, 20000);
fetch("/api/versao").then((r) => r.json()).then((j) => (versaoPagina = j.versao)).catch(() => {});
(async () => {
  const pedido = new URLSearchParams(location.search).get("projeto");
  await carregarStatus();
  if (pedido && pedido !== state.status.projeto.slug && state.status.projetos.some((p) => p.slug === pedido)) {
    await post("/api/projeto", { slug: pedido }); await carregarStatus();
  }
  if (pedido) history.replaceState(null, "", "/" + location.hash);
  rota();
  await garantirIdentificacao();
  iniciarPresencaProjeto();
})();
