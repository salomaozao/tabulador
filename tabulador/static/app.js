/* Tabulador — front-end (vanilla JS, sem build). */
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (n, d) => (d ? Math.round((100 * n) / d) + "%" : "–");
const POR_PAGINA = 100;

const filtroInicial = () => ({ q: "", cat: "", alertas: false, comentarios: false, situacao: "", ordem: "conf" });
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
  $("#busy-sub").textContent = ativa ? ativa.nome + "…" : "";
  const st = [`⏱ <b>${fmtDur(p.decorrido)}</b> decorridos`];
  if (p.restante != null) st.push(`${p.restante < 1 ? "<b>quase pronto…</b> <small>(a IA está demorando mais que a média)</small>" : `faltam <b>~${fmtDur(p.restante)}</b>`}${p.restante < 1 ? "" :ativa && ativa.estimativa && !p.feitos ? " <small>(pela média das últimas vezes)</small>" : ""}`);
  if (p.total && ativa && ativa.chave === "ia") st.push(`<b>${p.feitos}</b> de <b>${p.total}</b> ${p.unidade || "respostas"}`);
  if (p.lotes_total) st.push(`lote <b>${p.lotes_feitos}</b>/${p.lotes_total}`);
  if (p.velocidade_min) st.push(`<b>${Math.round(p.velocidade_min)}</b> respostas/min`);
  if (p.ia_ativas) st.push(`🤖 ${p.ia_ativas} chamada(s) à IA em andamento`);
  if (p.ia_feitas) st.push(`${p.ia_feitas} chamada(s) concluída(s)`);
  if (p.tokens) st.push(`${fmtMil(p.tokens)} tokens`);
  if (p.erros) st.push(`<span class="warn-t">${p.erros} lote(s) com erro</span>`);
  if (p.limite_atingido) st.push(`<span class="warn-t">limite do provedor atingido — parando…</span>`);
  $("#busy-stats").innerHTML = st.join("<span>·</span>");
  $("#busy-etapas").innerHTML = (p.etapas || []).map((e) => {
    const ic = e.estado === "feito" ? "✓" : e.estado === "ativo" ? '<span class="mini-spin"></span>' : e.estado === "erro" ? "✕" : "○";
    const t = e.estado === "ativo" && e.decorrido != null ? fmtDur(e.decorrido) : e.estado === "feito" && e.fim && e.inicio ? fmtDur(e.fim - e.inicio) : "";
    return `<li class="${e.estado}"><span class="ic">${ic}</span><span>${esc(e.nome)}${e.detalhe && e.estado !== "pendente" ? `<span class="det">${esc(e.detalhe)}</span>` : ""}</span><span class="t">${t}</span></li>`;
  }).join("");
  $("#busy-log").innerHTML = (p.eventos || []).slice(-6).reverse().map((e) => `<div><span>${esc(e.hora)}</span>${esc(e.msg)}</div>`).join("");
}
function busy(msg) {
  busyIni = Date.now();
  $("#busy-msg").textContent = msg || "Processando…"; $("#busy-sub").textContent = "";
  $("#busy-stats").innerHTML = ""; $("#busy-etapas").innerHTML = ""; $("#busy-log").innerHTML = "";
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
let toastT;
function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.add("hidden"), err ? 9000 : 2800);
}
async function api(path, opts = {}, msg, progresso = false) {
  if (msg) busy(msg, progresso);
  const timeoutMs = opts.timeout || 35000;
  const signal = opts.signal || (AbortSignal.timeout ? AbortSignal.timeout(timeoutMs) : undefined);
  try {
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, signal, ...opts }).catch((err) => {
      if (err?.name === "TimeoutError") {
        throw new Error(`o servidor demorou mais de ${timeoutMs / 1000}s para responder.`);
      }
      throw new Error("o Tabulador não respondeu — a janela do programa foi fechada ou reiniciada. Abra-o de novo pelo atalho e recarregue a página.");
    });
    const j = await r.json().catch(() => ({ erro: r.statusText }));
    if (!r.ok) throw new Error(j.erro || r.statusText);
    return j;
  } catch (e) { toast("Erro: " + e.message, true); throw e; }
  finally { if (msg) idle(); }
}
const post = (path, body, msg, progresso) => api(path, { method: "POST", body: JSON.stringify(body || {}) }, msg, progresso);
const manterScroll = (fn) => { const y = window.scrollY; fn(); window.scrollTo(0, y); };

// ---------------------------------------------------------------- status / topo / barra lateral
async function carregarStatus() {
  state.status = await api("/api/status");
  const S = state.status, b = S.base;
  $("#sel-projeto").innerHTML = S.projetos.map((p) => `<option value="${esc(p.slug)}" ${p.slug === S.projeto.slug ? "selected" : ""} ${p.ok ? "" : "disabled"}>${esc(p.nome)}${p.ok ? "" : " (erro)"}</option>`).join("");
  $("#ia-status").innerHTML = `IA: ${S.ia.tem_chave ? esc(S.ia.modelo) + (S.ia.provedor !== "openai" ? ` <small>(${esc(S.ia.provedor)})</small>` : "") : '<span class="pill warn">sem chave</span>'}`;
  const n = S.nuvem, ns = $("#nuvem-status");
  const dotCls = n.conectada ? "ok" : n.ativa ? "warn" : "off";
  const texto = n.conectada ? `sincronizado ${fmtDataHora(n.ultima_sincronizacao)}` : n.ativa ? "nuvem configurada, sem conexão" : "sem nuvem (local)";
  const titulo = n.conectada ? "Conectado ao banco compartilhado da equipe — a revisão de todo mundo aparece aqui."
    : n.ativa ? "TABULADOR_TURSO_URL configurado, mas não deu para conectar agora — a revisão pode estar desatualizada."
    : "Sem TABULADOR_TURSO_URL configurado: a revisão fica só nesta máquina, não sincroniza com a equipe.";
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
  $("#li-usage").className = state.view === "usage" ? "ativa" : "";
  $("#li-resultados").className = state.view === "resultados" ? "ativa" : "";
  $("#li-gerenciar").className = state.view === "gerenciar" ? "ativa" : "";
  const ul = $("#lista-perguntas"); ul.innerHTML = "";
  for (const s of state.status.perguntas) {
    const li = document.createElement("li");
    li.className = s.qid === state.qid ? "ativa" : "";
    const badges = [pillStatus(s)];
    if (s.codificacao && s.n_codificadas) badges.push(`<span class="pill">${pct(s.n_revisadas, s.n_codificadas)} revisado</span>`);
    li.innerHTML = `<span class="t">${esc(s.rotulo)}</span><span class="small">${esc(s.qid)}${s.backcoding ? " · back-coding" : ""}${s.respondeu ? " · " + s.respondeu + " resp." : ""}</span><span class="b">${badges.join("")}</span>`;
    li.onclick = () => irPara(s.qid);
    ul.appendChild(li);
  }
}
function irPara(qid) { location.hash = qid || "painel"; }

