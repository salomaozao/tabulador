/* Categorizador — front-end (vanilla JS, sem build). */
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (n, d) => (d ? Math.round((100 * n) / d) + "%" : "–");
const POR_PAGINA = 100;

const filtroInicial = () => ({ q: "", cat: "", alertas: false, comentarios: false, situacao: "", ordem: "conf" });
const state = { view: "painel", status: null, qid: null, P: null, filtro: filtroInicial(), mostrar: POR_PAGINA, amostra: 50 };

// ---------------------------------------------------------------- infra
let progT;
function busy(msg, progresso = false) {
  $("#busy-msg").textContent = msg || "Processando…"; $("#busy-prog").textContent = "";
  $("#busy-bar").classList.add("hidden"); $("#busy-bar").firstElementChild.style.width = "0%";
  $("#busy").classList.remove("hidden");
  clearInterval(progT);
  if (progresso) progT = setInterval(async () => {
    try {
      const p = await (await fetch("/api/progresso")).json();
      if (p.ativo && p.total) {
        $("#busy-prog").textContent = `${p.feitos} de ${p.total} respostas (${pct(p.feitos, p.total)})${p.erros ? ` · ${p.erros} lote(s) com erro` : ""}${p.limite_atingido ? " · limite do provedor atingido, parando…" : ""}`;
        $("#busy-bar").classList.remove("hidden");
        $("#busy-bar").firstElementChild.style.width = `${Math.min(100, (100 * p.feitos) / p.total)}%`;
      }
    } catch (e) { /* ignora */ }
  }, 1500);
}
function idle() { clearInterval(progT); $("#busy").classList.add("hidden"); }
let toastT;
function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.add("hidden"), err ? 9000 : 2800);
}
async function api(path, opts = {}, msg, progresso = false) {
  if (msg) busy(msg, progresso);
  try {
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts }).catch(() => {
      // "Failed to fetch": o servidor não respondeu (janela do programa fechada ou reiniciada)
      throw new Error("o Categorizador não respondeu — a janela do programa foi fechada ou reiniciada. Abra-o de novo pelo atalho e recarregue a página.");
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
  $("#base-status").innerHTML = b.carregada
    ? `Base: <b>${b.n}</b> respondentes · atualizada ${b.atualizada_em} · IA: ${S.ia.tem_chave ? esc(S.ia.modelo) + (S.ia.provedor !== "openai" ? ` <small>(${esc(S.ia.provedor)})</small>` : "") : '<span class="pill warn">sem chave</span>'}`
    : `<span class="pill warn">Base ainda não carregada</span>`;
  document.title = `${S.ia.modo_teste ? "🧪 TESTE · " : ""}Categorizador · ${S.projeto.nome}`;
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
  const linhaRes = (tipo, titulo, desc) => {
    const r = R[tipo]; if (!r) return "";
    return `<tr><td><b>${titulo}</b><br><small>${desc}</small></td><td>${r.existe ? `atualizado ${esc(r.atualizado_em)}` : '<span class="small">ainda não gerado</span>'}</td>
      <td class="acoes">${tipo !== "base" ? `<button class="btn sm" data-gerar="${tipo}">${r.existe ? "↻ Atualizar" : "Gerar"}</button>` : ""} ${r.existe ? `<a class="btn sm primary" href="/arquivo/${tipo}">⬇ Baixar</a>` : ""}</td></tr>`;
  };
  $("#main").innerHTML = `
    <h1>${esc(S.projeto.nome)}</h1>
    <div class="small">Planilha-fonte: ${esc(b.fonte)}</div>
    ${avisos.join("")}
    <h2>Perguntas abertas <small>${aprovadas} de ${S.perguntas.length} aprovadas</small></h2>
    <div class="cards">${cards}</div>
    <h2>Resultados <span class="acoes"><button class="btn" data-acao="pasta">📂 Abrir pasta de resultados</button></span></h2>
    <div class="info">Os resultados usam apenas as perguntas <b>aprovadas</b>. Depois de aprovar ou corrigir algo, clique em “Atualizar”.</div>
    <table class="res"><tbody>
      ${linhaRes("planilha", "Planilha final categorizada", "a planilha original com as colunas de categoria preenchidas (e a secundária ao lado)")}
      ${linhaRes("codebook", "Codebook", "todas as variáveis, valores e as categorias de cada pergunta aberta")}
      ${linhaRes("cruzamentos", "Cruzamentos (tabelas)", "% de cada pergunta por perfil (banners), uma aba por pergunta")}
      ${linhaRes("base", "Base processada", "uma linha por respondente, com os códigos das categorias")}
    </tbody></table>`;
  document.querySelectorAll(".card").forEach((c) => (c.onclick = () => irPara(c.dataset.qid)));
  document.querySelectorAll("[data-acao=ia]").forEach((b) => (b.onclick = abrirIA));
  document.querySelectorAll("[data-acao=load]").forEach((b) => (b.onclick = recarregarPlanilha));
  document.querySelector("[data-acao=pasta]").onclick = () => post("/api/abrir-pasta");
  document.querySelectorAll("[data-gerar]").forEach((btn) => (btn.onclick = async () => {
    const tipo = btn.dataset.gerar;
    const r = await post(`/api/gerar/${tipo}`, {}, tipo === "planilha" ? "Gerando a planilha final… (pode levar até 1 minuto)" : "Gerando… (pode levar alguns segundos)");
    state.status.resultados = r.resultados; renderPainel(); toast("Pronto! Clique em Baixar.");
  }));
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
}
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
  let cod = 0, conf = 0, corr = 0, corrIA = 0;
  for (const r of P.itens) {
    for (const [k, campo] of [[r.primaria, "primaria"], [r.secundaria, "secundaria"]]) {
      if (k == null) continue;
      cont[k] = cont[k] || { primaria: 0, secundaria: 0 }; cont[k][campo] += r.n;
    }
    if (r.primaria == null) continue;
    cod++;
    if (r.revisao === "confirmada") conf++;
    if (r.revisao === "corrigida") { corr++; if (r.corrigido_de_nome != null) corrIA++; }
  }
  P.contagens = cont;
  P.n_alertas = P.itens.filter((r) => r.alertas && r.alertas !== "não codificado").length;
  P.n_comentarios_pendentes = P.itens.filter((r) => r.comentario_pendente).length;
  const aval = conf + corrIA, tot = P.itens.length;
  P.revisao = { n_unicas: tot, n_codificadas: cod, n_faltantes: tot - cod, n_confirmadas: conf, n_corrigidas: corr, n_revisadas: conf + corr, acerto_ia: aval ? conf / aval : null, n_avaliadas_ia: aval };
}
function aplicarItem(r, it) {
  Object.assign(r, {
    primaria: it.primaria, secundaria: it.secundaria, origem: it.origem, confianca: it.confianca,
    comentario: it.comentario || null, comentario_pendente: !!it.comentario && !it.comentario_aplicado_em,
    revisao: it.primaria == null ? null : it.origem === "humano" ? "corrigida" : it.validado ? "confirmada" : "pendente",
    corrigido_de_nome: it.corrigido_de != null ? nomeCat(it.corrigido_de) : null,
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
  `;
  $("#instr").onblur = async (e) => { if (e.target.value !== P.instrucoes) { await post(`/api/pergunta/${P.qid}/instrucoes`, { texto: e.target.value }); P.instrucoes = e.target.value; toast("Instruções salvas"); } };
  $("#b-induzir")?.addEventListener("click", async () => {
    if (F && !confirm("Gerar do zero substitui as categorias atuais" + (C ? " e a classificação terá de ser refeita" : "") + ". Para ajustes pontuais, use 'Pedir ajuste à IA'. Continuar?")) return;
    refresh(await post(`/api/pergunta/${P.qid}/frame/induzir`, {}, "A IA está lendo as respostas e propondo categorias… (até 1 minuto)"));
  });
  $("#b-aprovar-frame")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/frame/aprovar`, {}, "Aprovando…")));
  $("#b-reabrir")?.addEventListener("click", async () => refresh(await post(`/api/pergunta/${P.qid}/reabrir`, {}, "Reabrindo…")));
  bindFrame(); bindAcoesCod(); bindCodificacao();
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
        <div><b>Revisão:</b> ${V.n_revisadas} de ${V.n_codificadas} classificadas conferidas (${pct(V.n_revisadas, V.n_codificadas)}) · <span class="pill ok">✓ ${V.n_confirmadas} confirmadas</span> <span class="pill human">✎ ${V.n_corrigidas} corrigidas</span>
        ${acerto != null ? ` · <b>a IA acertou ${acerto}%</b> <small>(de ${V.n_avaliadas_ia} conferidas)</small>` : ""}</div>
        <div class="prog"><i style="width:${V.n_codificadas ? (100 * V.n_revisadas) / V.n_codificadas : 0}%"></i></div>
      </div>
      <div class="small">Loop: confirme ✓ o que está certo · corrija na hora pelo menu · ou escreva um comentário e clique em <b>Reclassificar comentadas</b>. Se o erro se repete, ajuste as <b>instruções</b> ou as <b>categorias</b> e clique em <b>Reclassificar tudo</b> (o que você corrigiu/confirmou é mantido).</div>
      <div class="tools">
        <button class="btn primary" id="b-recod-com" ${P.n_comentarios_pendentes ? "" : "disabled"}>✨ Reclassificar comentadas (${P.n_comentarios_pendentes})</button>
        <button class="btn" id="b-recod-tudo" title="Refaz com a IA tudo que você ainda não conferiu">↻ Reclassificar tudo</button>
        ${V.n_faltantes ? `<span class="sep"></span><button class="btn" id="b-mais">+ Classificar mais ${tam}</button><button class="btn primary" id="b-restantes">Classificar as restantes (${V.n_faltantes})</button>` : ""}
        <span class="sep"></span>
        <button class="btn ok" id="b-aprovar-cod" ${V.n_faltantes ? `disabled title="Classifique as restantes antes de aprovar"` : ""}>✓ Aprovar e gravar nos resultados</button>
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
  $("#b-aprovar-cod")?.addEventListener("click", async () => {
    const V = P.revisao, naoConf = V.n_codificadas - V.n_revisadas;
    if (!confirm(`Aprovar a classificação?${P.n_alertas ? `\n• ${P.n_alertas} resposta(s) com alerta` : ""}${naoConf ? `\n• ${naoConf} resposta(s) não conferidas por você (ficam como a IA classificou)` : ""}`)) return;
    refresh(await post(`/api/pergunta/${P.qid}/aprovar`, {}, "Gravando nos resultados…")); toast("Classificação aprovada");
  });
}

