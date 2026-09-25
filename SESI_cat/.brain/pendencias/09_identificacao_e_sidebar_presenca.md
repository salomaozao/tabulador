---
id: PEND-09
titulo: Identificação de quem está logado (pessoa ou IA) e sidebar mostrando onde cada um está no projeto
modulo_afetado: [tabulador, app.py, app.js, nuvem.py, config.py]
criticidade: baixa
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-24
resumo: "Ideia do Gabriel: hoje o Tabulador identifica quem está usando a máquina pelo login do Windows (config.USUARIO, usado só para avisar de edição simultânea numa mesma pergunta — ver a presença por pergunta implementada em 2026-09-24). Falta: (1) uma identificação explícita na tela inicial — a pessoa se apresenta (ou diz que é uma IA, ex. 'Claude', 'Codex') em vez de confiar só no login do SO; (2) uma sidebar à direita mostrando, para todo o projeto, onde cada pessoa/IA está agora (em qual pergunta, ou no painel/resultados), não só um aviso dentro da pergunta aberta."
---

# PEND-09: Identificação de sessão + sidebar de presença do projeto inteiro

## Contexto
Em 2026-09-24 foi implementada a presença **por pergunta**: `nuvem.py` ganhou uma tabela `presenca`
(`marcar_presenca`/`sair_presenca`, heartbeat a cada 12s do navegador, janela de 30s) e a tela de
revisão mostra um aviso ("⚠ Fulano também está revisando esta pergunta agora...") quando outra pessoa
está na mesma pergunta ao mesmo tempo — só isso, sem visão do projeto inteiro. A identidade usada é
`config.USUARIO` (login do Windows, ou `TABULADOR_USUARIO` no `.env` se quiser outro nome), sem tela de
login nem distinção entre pessoa e IA.

Nessa mesma conversa o Gabriel comentou que **outras IAs (Codex, Antigravity, Gemini) também mexem no
projeto direto pelo código/CLI**, não só pela interface — então "quem está" não é só quem abriu o
navegador.

## Ideia (ainda não desenhada)
1. Tela inicial pede para a pessoa se identificar (nome, ou "sou uma IA: Claude/Codex/..."), em vez de
   assumir o login do Windows — cobre o caso de máquina compartilhada ou de IA rodando via terminal.
2. Sidebar à direita (ou um painel) mostrando, para o projeto inteiro, uma lista "quem está onde agora"
   (pergunta X, painel geral, resultados...), não só o aviso pontual dentro de uma pergunta.
3. Em aberto: como uma IA que roda por fora da interface (CLI, terminal) se anunciaria nessa mesma lista
   — hoje a presença só é marcada pelo heartbeat do navegador (`app.js`); um agente mexendo direto nos
   arquivos/no `codeframe.py` não passa por ali.

## Próximo passo
Quando for retomar: decidir se a identificação vale a pena (troca simplicidade por fricção de login) e
desenhar como estender `nuvem.marcar_presenca` para o projeto inteiro (não só por `qid`) antes de montar
a sidebar. Só registro da ideia — não implementar sem o Gabriel priorizar.

## Atualização 2026-09-25
O lado *dev/CLI* do item 3 (como uma IA que roda por fora da interface se anuncia) ganhou uma resposta
parcial fora deste escopo de produto: `jumppi/COMUNICACAO_IAS.md` agora é um log de mensagens
`INÍCIO`/`FIM` (qualquer IA — Claude Code, Codex, Antigravity, Gemini — anuncia lá o que vai mexer),
com `tabulador/.claude/scripts/coordenacao_ias.py` cruzando isso com `git worktree`/`git status` reais.
Isso resolve coordenação entre IAs mexendo em código, mas continua sem tela/sidebar dentro do próprio
Tabulador para quem usa o navegador — itens 1 e 2 desta pendência continuam em aberto.
