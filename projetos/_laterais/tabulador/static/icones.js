/* Troca emojis coloridos por ícones SVG de traço (currentColor), conforme o DESIGN.md.
   Roda sobre o texto já renderizado (MutationObserver); o texto-fonte do app não muda. */
(function () {
  const P = {
    link: '<path d="M6.5 9.5a2.5 2.5 0 0 0 3.5 0l2-2a2.5 2.5 0 0 0-3.5-3.5l-.7.7M9.5 6.5a2.5 2.5 0 0 0-3.5 0l-2 2a2.5 2.5 0 0 0 3.5 3.5l.7-.7"/>',
    busca: '<circle cx="7" cy="7" r="4"/><path d="M10 10l3.5 3.5"/>',
    frasco: '<path d="M6.5 2.5h3M7 2.5v4L3.5 12a1 1 0 0 0 .9 1.5h7.2a1 1 0 0 0 .9-1.5L9 6.5v-4"/>',
    ideia: '<path d="M6 12h4M6.5 14h3M8 2a4 4 0 0 0-2 7.5V11h4V9.5A4 4 0 0 0 8 2z"/>',
    brilho: '<path d="M8 2l1.5 4.5L14 8l-4.5 1.5L8 14l-1.5-4.5L2 8l4.5-1.5z"/>',
    robo: '<rect x="3" y="5" width="10" height="7.5" rx="1.8"/><path d="M8 5V2.8"/><circle cx="6" cy="8.7" r=".6" fill="currentColor"/><circle cx="10" cy="8.7" r=".6" fill="currentColor"/>',
    pasta: '<path d="M2 4.5a1 1 0 0 1 1-1h3l1.5 1.5H13a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z"/>',
    pulso: '<path d="M1.5 8h3l1.5-4 3 8 1.5-4h4"/>',
    pino: '<path d="M6 2.5h4l-.5 4 2 2.5H4.5l2-2.5zM8 9v4.5"/>',
    relogio: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3l2 1.5"/>',
    alvo: '<circle cx="8" cy="8" r="5.5"/><circle cx="8" cy="8" r="2.2"/>',
    bandeira: '<path d="M4 14V2.5M4 3h8l-1.5 2.5L12 8H4"/>',
    caixa: '<path d="M2.5 5.5 8 2.5l5.5 3v5L8 13.5l-5.5-3zM2.5 5.5 8 8.5l5.5-3M8 8.5v5"/>',
    olho: '<path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z"/><circle cx="8" cy="8" r="2"/>',
    queda: '<path d="M2.5 4.5 6 8l2.5-2.5 5 6M10.5 11.5h3v-3"/>',
    lixo: '<path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.5 9h6l.5-9"/>',
    barras: '<path d="M2.5 13.5h11M4.5 11V7.5M8 11V3.5M11.5 11V6"/>',
    aviso: '<path d="M8 2.5l6 10.5H2zM8 7v3M8 11.5v.01"/>',
    tela: '<rect x="2" y="3" width="12" height="8" rx="1"/><path d="M6 13.5h4"/>',
    texto: '<path d="M2.5 12.5 6 3.5l3.5 9M3.8 9.5h4.4M11 12.5V7.5a2 2 0 0 1 3 0"/>',
    moeda: '<circle cx="8" cy="8" r="5.5"/><path d="M9.8 6.2c-.4-.6-1-.9-1.8-.9-1 0-1.7.5-1.7 1.2 0 1.8 3.6.8 3.6 2.6 0 .7-.8 1.2-1.9 1.2-.8 0-1.5-.3-1.9-.9M8 4v8"/>',
    foguete: '<path d="M5 11l6-6M6 5h5v5"/>',
    livros: '<path d="M3 3v10M6.5 3v10M10 4l3 .8-2 8.4-3-.8z"/>',
    trofeu: '<path d="M5 2.5h6v4a3 3 0 0 1-6 0zM5 4H3v1a2 2 0 0 0 2 2M11 4h2v1a2 2 0 0 1-2 2M8 9.5v2.5M5.5 13.5h5"/>',
    vassoura: '<path d="M9 2.5l3 3-4.5 4.5-3-3zM4.5 10l-2 3.5 3.5-1"/>',
    cadeado: '<rect x="3.5" y="7" width="9" height="6.5" rx="1"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/>',
    atualizar: '<path d="M13 8a5 5 0 1 1-1.5-3.5M13 2.5v3h-3"/>',
  };
  const MAPA = {
    "🔗": "link", "🔎": "busca", "🔍": "busca", "🧪": "frasco", "💡": "ideia", "🧠": "brilho", "🤖": "robo",
    "🗂": "pasta", "📂": "pasta", "🩺": "pulso", "📌": "pino", "🕘": "relogio", "🎯": "alvo", "🏁": "bandeira",
    "📦": "caixa", "👁": "olho", "👀": "olho", "📉": "queda", "🗑": "lixo", "📊": "barras", "🚧": "aviso",
    "💻": "tela", "🔤": "texto", "💰": "moeda", "🚀": "foguete", "📚": "livros", "🏆": "trofeu", "🧹": "vassoura",
    "🔒": "cadeado", "🔄": "atualizar",
  };
  const MEDALHA = { "🥇": "1", "🥈": "2", "🥉": "3" };
  const RE = /[\u{1F300}-\u{1FAFF}]️?/gu;
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "OPTION", "SELECT", "INPUT", "TITLE", "SVG", "CODE", "PRE"]);

  function svg(chave, rotulo) {
    const base = 'class="ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"';
    if (rotulo) {
      return `<svg ${base} fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="6"/><text x="8" y="11.2" text-anchor="middle" font-size="8.5" font-weight="700" fill="currentColor" stroke="none">${rotulo}</text></svg>`;
    }
    return `<svg ${base} fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${P[chave]}</svg>`;
  }

  function trocar(no) {
    const t = no.nodeValue;
    RE.lastIndex = 0;
    if (!RE.test(t)) return;
    RE.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let ultimo = 0, m;
    while ((m = RE.exec(t))) {
      if (m.index > ultimo) frag.appendChild(document.createTextNode(t.slice(ultimo, m.index)));
      const e = m[0].replace("️", "");
      const html = MEDALHA[e] ? svg(null, MEDALHA[e]) : MAPA[e] ? svg(MAPA[e]) : "";
      if (html) {
        const tpl = document.createElement("template");
        tpl.innerHTML = html;
        frag.appendChild(tpl.content.firstChild);
      }
      ultimo = m.index + m[0].length;
    }
    if (ultimo < t.length) frag.appendChild(document.createTextNode(t.slice(ultimo)));
    no.parentNode.replaceChild(frag, no);
  }

  function varrer(raiz) {
    if (raiz.nodeType === 3) {
      if (raiz.parentNode && !SKIP.has(raiz.parentNode.nodeName.toUpperCase())) trocar(raiz);
      return;
    }
    if (raiz.nodeType !== 1 || SKIP.has(raiz.nodeName.toUpperCase())) return;
    const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (SKIP.has(n.parentNode.nodeName.toUpperCase()) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    const lista = [];
    while (w.nextNode()) lista.push(w.currentNode);
    lista.forEach(trocar);
  }

  function iniciar() {
    varrer(document.body);
    new MutationObserver((muts) => {
      for (const mu of muts) {
        if (mu.type === "characterData") varrer(mu.target);
        else mu.addedNodes.forEach(varrer);
      }
    }).observe(document.body, { childList: true, characterData: true, subtree: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