// ---------------------------------------------------------------- tabela de classificação
function filtrarItens() {
  // depois de confirmar/corrigir uma linha a ordem fica CONGELADA (a linha não pula de lugar nem some
  // do filtro); só reordena/refiltra quando o pesquisador muda filtro/ordenação ou recarrega
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
    (!f.situacao || (f.situacao === "nao" ? r.primaria == null : r.revisao === f.situacao)));
  const conf = (r) => (r.primaria == null ? 9 : r.revisao !== "pendente" ? 2 + (r.confianca ?? 0) : r.confianca ?? 0);
  const k = f.ordem;
  rows.sort((a, b) => k === "conf" ? conf(a) - conf(b) || b.n - a.n : k === "n" ? b.n - a.n : (a.primaria ?? 999) - (b.primaria ?? 999) || b.n - a.n);
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
  const rows = vis.map((r) => {
    const nc = r.primaria == null;
    const cls = [r.alertas && !nc ? "alerta" : "", r.revisao === "corrigida" ? "humano" : "", r.revisao === "confirmada" ? "confirmada" : "", r.comentario_pendente ? "pendente" : "", nc ? "naocod" : ""].join(" ");
    const origem = nc ? '<span class="pill">não classificada</span>' : r.revisao === "corrigida" ? `<span class="pill human" title="${r.corrigido_de_nome ? "A IA tinha posto: " + esc(r.corrigido_de_nome) : ""}">✎ você</span>` : r.revisao === "confirmada" ? '<span class="pill ok">✓ conferida</span>' : r.origem === "regra" ? '<span class="pill">regra</span>' : r.origem === "llm+comentario" ? '<span class="pill acc">IA + comentário</span>' : r.origem === "erro" ? '<span class="pill warn">erro</span>' : '<span class="pill">IA</span>';
    const btnOk = nc || locked || r.revisao === "corrigida" ? "" : r.revisao === "confirmada" ? `<button class="btn sm c-ok on" title="Desfazer confirmação">✓</button>` : `<button class="btn sm c-ok" title="A IA acertou — confirmar">✓</button>`;
    return `<tr class="${cls}" data-rid="${r.rid}" tabindex="0">
      <td>${btnOk}</td>
      <td><div class="txt-resp${r.texto.length > 280 ? " longa" : ""}" title="${r.texto.length > 280 ? "clique para ver a resposta inteira" : ""}">${esc(r.texto)}</div>${r.justificativa ? `<small>IA: ${esc(r.justificativa)}</small>` : ""}${r.alertas && !nc ? `<br><span class="pill warn">${esc(r.alertas)}</span>` : ""}${r.corrigido_de_nome ? `<br><small>a IA tinha posto: ${esc(r.corrigido_de_nome)}</small>` : ""}</td>
      <td class="num">${r.n}</td>
      <td><select class="cat c-prim">${nc ? `<option value="" selected>— escolha —</option>` : ""}${optCat(r.primaria, null)}</select></td>
      <td><select class="cat c-sec" ${nc ? "disabled" : ""}>${optCat(r.secundaria, "— nenhuma —")}</select></td>
      <td class="num">${r.confianca == null || nc ? "" : Number(r.confianca).toFixed(2)}</td>
      <td><textarea class="inline c-com" rows="1" ${nc ? "disabled" : ""} placeholder="O que está errado? (a IA reclassifica)">${esc(r.comentario || "")}</textarea>${r.comentario && !r.comentario_pendente ? `<small>já aplicado</small>` : ""}</td>
      <td>${origem}</td>
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
        <option value="confirmada" ${f.situacao === "confirmada" ? "selected" : ""}>confirmadas ✓</option>
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
    <table id="tab-cod"><thead><tr><th style="width:44px" title="Confirmar que a IA acertou">OK</th><th>Resposta <small>(e justificativa da IA)</small></th><th class="num" style="width:40px">n</th><th style="width:18%">Categoria principal</th><th style="width:16%">Secundária</th><th class="num" style="width:54px">Conf.</th><th style="width:19%">Comentário para a IA</th><th style="width:96px">Situação</th></tr></thead><tbody>${rows}</tbody></table>
    ${todas.length > vis.length ? `<div class="tools"><button class="btn" id="c-mais">Mostrar mais ${Math.min(POR_PAGINA, todas.length - vis.length)}</button><span class="small">${todas.length - vis.length} restantes</span></div>` : ""}
    <div class="small atalhos">⌨ <b>Atalhos</b> (clique numa linha da tabela primeiro): <kbd>↑</kbd><kbd>↓</kbd> navegar · <kbd>Enter</kbd> confirmar ✓ e ir para a próxima · <kbd>C</kbd> escrever comentário · <kbd>1</kbd>–<kbd>9</kbd> trocar a categoria principal pelo código.</div>
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
  // re-renderiza mantendo a ordem e a linha `rid` no mesmo lugar da tela
  const rerenderNaLinha = (rid) => {
    const antes = document.querySelector(`#tab-cod tr[data-rid="${rid}"]`)?.getBoundingClientRect().top;
    state.congelar = true; manterScroll(render);
    const depois = document.querySelector(`#tab-cod tr[data-rid="${rid}"]`)?.getBoundingClientRect().top;
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
  $("#c-mais")?.addEventListener("click", () => { state.mostrar += POR_PAGINA; state.congelar = true; rerender(); });
  $("#c-ok-todas")?.addEventListener("click", async () => {
    const rids = [...document.querySelectorAll("#tab-cod tbody tr")].map((tr) => +tr.dataset.rid).filter((rid) => state.P.itens.find((i) => i.rid === rid)?.revisao === "pendente");
    const r = await post(`/api/pergunta/${P.qid}/validar`, { rids, valor: true }, "Confirmando…");
    toast(`${r.alterados} resposta(s) confirmada(s)`); refresh(r);
  });
  const locked = P.codificacao.status === "aprovado";
  for (const tr of $("#tab-cod tbody").rows) {
    const rid = +tr.dataset.rid, r = state.P.itens.find((i) => i.rid === rid);
    const prim = tr.querySelector(".c-prim"), sec = tr.querySelector(".c-sec"), com = tr.querySelector(".c-com"), ok = tr.querySelector(".c-ok");
    if (locked) { prim.disabled = sec.disabled = com.disabled = true; continue; }
    const salvar = async (body, msg, proxima = false) => {
      const res = await post(`/api/pergunta/${P.qid}/item/${rid}`, body);
      aplicarItem(r, res.item); recalcular(); rerenderNaLinha(rid); toast(msg);
      // devolve o foco à tabela para continuar pelo teclado
      const atual = document.querySelector(`#tab-cod tr[data-rid="${rid}"]`);
      (proxima ? proximaLinha(atual, 1) : atual)?.focus({ preventScroll: false });
    };
    tr.onkeydown = (e) => {
      if (e.target !== tr) return;  // digitando num campo: não interfere
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); proximaLinha(tr, e.key === "ArrowDown" ? 1 : -1)?.focus(); }
      else if (e.key === "Enter" && r.primaria != null) {
        e.preventDefault();
        if (r.revisao === "pendente") salvar({ validado: true }, "Confirmada ✓", true);
        else proximaLinha(tr, 1)?.focus();
      } else if (e.key.toLowerCase() === "c" && !com.disabled) { e.preventDefault(); com.focus(); }
      else if (/^[1-9]$/.test(e.key)) {
        const cat = catsValidas().find((c) => c.codigo === +e.key);
        if (cat && cat.codigo !== r.primaria) { e.preventDefault(); salvar({ primaria: cat.codigo }, `Categoria principal: ${cat.nome}`); }
      }
    };
    com.addEventListener("keydown", (e) => { if (e.key === "Escape") { com.blur(); tr.focus(); } });
    prim.onchange = () => prim.value && salvar({ primaria: prim.value }, "Categoria principal alterada");
    sec.onchange = () => salvar({ secundaria: sec.value || null }, "Categoria secundária alterada");
    com.onchange = () => salvar({ comentario: com.value }, com.value.trim() ? "Comentário salvo — clique em 'Reclassificar comentadas' para a IA aplicar" : "Comentário removido");
    com.addEventListener("focus", () => { com.rows = 3; }); com.addEventListener("blur", () => { com.rows = 1; });
    ok?.addEventListener("click", () => salvar({ validado: r.revisao !== "confirmada" }, r.revisao === "confirmada" ? "Confirmação desfeita" : "Confirmada ✓"));
  }
}

