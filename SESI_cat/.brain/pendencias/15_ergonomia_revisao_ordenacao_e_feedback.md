---
id: PEND-15
titulo: Botão "Aprovar e gravar nos resultados" sempre à mão (barra fixa no topo da pergunta)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js, static/app.css]
criticidade: alta
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
prazo: 2026-10-02
data_resolucao: 2026-10-01
resumo: "Em 30/09 o botão saiu do fim da tabela e foi para junto de 'Classificar as restantes' (ainda sem commit). Mesmo assim ele fica abaixo do quadro de categorias inteiro (tabela + saúde + 'Pedir ajuste à IA'), e o usuário ainda precisa rolar muito. Solução: uma barra fixa (sticky) no topo da área da pergunta, com o resumo da revisão, '👁 ver as N a conferir' e '✓ Aprovar e gravar'."
---

# PEND-15: Aprovar sempre à mão

Arquivo estava vazio no disco (criado em 30/09). Reescrito em 01/10: US-04 do PRD `ciclos/2026-09-30_feedbacks_sara` + reforço do Gabriel ("o usuário não deveria precisar subir tanto").

- **Implementado em 01/10:**
  - `renderRevbar()` passa a utilizar container `.revbar-sticky` com `position: sticky; top: var(--topo, 49px); z-index: 4;`.
  - A barra reúne em duas linhas compactas: linha 1 com resumo da revisão (conferidas, manual, ⚡ auto, corrigidas, taxa de acerto da IA, atalho "👁 ver as N a conferir") e o botão `${renderAprovarBtn()}` ancorado na ponta direita; linha 2 com o progresso de classificadas e barra empilhada.
  - O botão Aprovar mantém todas as travas (desabilitado se faltam respostas a classificar com tooltip claro) e exibe estado de já aprovado nos resultados.
  - Adicionado atalho extra no cabeçalho da pergunta: link "↓ ir para a revisão" com rolagem suave direta até `#area-revisao`.
  - `.q-cab` desancorado do modo sticky para permitir leitura leve, e `table.res th` ajustado com `top: calc(var(--topo, 49px) + var(--revbar-h, 66px))` para não cobrir nem ser coberto pelo thead da tabela de respostas.