// ---------------------------------------------------------------- painel geral
function renderPainel() {
  state.view = "painel"; state.qid = null; state.P = null; renderSidebar();
  const S = state.status, b = S.base, R = S.resultados;
  const avisos = [];
  if (!S.ia.tem_chave) avisos.push(`<div class="aviso">A chave da OpenAI ainda não foi configurada — sem ela a IA não funciona. <button class="btn sm" data-acao="ia">⚙ Configurar IA</button></div>`);
  if (!b.fonte_existe) avisos.push(`<div class="aviso">Planilha-fonte não encontrada: <code>${esc(b.fonte)}</code></div>`);
  else if (!b.carregada) avisos.push(`<div class="aviso">A planilha ainda não foi lida. <button class="btn sm primary" data-acao="load">Ler a planilha agora</button></div>`);

  const cards = S.perguntas.map((s) => {
    const cod = s.n_codificadas || 0, tot = s.n_unicas || s.respostas || 0;
    const barra = (v, d, cls = "") => `<div class="prog ${cls}"><i style="width:${d ? (100 * v) / d : 0}%"></i></div>`;
    return `<div class="card" data-qid="${esc(s.qid)}">
      <div class="card-h"><b>${esc(s.rotulo)}</b><span class="small">${esc(s.qid)}</span></div>
      <div class="small">${s.respondeu ? `${s.respondeu} responderam · ${tot} respostas únicas` : "respostas ainda não lidas"}</div>
      <div>${pillStatus(s)} ${s.alertas ? `<span class="pill warn">${s.alertas} alertas</span>` : ""}</div>
      ${s.codificacao ? `
        <div class="kv"><span>Classificadas</span><span>${cod} de ${tot}</span></div>${barra(cod, tot)}
        <div class="kv"><span>Revisadas por você</span><span>${s.n_revisadas} (${pct(s.n_revisadas, cod)})</span></div>${barra(s.n_revisadas, cod, "hum")}
        <div class="kv"><span>Acerto da IA</span><span>${s.acerto_ia == null ? "–" : Math.round(100 * s.acerto_ia) + "%"} <small>${s.n_avaliadas_ia ? `(${s.n_avaliadas_ia} conferidas)` : ""}</small></span></div>
        ${s.top && s.top.length ? `<div class="small top">Mais citadas: ${s.top.slice(0, 3).map((t) => esc(t.nome)).join(" · ")}</div>` : ""}` : ""}
      <button class="btn sm ${s.codificacao === "aprovado" ? "" : "primary"}">${s.codificacao === "aprovado" ? "Ver" : s.frame ? "Continuar" : "Começar"}</button>
    </div>`;
  }).join("");

  const aprovadas = S.perguntas.filter((s) => s.codificacao === "aprovado").length;
  const nArq = Object.values(R).filter((r) => r.existe).length;
  $("#main").innerHTML = `
    <h1>${esc(S.projeto.nome)}</h1>
    <div class="small">Planilha-fonte: ${esc(b.fonte)}</div>
    ${b.carregada ? `<div class="small">Base: <b>${b.n}</b> respondentes · atualizada ${b.atualizada_em}</div>` : ""}
    ${avisos.join("")}
    <h2>Perguntas abertas <small>${aprovadas} de ${S.perguntas.length} aprovadas</small></h2>
    <div class="cards">${cards}</div>
    <h2>Resultados</h2>
    <div class="info">📦 ${aprovadas} pergunta(s) aprovada(s) · ${nArq} arquivo(s) gerado(s). O resumo das categorias e os downloads (planilha final, codebook, cruzamentos) ficam na aba <a href="#resultados"><b>Resultados</b></a>.</div>`;
  document.querySelectorAll(".card").forEach((c) => (c.onclick = () => irPara(c.dataset.qid)));
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
async function refresh(payload) {
  state.P = payload || (await api(`/api/pergunta/${state.qid}`)); prepararItens();
  manterScroll(render); carregarStatus();
  if (payload?.limite_atingido) {
    toast(`Limite de uso do provedor atingido: parei a classificação. ${payload.nao_tentados} resposta(s) ficaram pendentes — espere um pouco (ou troque de provedor em '⚙ Configurar IA') e tente de novo.`, true);
  }
}
function prepararItens() { for (const r of state.P.itens || []) if (r._alertas_ia === undefined) r._alertas_ia = r.alertas; }

function catsValidas() { return state.P.frame?.categorias || []; }
function nomeCat(c) { const x = catsValidas().find((k) => k.codigo === +c); return x ? x.nome : ""; }

// recalcula contagens e números da revisão no navegador (sem recarregar tudo a cada clique)
function recalcular() {
  const P = state.P, cont = {};
  let cod = 0, conf = 0, confAuto = 0, corr = 0, corrIA = 0;
  for (const r of P.itens) {
    for (const [k, campo] of [[r.primaria, "primaria"], [r.secundaria, "secundaria"]]) {
      if (k == null) continue;
      cont[k] = cont[k] || { primaria: 0, secundaria: 0 }; cont[k][campo] += r.n;
    }
    if (r.primaria == null || r.origem === "erro") continue;  // erro na chamada = ainda falta classificar
    cod++;
    if (r.revisao === "confirmada") { conf++; if (r.validado_por === "auto") confAuto++; }
    if (r.revisao === "corrigida") { corr++; if (r.corrigido_de_nome != null) corrIA++; }
  }
  P.contagens = cont;
  P.n_alertas = P.itens.filter((r) => r.alertas && r.alertas !== "não codificado").length;
  P.n_comentarios_pendentes = P.itens.filter((r) => r.comentario_pendente).length;
  // confirmadas pelo supervisor.py (auto) não medem o acerto da IA — mesma regra de coding.resumo_revisao
  const aval = conf - confAuto + corrIA, tot = P.itens.length;
  P.revisao = { n_unicas: tot, n_codificadas: cod, n_faltantes: tot - cod, n_confirmadas: conf, n_confirmadas_auto: confAuto, n_corrigidas: corr, n_revisadas: conf + corr, acerto_ia: aval ? (conf - confAuto) / aval : null, n_avaliadas_ia: aval };
}
function aplicarItem(r, it) {
  const au = it.auditoria || null;
  Object.assign(r, {
    primaria: it.primaria, secundaria: it.secundaria, origem: it.origem, confianca: it.confianca,
    comentario: it.comentario || null, comentario_pendente: !!it.comentario && !it.comentario_aplicado_em,
    revisao: it.primaria == null ? null : it.origem === "humano" ? "corrigida" : it.validado ? "confirmada" : "pendente",
    validado_por: it.validado_por ?? null,
    corrigido_de_nome: it.corrigido_de != null ? nomeCat(it.corrigido_de) : null,
    auditoria: au,
    sugestao_nome: au && au.ok === false ? nomeCat(au.primaria) : null,
    sugestao_sec_nome: au && au.ok === false && au.secundaria != null ? nomeCat(au.secundaria) : null,
    ia_original_nome: it.ia_original ? nomeCat(it.ia_original.primaria) : null,
  });
  r.primaria_nome = nomeCat(r.primaria); r.secundaria_nome = nomeCat(r.secundaria);
  r.alertas = r.revisao === "pendente" ? r._alertas_ia || "" : r.revisao ? "" : "não codificado";
}

function render() {
  const P = state.P, R = P.respostas || {}, F = P.frame, C = P.codificacao, V = P.revisao;
  const frameOk = F && F.status === "aprovado", codOk = C && C.status === "aprovado";
  const faltam = V ? V.n_faltantes : 0;
  $("#main").innerHTML = `
    <div class="small"><a href="#painel">← Painel geral</a></div>
    <h1>${esc(P.rotulo)} <small>${esc(P.qid)}</small></h1>
    <div class="muted">${esc(R.enunciado || "")}</div>
    <div class="small">Quem respondeu: ${esc(R.base_descricao || "")}</div>
    <div id="presenca-banner"></div>
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
        ${!F ? `<button class="btn primary" id="b-induzir">✨ Gerar categorias com IA</button>` : ""}
        ${F && !F.fixo ? `<button class="btn" id="b-induzir">✨ Gerar do zero</button>` : ""}
        ${F ? `<button class="btn" id="b-janela-cat" title="Cada categoria com definição, exemplos${C ? ", perfil de quem citou e confirmação em bloco" : ""}">🗂 Revisar por categoria</button>` : ""}
        ${F && !frameOk ? `<button class="btn ok" id="b-aprovar-frame">✓ Aprovar categorias</button>` : ""}
      </span>
    </h2>
    ${F ? renderFrame() : `<div class="info">A IA lê as respostas e propõe uma lista fechada de categorias com definição e exemplos. Você pode renomear, mesclar, excluir, acrescentar ou pedir ajustes à IA antes de aprovar.</div>`}

    <h2>Classificação das respostas
      ${C ? `<span class="pill ${codOk ? "ok" : "warn"}">${codOk ? "aprovada" : "rascunho"}</span>` : ""}
      <span class="acoes">
        ${codOk ? `<button class="btn" id="b-reabrir">Reabrir para correções</button>` : ""}
        ${C ? `<a class="btn ghost" href="/relatorio/${P.qid}" target="_blank">Relatório</a><a class="btn ghost" href="/revisao/${P.qid}.xlsx">Baixar Excel</a>` : ""}
      </span>
    </h2>
    ${!frameOk ? `<div class="info">Aprove as categorias para liberar a classificação.</div>` : ""}
    ${frameOk && !codOk ? renderAcoesCod() : ""}
    ${C ? renderCodificacao() : ""}
    ${frameOk && !codOk ? renderAprovarBar() : ""}
  `;
  $("#instr").onblur = async (e) => { if (e.target.value !== P.instrucoes) { await post(`/api/pergunta/${P.qid}/instrucoes`, { texto: e.target.value }); P.instrucoes = e.target.value; toast("Instruções salvas"); } };
  $("#b-induzir")?.addEventListener("click", async () => {
    if (F && !confirm("Gerar do zero substitui as categorias atuais" + (C ? " e a classificação terá de ser refeita" : "") + ". Para ajustes pontuais, use 'Pedir ajuste à IA'. Continuar?")) return;
    refresh(await post(`/api/pergunta/${P.qid}/frame/induzir`, {}, "Gerando categorias com IA…"));
  });
  $("#b-aprovar-frame")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/frame/aprovar`, {}, "Aprovando…")));
  $("#b-janela-cat")?.addEventListener("click", () => abrirJanelaCategorias());
  $("#b-reabrir")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/reabrir`, {}, "Reabrindo…")));
  bindFrame(); bindAcoesCod(); bindCodificacao(); bindAprovarBar();
}

