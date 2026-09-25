---
id: PEND-09
titulo: Identificação de quem está logado (pessoa ou IA) e sidebar mostrando onde cada um está no projeto
modulo_afetado: [tabulador, app.py, app.js, nuvem.py, config.py]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-24
data_resolucao: 2026-09-25
resumo: "Ideia do Gabriel: hoje o Tabulador identifica quem está usando a máquina pelo login do Windows (config.USUARIO, usado só para avisar de edição simultânea numa mesma pergunta — ver a presença por pergunta implementada em 2026-09-24). Faltava: (1) identificação explícita na tela inicial; (2) uma sidebar mostrando, para todo o projeto, onde cada pessoa/IA está agora. Desenhado pelo conselho de IAs e implementado em 25/09: nome autodeclarado + sessão por aba + lista de presença no painel lateral esquerdo (não direito — ver nota de escopo); presença de IA via CLI ficou deliberadamente fora, é gambiarra sem heartbeat real de processo."
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

## Resolução (2026-09-25) — implementado (menor passo viável)
Rodei o conselho de IAs (Arquiteto/Crítico/Pragmático/Rubber Duck, 2 rodadas — transcrição completa em
`jumppi/_general/conselho/rodadas/20260925_154901_pend-09-desenhar-sem-implementar-ainda-identificacao-explici.md`).
O Crítico achou dois furos reais na primeira proposta (sessão fixa por CLI colidindo entre operadores
diferentes; `sessao_id` só em `localStorage` "teleportando" entre abas do mesmo navegador) que o
Pragmático incorporou sem inchar o escopo. Desenho final, implementado como está:

- **Tabela nova** `presenca_projeto` em `nuvem.py` (`sessao_id, nome_exibicao, origem, localizacao,
  atualizado_em`) — **aditiva**, não mexe na tabela `presenca` (por pergunta) que já está em produção
  durante o campo; decisão de segurança minha, não do conselho, por causa do momento (PEND-01/03).
- **Identificação**: modal de 1 campo ("Como você quer aparecer?"), sem dropdown de tipo/modelo — pede
  uma vez, guarda em `localStorage`. Uma IA rodando pelo navegador digita "IA: Claude" etc.
- **`sessao_id`**: gerado em memória (`crypto.randomUUID()`) a cada carregamento de página — por ABA,
  nunca persistido — resolve o teleporte entre abas que o Crítico apontou.
- **Sidebar**: virou um bloco na nav lateral **esquerda** já existente (`#bloco-presenca-projeto`),
  não uma coluna nova à direita como o pedido original imaginava — layout novo de coluna ficaria fora
  do "menor passo", registrado aqui como desvio consciente do pedido original.
- **IA via CLI**: fora do escopo funcional, como o Pragmático cortou — o schema já tem `origem`
  (`browser`|`cli`) pronto pra quando alguém desenhar heartbeat de processo de verdade (zumbi/crash
  cleanup, que o Crítico apontou como não-trivial); hoje só "browser" é populado.
- Sem detector de ociosidade (mouse/teclado) — cortado pelo Pragmático como over-engineering; mesmo
  comportamento "solta em 30s sem heartbeat" que já existia na presença por pergunta.

Código: `tabulador/src/nuvem.py` (tabela + `marcar_presenca_projeto`/`sair_presenca_projeto`),
`tabulador/app.py` (`POST /api/presenca`, `POST /api/presenca/sair`), `tabulador/static/app.js`
(`SESSAO_ID`, `garantirIdentificacao`, `iniciarPresencaProjeto`), `tabulador/templates/index.html`
(`#dlg-identificacao`, `#bloco-presenca-projeto`). Testado com `tests/test_nuvem.py` (4 testes novos)
e suíte completa.