// ---------------------------------------------------------------- topo: projeto, IA, planilha
async function recarregarPlanilha() {
  if (!confirm("Reler a planilha-fonte e reconstruir a base? As classificações aprovadas são reaplicadas automaticamente.")) return;
  const r = await post("/api/load", {}, "Lendo a planilha…"); toast(`Base carregada: ${r.n} respondentes`);
  await carregarStatus(); rota();
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
          solucao: "Confira se a janela do Categorizador continua aberta; se não, abra-o pelo atalho e recarregue a página." };
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
async function renderUsage() {
  state.view = "usage"; state.qid = null; state.P = null; renderSidebar();
  $("#main").innerHTML = `<div class="empty">Carregando consumo…</div>`;
  const U = await api("/api/usage?ultimas=200"), T = U.total;
  const semPreco = T.sem_preco ? `<div class="small">${T.sem_preco} chamada(s) de modelo sem preço de referência (não entram no custo).</div>` : "";
  const linha = (r, primeira) => `<tr><td>${primeira}</td><td class="num">${fmtN(r.chamadas)}${r.erros ? ` <small class="warn-t">(${r.erros} erro${r.erros > 1 ? "s" : ""})</small>` : ""}</td><td class="num">${fmtN(r.prompt)}</td><td class="num">${fmtN(r.completion)}</td><td class="num"><b>${fmtN(r.total)}</b></td><td class="num">${fmtTempo(r.segundos)}</td><td class="num">${fmtUSD(r.usd)}</td><td class="num">${fmtBRL(r.brl)}</td></tr>`;
  const cab = (p) => `<thead><tr><th>${p}</th><th class="num">Chamadas</th><th class="num">Tokens entrada</th><th class="num">Tokens saída</th><th class="num">Total</th><th class="num">Tempo</th><th class="num">Custo (US$)</th><th class="num">Custo (R$)</th></tr></thead>`;
  const maxT = Math.max(1, ...U.por_pergunta.map((r) => r.total));
  const L = U.limite_diario;
  const gauge = L.limite
    ? `<div class="tile grande"><div class="l">Limite diário de chamadas — ${esc(L.nome_provedor)}</div><div class="v">${L.pct}%</div><div class="small">${fmtN(L.usado_hoje)} de ${fmtN(L.limite)} chamadas hoje (estimativa do plano gratuito)</div><div class="prog" style="margin-top:8px"><i style="width:${Math.min(100, L.pct)}%"></i></div></div>`
    : `<div class="tile grande"><div class="l">Limite diário — ${esc(L.nome_provedor)}</div><div class="v">${fmtN(L.usado_hoje)}</div><div class="small">chamadas hoje · sem limite diário fixo conhecido para este provedor</div></div>`;
  $("#main").innerHTML = `
    <div class="small"><a href="#painel">← Painel geral</a></div>
    <h1>Consumo da IA <small>${esc(U.projeto)}</small></h1>
    <div class="small">${T.chamadas ? `De ${esc(T.primeira)} a ${esc(T.ultima)}` : "Nenhuma chamada registrada ainda neste projeto."} · custo é <b>estimativa</b> (tabela de preços de referência em <code>usage.py</code>; câmbio US$ 1 = R$ ${String(U.cambio).replace(".", ",")})</div>
    <div class="tools"><button class="btn" id="u-atualizar">↻ Atualizar dados de consumo</button></div>
    <div class="tiles">
      <div class="tile grande"><div class="l">Total de tokens usados</div><div class="v">${fmtN(T.total)}</div><div class="small">${fmtN(T.prompt)} de entrada + ${fmtN(T.completion)} de saída</div></div>
      ${gauge}
    </div>
    <div class="tiles">
      <div class="tile"><div class="l">Chamadas</div><div class="v">${fmtN(T.chamadas)}</div><div class="small">${T.taxa_sucesso == null ? "" : Math.round(100 * T.taxa_sucesso) + "% com sucesso"}</div></div>
      <div class="tile"><div class="l">Tokens de entrada</div><div class="v">${fmtN(T.prompt)}</div></div>
      <div class="tile"><div class="l">Tokens de saída</div><div class="v">${fmtN(T.completion)}</div></div>
      <div class="tile"><div class="l">Tempo de IA</div><div class="v">${fmtTempo(T.segundos)}</div><div class="small">soma das chamadas</div></div>
      <div class="tile"><div class="l">Custo estimado</div><div class="v">${fmtBRL(T.brl)}</div><div class="small">${fmtUSD(T.usd)}</div></div>
    </div>
    ${semPreco}
    <h2>Por modelo</h2>
    <table class="usage">${cab("Modelo")}<tbody>${U.por_modelo.map((r) => linha(r, `<b>${esc(r.modelo)}</b>${r.preco ? `<br><small>US$ ${r.preco[0]} / ${r.preco[1]} por 1M tokens (entrada / saída)</small>` : "<br><small>sem preço de referência</small>"}`)).join("") || `<tr><td colspan="8" class="small">—</td></tr>`}</tbody></table>
    <h2>Por pergunta e operação</h2>
    <table class="usage">${cab("Pergunta · operação")}<tbody>${U.por_pergunta.map((r) => linha(r, `<b>${esc(r.pergunta)}</b> · ${esc(r.operacao)}<div class="prog"><i style="width:${(100 * r.total) / maxT}%"></i></div>`)).join("") || `<tr><td colspan="8" class="small">—</td></tr>`}</tbody></table>
    <h2>Tokens por dia</h2>
    <table class="usage">${cab("Dia")}<tbody>${U.por_dia.map((r) => linha(r, `<b>${esc(r.dia)}</b>`)).join("") || `<tr><td colspan="8" class="small">—</td></tr>`}</tbody></table>
    <h2>Chamadas recentes <small>(últimas ${U.ultimas.length})</small></h2>
    <div class="scroll-y"><table class="usage"><thead><tr><th>Quando</th><th>Pergunta · operação</th><th>Modelo</th><th class="num">Entrada</th><th class="num">Saída</th><th class="num">Tempo</th><th class="num">Custo (US$)</th><th>Situação</th></tr></thead><tbody>
      ${U.ultimas.map((c) => `<tr><td class="num">${esc(c.quando)}</td><td>${esc(c.pergunta)} · ${esc(c.operacao)}</td><td>${esc(c.modelo)}${c.provedor !== "openai" ? ` <small>(${esc(c.provedor)})</small>` : ""}</td><td class="num">${fmtN(c.prompt)}</td><td class="num">${fmtN(c.completion)}</td><td class="num">${c.segundos.toFixed(1).replace(".", ",")} s</td><td class="num">${fmtUSD(c.usd)}</td><td>${c.ok ? '<span class="pill ok">ok</span>' : `<span class="pill warn" title="${esc(c.erro || "")}">erro</span>`}</td></tr>`).join("") || `<tr><td colspan="8" class="small">—</td></tr>`}
    </tbody></table></div>`;
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
$("#sel-projeto").onchange = async (e) => {
  await post("/api/projeto", { slug: e.target.value }, "Trocando de projeto…");
  state.qid = null; await carregarStatus();
  if (location.hash === "#usage") renderUsage(); else if (location.hash === "#painel" || !location.hash) renderPainel(); else irPara(null);
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
      <code>_laterais/categorizador</code>. A IA segue o roteiro de <code>.claude/skills/novo-projeto/SKILL.md</code>
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
      <pre class="pedido-skill">Crie um projeto novo no Categorizador com a planilha &lt;caminho da planilha.xlsx&gt;, seguindo a skill novo-projeto.</pre>
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
    state.novo.validacao = await post("/api/novo/validar", { pasta: state.novo.pasta, projeto: state.novo.projeto }, "Validando (lendo a planilha como o categorizador vai ler)…");
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
  if (h === "novo") renderNovo();
  else if (h === "usage") renderUsage();
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