// ---------------------------------------------------------------- frame
function renderFrame() {
  const P = state.P, F = P.frame, n = P.respostas?.n_respondeu || 0, cats = F.categorias;
  const opts = (excl) => cats.filter((c) => !c.fixa && c.codigo !== excl).map((c) => `<option value="${c.codigo}">${c.codigo} · ${esc(c.nome)}</option>`).join("");
  const rows = cats.map((c) => {
    const k = P.contagens[c.codigo] || { primaria: 0, secundaria: 0 }, m = k.primaria + k.secundaria;
    const ro = c.fixa || F.fixo;
    return `<tr data-cod="${c.codigo}">
      <td class="num">${c.codigo}</td>
      <td>${ro ? `<b>${esc(c.nome)}</b>` : `<input class="inline f-nome" value="${esc(c.nome)}" title="Clique para renomear">`}</td>
      <td>${ro ? esc(c.definicao) : `<textarea class="inline f-def" rows="2">${esc(c.definicao)}</textarea>`}</td>
      <td class="ex"><small title="${esc((c.exemplos || []).join(" | "))}">${esc((c.exemplos || []).slice(0, 3).join("; "))}</small></td>
      <td class="num">${k.primaria}</td><td class="num">${k.secundaria}</td><td class="num"><b>${m}</b> <small>${pct(m, n)}</small></td>
      <td class="acoes">${ro ? "" : `<select class="f-mesclar sm" title="Mesclar esta categoria em outra"><option value="">mesclar em…</option>${opts(c.codigo)}</select> <button class="btn sm danger f-remover" title="Excluir (respostas vão para Outros)">✕</button>`}</td>
    </tr>`;
  }).join("");
  return `
    ${F.raciocinio && !F.fixo ? `<div class="info">💡 ${esc(F.raciocinio)}</div>` : ""}
    <table id="tab-frame"><thead><tr><th style="width:44px">Cód.</th><th style="width:19%">Categoria</th><th style="width:27%">Definição</th><th>Exemplos</th><th class="num" style="width:60px">Prim.</th><th class="num" style="width:60px">Sec.</th><th class="num" style="width:90px">Menções</th><th style="width:200px">Ações</th></tr></thead>
    <tbody>${rows}
      ${F.fixo ? "" : `<tr class="frame-add"><td>+</td><td><input class="inline" id="f-novo-nome" placeholder="Nova categoria"></td><td><input class="inline" id="f-novo-def" placeholder="Definição (1 frase)"></td><td colspan="4"></td><td><button class="btn sm" id="f-add">Adicionar</button></td></tr>`}
    </tbody></table>
    <div class="small">Renomear/definir: edite o texto e saia do campo. Mesclar: as respostas passam para a categoria de destino. 97 (Outros) e 98 (NS/NR) são fixas.</div>
    ${P.codificacao ? `<div class="info">Já há respostas classificadas, então as mudanças aqui valem na hora, sem aprovar de novo. <b>Renomear</b> não muda as respostas. <b>Mesclar</b> e <b>excluir</b> movem as respostas (as excluídas vão para Outros). Uma <b>definição nova</b> vale para as próximas classificações; para refazer as que você ainda não conferiu, use <b>Reclassificar tudo</b>.</div>` : ""}
    ${F.fixo ? "" : `
    <div class="box-instr refino">
      <b>Pedir ajuste à IA</b> <span class="small">— descreva o que mudar; a IA revisa a lista mantendo o resto</span>
      <textarea id="refino" placeholder="Ex.: 'Junte Estrutura física e Conservação', 'Crie uma categoria para transporte escolar', 'A categoria Ensino está ampla demais: separe metodologia e professores'"></textarea>
      <div class="tools"><button class="btn primary" id="b-refinar">✨ Ajustar categorias com IA</button>${P.pode_desfazer_refino ? `<button class="btn" id="b-desfazer">↶ Desfazer último ajuste</button>` : ""}</div>
    </div>`}`;
}
function bindFrame() {
  const P = state.P; if (!P.frame) return;
  document.querySelectorAll("#tab-frame tr[data-cod]").forEach((tr) => {
    const cod = tr.dataset.cod;
    tr.querySelector(".f-nome")?.addEventListener("change", async (e) => { refresh(await post(`/api/pergunta/${P.qid}/frame/categoria`, { codigo: cod, nome: e.target.value })); toast("Categoria renomeada"); });
    tr.querySelector(".f-def")?.addEventListener("change", async (e) => { await post(`/api/pergunta/${P.qid}/frame/categoria`, { codigo: cod, definicao: e.target.value }); toast("Definição salva"); });
    tr.querySelector(".f-mesclar")?.addEventListener("change", async (e) => {
      const dest = e.target.value; if (!dest) return;
      if (!confirm(`Mesclar "${nomeCat(cod)}" em "${nomeCat(dest)}"? A categoria ${cod} deixa de existir.`)) { e.target.value = ""; return; }
      refresh(await post(`/api/pergunta/${P.qid}/frame/fundir`, { destino: dest, origens: [cod] }, "Mesclando…"));
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
function renderAcoesCod() {
  const P = state.P, C = P.codificacao, V = P.revisao, R = P.respostas || {};
  const tam = `<select id="tam-amostra">${[30, 50, 100, 200].map((n) => `<option ${n === state.amostra ? "selected" : ""}>${n}</option>`).join("")}</select>`;
  if (!C) return `
    <div class="passo">
      <div><b>Comece por uma amostra.</b> A IA classifica ${tam} respostas; você confere, corrige e ajusta as instruções/categorias. Quando a taxa de acerto estiver boa, classifique o restante.</div>
      <div class="tools"><button class="btn primary" id="b-amostra">✨ Classificar amostra</button><button class="btn" id="b-codificar">Classificar todas as ${R.n_unicas || ""} de uma vez</button></div>
    </div>`;
  const acerto = V.acerto_ia == null ? null : Math.round(100 * V.acerto_ia);
  return `
    <div class="passo">
      <div class="revbar">
        <div><b>Revisão:</b> ${V.n_revisadas} de ${V.n_codificadas} classificadas conferidas (${pct(V.n_revisadas, V.n_codificadas)}) · <span class="pill ok">✓ ${V.n_confirmadas - (V.n_confirmadas_auto || 0)} confirmadas por pessoas</span>${V.n_confirmadas_auto ? ` <span class="pill ok auto" title="Confirmadas sozinhas: confiança alta e o auditor (outra IA) concordou">⚡ ${V.n_confirmadas_auto} automáticas</span>` : ""} <span class="pill human">✎ ${V.n_corrigidas} corrigidas</span>
        ${acerto != null ? ` · <b>a IA acertou ${acerto}%</b> <small>(de ${V.n_avaliadas_ia} conferidas)</small>` : ""}</div>
        <div class="small"><b>Classificadas:</b> ${V.n_codificadas} de ${V.n_unicas} respostas (${pct(V.n_codificadas, V.n_unicas)})${V.n_faltantes ? ` · faltam ${V.n_faltantes}` : ""}
          <span class="legenda"><i class="conf"></i>conferidas <i class="ia"></i>classificadas, a conferir <i></i>ainda não classificadas</span></div>
        <div class="prog pilha" title="${V.n_revisadas} conferidas · ${V.n_codificadas - V.n_revisadas} classificadas a conferir · ${V.n_faltantes} ainda não classificadas">
          <i class="conf" style="width:${V.n_unicas ? (100 * V.n_revisadas) / V.n_unicas : 0}%"></i><i class="ia" style="width:${V.n_unicas ? (100 * (V.n_codificadas - V.n_revisadas)) / V.n_unicas : 0}%"></i></div>
      </div>
      <div class="small">Loop: confirme ✓ o que está certo · corrija na hora pelo menu · ou escreva um comentário e clique em <b>Reclassificar comentadas</b>. Se o erro se repete, ajuste as <b>instruções</b> ou as <b>categorias</b> e clique em <b>Reclassificar tudo</b> (o que você corrigiu/confirmou é mantido).</div>
      <div class="tools">
        <button class="btn primary" id="b-recod-com" ${P.n_comentarios_pendentes ? "" : "disabled"}>✨ Reclassificar comentadas (${P.n_comentarios_pendentes})</button>
        <button class="btn" id="b-recod-tudo" title="Refaz com a IA tudo que você ainda não conferiu">↻ Reclassificar tudo</button>
        ${V.n_faltantes ? `<span class="sep"></span><button class="btn" id="b-mais">+ Classificar mais ${tam}</button><button class="btn primary" id="b-restantes">Classificar as restantes (${V.n_faltantes})</button>` : ""}
      </div>
      <div class="tools supervisao">
        <b>Supervisão:</b>
        <button class="btn" id="b-auditar" title="Outra IA confere a classificação, resposta por resposta (segundo codificador)">🔎 Auditar com outra IA</button>
        <button class="btn" id="b-auto" title="Confirma sozinho o que tem confiança alta E o auditor concordou">⚡ Aceitar alta confiança</button>
        <label class="small">limiar <input id="auto-limiar" type="number" min="0.5" max="1" step="0.05" value="${state.limiar ?? 0.85}" style="width:64px"></label>
        ${V.n_confirmadas_auto ? `<button class="btn ghost" id="b-desfazer-auto">↶ Desfazer as ${V.n_confirmadas_auto} automáticas</button>` : ""}
        <span class="sep"></span>
        <button class="btn" id="b-janela" title="Cada categoria com exemplos, perfil de quem citou e confirmação em bloco">🗂 Revisar por categoria</button>
      </div>
    </div>`;
}
function bindAcoesCod() {
  const P = state.P;
  $("#tam-amostra")?.addEventListener("change", (e) => (state.amostra = +e.target.value));
  const classificar = async (body, msg) => refresh(await post(`/api/pergunta/${P.qid}/codificar`, body, msg, true));
  $("#b-amostra")?.addEventListener("click", () => classificar({ limite: state.amostra }, "A IA está classificando a amostra…"));
  $("#b-codificar")?.addEventListener("click", () => { if (!confirm(`Classificar todas as ${P.respostas?.n_unicas} respostas agora? (Recomendado: testar numa amostra antes.)`)) return; classificar({}, "A IA está classificando as respostas…"); });
  $("#b-mais")?.addEventListener("click", () => classificar({ limite: state.amostra, restantes: true }, "A IA está classificando mais respostas…"));
  $("#b-restantes")?.addEventListener("click", () => classificar({ restantes: true }, "A IA está classificando as respostas restantes…"));
  $("#b-recod-com")?.addEventListener("click", async () => { const r = await post(`/api/pergunta/${P.qid}/recodificar`, { apenas_comentados: true }, "Reclassificando as respostas comentadas…", true); toast(`${r.recodificados} resposta(s) reclassificada(s)`); refresh(r); });
  $("#b-recod-tudo")?.addEventListener("click", async () => {
    if (!confirm("Reclassificar com a IA tudo o que você ainda não conferiu? O que você corrigiu ou confirmou é mantido.")) return;
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
async function abrirJanelaCategorias() {
  const P = state.P, qid = P.qid;
  const D = await api(`/api/pergunta/${qid}/perfil`, {}, "Montando o perfil das categorias…");
  const F = P.frame, frameOk = F && F.status === "aprovado", locked = P.codificacao?.status === "aprovado";
  const podeEditar = !F?.fixo && !locked;
  const catsOpc = (excl) => catsValidas().filter((c) => !c.fixa && c.codigo !== excl).map((c) => `<option value="${c.codigo}">${c.codigo} · ${esc(c.nome)}</option>`).join("");
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
      if (!confirm(`Mesclar "${c.nome}" em "${nomeCat(dest)}"? As respostas passam para a categoria de destino.`)) { e.target.value = ""; return; }
      await depois(await post(`/api/pergunta/${qid}/frame/fundir`, { destino: dest, origens: [cod] }, "Mesclando…"), "Categorias mescladas");
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
  const encherModelos = () => { const p = provs[selProv.value] || {}; selMod.innerHTML = (p.modelos || [p.modelo]).filter(Boolean).map((m) => `<option>${esc(m)}</option>`).join(""); };
  selProv.onchange = encherModelos; encherModelos();
  $("#au-ok").onclick = async () => {
    const body = { provedor: selProv.value, modelo: selMod.value, escopo: $("#au-esc").value, aceitar: $("#au-aceitar").checked, limiar: state.limiar ?? 0.85 };
    dlg.close();
    const r = await post(`/api/pergunta/${P.qid}/auditar`, body, "O auditor está conferindo a classificação…", true);
    refresh(r);
    const A = r.auditoria || {};
    abrirJanela("Auditoria concluída", `<p>Auditor: <b>${esc(A.por || "—")}</b>. ${fmtN(A.auditadas || 0)} resposta(s) conferidas:
      <b>${fmtN(A.concorda || 0)}</b> concordam e <b>${fmtN(A.discorda || 0)}</b> discordam.${A.lotes_com_erro ? ` ${A.lotes_com_erro} lote(s) deram erro (rode de novo depois).` : ""}</p>
      ${A.auto ? `<p><b>${fmtN(A.auto.aceitas)}</b> aceitas sozinhas (confiança alta + auditor concordando).</p>` : ""}
      <p class="small">As discordâncias aparecem na tabela com <b>🔎 auditor sugere…</b>. Filtre por <b>auditor discordou</b> e use o botão ou a tecla <kbd>S</kbd> para aceitar a sugestão.</p>`);
  };
}
// botão de aprovar fica no fim da tabela (depois de revisar tudo), não no topo — ver renderCodificacao
function renderAprovarBar() {
  const P = state.P, C = P.codificacao, V = P.revisao;
  if (!C) return "";
  return `
    <div class="tools aprovar-bar">
      <button class="btn ok" id="b-aprovar-cod" ${V.n_faltantes ? `disabled title="Classifique as restantes antes de aprovar"` : ""}>✓ Aprovar e gravar nos resultados</button>
    </div>`;
}
function bindAprovarBar() {
  const P = state.P; if (!P.codificacao) return;
  $("#b-aprovar-cod")?.addEventListener("click", async () => {
    const V = P.revisao, naoConf = V.n_codificadas - V.n_revisadas;
    if (!confirm(`Aprovar a classificação?${P.n_alertas ? `\n• ${P.n_alertas} resposta(s) com alerta` : ""}${naoConf ? `\n• ${naoConf} resposta(s) não conferidas por você (ficam como a IA classificou)` : ""}`)) return;
    refresh(await post(`/api/pergunta/${P.qid}/aprovar`, {}, "Gravando nos resultados…")); toast("Classificação aprovada");
  });
}

// ---------------------------------------------------------------- tabela de classificação
const temSugestao = (r) => r.revisao === "pendente" && r.auditoria?.ok === false && r.auditoria.primaria != null && r.auditoria.primaria !== r.primaria;
function situacaoOk(r, s) {
  if (!s) return true;
  if (s === "nao") return r.primaria == null;
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
    (!q || (r.texto + " " + (r.justificativa || "")).toLowerCase().includes(q)) &&
    (!f.cat || String(r.primaria) === f.cat || String(r.secundaria) === f.cat) &&
    (!f.alertas || (r.alertas && r.alertas !== "não codificado")) &&
    (!f.comentarios || r.comentario) &&
    situacaoOk(r, f.situacao));
  const conf = (r) => (r.primaria == null ? 9 : r.revisao !== "pendente" ? 2 + (r.confianca ?? 0) : r.confianca ?? 0);
  const faixaConf = (r) => Math.floor(conf(r) * 10);  // agrupa em faixas de 10% para poder desempatar por categoria
  const k = f.ordem;
  const conferida = (r) => (r.revisao === "confirmada" || r.revisao === "corrigida" ? 1 : 0);  // conferidas sempre no fim
  rows.sort((a, b) => conferida(a) - conferida(b) ||
    (k === "conf" ? faixaConf(a) - faixaConf(b) || (a.primaria ?? 999) - (b.primaria ?? 999) || conf(a) - conf(b) || b.n - a.n
    : k === "n" ? b.n - a.n
    : (a.primaria ?? 999) - (b.primaria ?? 999) || b.n - a.n));
  state.ordemFixa = rows.map((r) => r.rid);
  return rows;
}
function renderCodificacao() {
  const P = state.P, cats = catsValidas(), n = P.respostas?.n_respondeu || 0, f = state.filtro, locked = P.codificacao.status === "aprovado";
  const ordem = [...cats].map((c) => ({ c, m: (P.contagens[c.codigo]?.primaria || 0) + (P.contagens[c.codigo]?.secundaria || 0) })).sort((a, b) => b.m - a.m);
  const maxm = Math.max(1, ...ordem.map((o) => o.m));
  const chart = ordem.map(({ c, m }) => `<div class="row"><div class="n" title="${esc(c.nome)}">${esc(c.nome)}</div><div class="bar"><i style="width:${(100 * m) / maxm}%"></i><span>${m} · ${pct(m, n)}</span></div></div>`).join("");
  const optCat = (sel, vazio) => (vazio ? `<option value="">${esc(vazio)}</option>` : "") + cats.map((c) => `<option value="${c.codigo}" ${c.codigo === sel ? "selected" : ""}>${c.codigo} · ${esc(c.nome)}</option>`).join("");
  const todas = filtrarItens(), vis = todas.slice(0, state.mostrar);
  // sub-filtro por categoria (visível ao ordenar por confiança): conta ignorando o filtro de categoria em si
  const chipsCat = (() => {
    if (f.ordem !== "conf") return "";
    const q = f.q.toLowerCase(), conta = new Map();
    P.itens.forEach((r) => {
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
    const cls = [r.alertas && !nc ? "alerta" : "", r.revisao === "corrigida" ? "humano" : "", r.revisao === "confirmada" ? "confirmada" : "", r.comentario_pendente ? "pendente" : "", nc ? "naocod" : ""].join(" ");
    const origem = nc ? '<span class="pill">não classificada</span>' : r.revisao === "corrigida" ? `<span class="pill human" title="${r.corrigido_de_nome ? "A IA tinha posto: " + esc(r.corrigido_de_nome) : ""}">✎ você</span>`
      : r.revisao === "confirmada" ? (r.validado_por === "auto" ? `<span class="pill ok auto" title="Confirmada sozinha: confiança alta e o auditor concordou">⚡ auto</span>` : '<span class="pill ok">✓ conferida</span>')
      : r.ia_original_nome ? `<span class="pill acc" title="O auditor corrigiu; a IA tinha posto: ${esc(r.ia_original_nome)}">revisor</span>`
      : r.origem === "regra" ? '<span class="pill">regra</span>' : r.origem === "llm+comentario" ? '<span class="pill acc">IA + comentário</span>' : r.origem === "erro" ? '<span class="pill warn">erro</span>' : '<span class="pill">IA</span>';
    // justificativa: sugestões já adotadas (supervisor.py) guardam o texto do revisor; mostra rotulado
    const just = r.justificativa ? (r.ia_original_nome ? `<small>revisor: ${esc(r.justificativa.replace(/^\[revisor [^:]*: ?/, "").replace(/\] IA tinha: .*$/, ""))} · a IA tinha posto: ${esc(r.ia_original_nome)}</small>` : `<small>IA: ${esc(r.justificativa)}</small>`) : "";
    const sugestao = !locked && temSugestao(r) ? `<div class="sugestao">🔎 auditor sugere: <b>${esc(r.sugestao_nome || r.auditoria.primaria)}</b>${r.sugestao_sec_nome ? ` + ${esc(r.sugestao_sec_nome)}` : ""}${r.auditoria.nota ? ` — ${esc(r.auditoria.nota)}` : ""} <button class="btn sm c-sug" title="Aceitar a sugestão do auditor (tecla S)">aceitar sugestão</button></div>` : "";
    const btnOk = nc || locked || r.revisao === "corrigida" ? "" : r.revisao === "confirmada" ? `<button class="btn sm c-ok on" title="Desfazer confirmação">✓</button>` : `<button class="btn sm c-ok" title="A IA acertou — confirmar">✓</button>`;
    return `<tr class="${cls}" data-rid="${r.rid}" tabindex="0">
      <td>${btnOk}</td>
      <td>${origem}</td>
      <td><div class="txt-resp${r.texto.length > 280 ? " longa" : ""}" title="${r.texto.length > 280 ? "clique para ver a resposta inteira" : ""}">${esc(r.texto)}</div>${just}${sugestao}${r.alertas && !nc ? `<br><span class="pill warn">${esc(r.alertas)}</span>` : ""}${r.corrigido_de_nome ? `<br><small>a IA tinha posto: ${esc(r.corrigido_de_nome)}</small>` : ""}</td>
      <td class="num">${r.n}</td>
      <td><select class="cat c-prim">${nc ? `<option value="" selected>— escolha —</option>` : ""}${optCat(r.primaria, null)}</select></td>
      <td><select class="cat c-sec" ${nc ? "disabled" : ""}>${optCat(r.secundaria, "— nenhuma —")}</select></td>
      <td class="num">${r.confianca == null || nc ? "" : Number(r.confianca).toFixed(2)}</td>
      <td><textarea class="inline c-com" rows="1" ${nc ? "disabled" : ""} placeholder="O que está errado? (a IA reclassifica)">${esc(r.comentario || "")}</textarea>${r.comentario && !r.comentario_pendente ? `<small>já aplicado</small>` : ""}</td>
    </tr>`;
  }).join("");
  const pendVis = vis.filter((r) => r.revisao === "pendente").length;
  return `
    <div class="chart">${chart}</div>
    <div class="tools">
      <input id="c-q" placeholder="buscar texto…" value="${esc(f.q)}">
      <select id="c-sit">
        <option value="">todas as situações</option>
        <option value="pendente" ${f.situacao === "pendente" ? "selected" : ""}>a conferir</option>
        <option value="confirmada" ${f.situacao === "confirmada" ? "selected" : ""}>confirmadas ✓ (todas)</option>
        <option value="humano" ${f.situacao === "humano" ? "selected" : ""}>confirmadas por pessoas</option>
        <option value="auto" ${f.situacao === "auto" ? "selected" : ""}>confirmadas automaticamente ⚡</option>
        <option value="discorda" ${f.situacao === "discorda" ? "selected" : ""}>auditor discordou 🔎</option>
        <option value="corrigida" ${f.situacao === "corrigida" ? "selected" : ""}>corrigidas por você</option>
        <option value="nao" ${f.situacao === "nao" ? "selected" : ""}>não classificadas</option>
      </select>
      <select id="c-cat"><option value="">todas as categorias</option>${cats.map((c) => `<option value="${c.codigo}" ${String(c.codigo) === f.cat ? "selected" : ""}>${c.codigo} · ${esc(c.nome)}</option>`).join("")}</select>
      <label><input type="checkbox" id="c-al" ${f.alertas ? "checked" : ""}> só alertas</label>
      <label><input type="checkbox" id="c-com" ${f.comentarios ? "checked" : ""}> só comentadas</label>
      <select id="c-ord"><option value="conf" ${f.ordem === "conf" ? "selected" : ""}>ordenar: menor confiança</option><option value="n" ${f.ordem === "n" ? "selected" : ""}>ordenar: mais frequentes</option><option value="cat" ${f.ordem === "cat" ? "selected" : ""}>ordenar: categoria</option></select>
      <span class="small">${vis.length} de ${todas.length} respostas${todas.length !== P.itens.length ? ` (filtradas de ${P.itens.length})` : ""}</span>
      ${!locked && pendVis ? `<button class="btn sm" id="c-ok-todas" title="Confirma as respostas 'a conferir' mostradas nesta página">✓ Confirmar as ${pendVis} mostradas</button>` : ""}
    </div>
    ${chipsCat}
    ${painelDiscordancias}
    <table id="tab-cod"><thead><tr><th style="width:44px" title="Confirmar que a IA acertou">OK</th><th style="width:96px">Situação</th><th>Resposta <small>(e justificativa da IA)</small></th><th class="num" style="width:40px">n</th><th style="width:18%">Categoria principal</th><th style="width:16%">Secundária</th><th class="num" style="width:54px">Conf.</th><th style="width:19%">Comentário para a IA</th></tr></thead><tbody>${rows}</tbody></table>
    ${todas.length > vis.length ? `<div class="tools"><button class="btn" id="c-mais">Mostrar mais ${Math.min(POR_PAGINA, todas.length - vis.length)}</button><span class="small">${todas.length - vis.length} restantes</span></div>` : ""}
    <div class="small atalhos">⌨ <b>Atalhos</b> (clique numa linha primeiro): <kbd>↑</kbd>/<kbd>↓</kbd> ou <kbd>J</kbd>/<kbd>K</kbd> navegar · <kbd>Enter</kbd> confirmar ✓ e ir para a próxima · <kbd>0</kbd>–<kbd>99</kbd> código da categoria · <kbd>C</kbd> comentar (<kbd>Ctrl+Enter</kbd> salva) · <kbd>S</kbd> aceitar sugestão do auditor.</div>
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
  $("#c-sit").onchange = (e) => mudaFiltro("situacao", e.target.value);
  $("#c-cat").onchange = (e) => mudaFiltro("cat", e.target.value);
  $("#c-al").onchange = (e) => mudaFiltro("alertas", e.target.checked);
  $("#c-com").onchange = (e) => mudaFiltro("comentarios", e.target.checked);
  $("#c-ord").onchange = (e) => mudaFiltro("ordem", e.target.value);
  document.querySelectorAll(".chip-cat[data-cat]").forEach((b) => (b.onclick = () => mudaFiltro("cat", state.filtro.cat === b.dataset.cat ? "" : b.dataset.cat)));
  $("#c-cat-limpar")?.addEventListener("click", () => mudaFiltro("cat", ""));
  $("#c-mais")?.addEventListener("click", () => { state.mostrar += POR_PAGINA; state.congelar = true; rerender(); });
  $("#c-ok-todas")?.addEventListener("click", async () => {
    const rids = [...document.querySelectorAll("#tab-cod tbody tr")].map((tr) => +tr.dataset.rid).filter((rid) => state.P.itens.find((i) => i.rid === rid)?.revisao === "pendente");
    const r = await post(`/api/pergunta/${P.qid}/validar`, { rids, valor: true }, "Confirmando…");
    toast(`${r.alterados} resposta(s) confirmada(s)`); refresh(r);
  });
  document.querySelectorAll(".b-aceitar-grupo").forEach((btn) => {
    btn.onclick = async () => {
      const rids = btn.dataset.rids.split(",").map(Number);
      const paraCod = +btn.dataset.paracod;
      btn.disabled = true;
      btn.textContent = "Gravando…";
      for (const rid of rids) {
        const item = state.P.itens.find((i) => i.rid === rid);
        const res = await post(`/api/pergunta/${P.qid}/item/${rid}`, {
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
  const locked = P.codificacao.status === "aprovado";
  let numBuf = "", numTimer = null;
  for (const tr of $("#tab-cod tbody").rows) {
    const rid = +tr.dataset.rid, r = state.P.itens.find((i) => i.rid === rid);
    const prim = tr.querySelector(".c-prim"), sec = tr.querySelector(".c-sec"), com = tr.querySelector(".c-com"), ok = tr.querySelector(".c-ok");
    if (locked) { prim.disabled = sec.disabled = com.disabled = true; continue; }
    const salvar = async (body, msg, proxima = false) => {
      const antes = r.revisao, seguinte = proximaLinha(tr, 1)?.dataset.rid;
      tr.classList.add("just-confirmed");
      const res = await post(`/api/pergunta/${P.qid}/item/${rid}`, body);
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
        if (r.revisao === "pendente") salvar({ validado: true }, "Confirmada ✓", true);
        else proximaLinha(tr, 1)?.focus();
      } else if (keyLow === "c" && !com.disabled) { e.preventDefault(); com.focus(); }
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
      <div class="perigo-item"><div class="d"><b>Excluir este projeto do Tabulador</b><small>Tira “${esc(P.nome)}” da lista de projetos. A pasta do projeto e a planilha não são apagadas (dá para cadastrar de novo). Opcionalmente, move a pasta de resultados para <code>…_excluido_&lt;data&gt;</code>.</small></div>
        <button class="btn perigo" id="pz-b4" ${G.n_projetos > 1 ? "" : 'disabled title="É o único projeto: crie outro antes"'}>Excluir projeto</button></div>
    </div>`;
  document.querySelector("[data-acao=pasta]").onclick = () => post("/api/abrir-pasta");
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
  sel.innerHTML = lista.map((m) => `<option value="${esc(m)}">${m === "padrao" ? "padrão do programa" : esc(m)}</option>`).join("")
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

// altura real da barra do topo (quebra em 2 linhas em telas estreitas): usada pelos cabeçalhos fixos
function medirTopo() { document.documentElement.style.setProperty("--topo", $(".top").offsetHeight + "px"); }
window.addEventListener("resize", medirTopo);

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
$("#btn-teste").onclick = () => alternarTeste(!state.status.ia.modo_teste);
$("#teste-sair").onclick = () => alternarTeste(false);
$("#teste-limpar").onclick = async () => {
  if (!confirm("Apagar todos os dados do MODO TESTE deste projeto (categorias, classificações e resultados simulados)?\nOs resultados reais não são afetados.")) return;
  await post("/api/modo-teste/limpar", {}, "Apagando dados de teste…"); toast("Dados de teste apagados");
  state.qid = null; await carregarStatus(); irPara(null); renderPainel();
};
$("#btn-ia").onclick = abrirIA;
$("#btn-load").onclick = recarregarPlanilha;
$("#li-painel").onclick = () => irPara(null);
$("#li-usage").onclick = () => { if (location.hash === "#usage") renderUsage(); else location.hash = "usage"; };
$("#li-resultados").onclick = () => { if (location.hash === "#resultados") renderResultados(); else location.hash = "resultados"; };
$("#li-gerenciar").onclick = () => { if (location.hash === "#gerenciar") renderGerenciar(); else location.hash = "gerenciar"; };
$("#sel-projeto").onchange = async (e) => {
  await post("/api/projeto", { slug: e.target.value }, "Trocando de projeto…");
  state.qid = null; await carregarStatus();
  if (["#usage", "#resultados", "#gerenciar", "#painel", ""].includes(location.hash)) rota(); else irPara(null);
};

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
$("#btn-novo").onclick = () => { if (location.hash === "#novo") renderNovo(); else location.hash = "novo"; };

// ---------------------------------------------------------------- rotas / boot
function rota() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (state.qid && h !== state.qid) pararPresenca();
  if (h === "novo") renderNovo();
  else if (h === "usage") renderUsage();
  else if (h === "resultados") renderResultados();
  else if (h === "gerenciar") renderGerenciar();
  else if (h && h !== "painel" && state.status.perguntas.some((s) => s.qid === h)) abrir(h);
  else renderPainel();
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
})();
