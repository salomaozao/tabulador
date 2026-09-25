---
id: PEND-10
titulo: Atalho "ver as N a conferir" na barra de revisão (filtra direto pro que precisa de atenção)
modulo_afetado: [tabulador, static/app.js, static/app.css]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-25
data_resolucao: 2026-09-25
resumo: "O conselho de IAs, ao ser perguntado qual a próxima melhoria de usabilidade de maior valor, convergiu em: a maior fricção hoje não é classificar, é achar o que precisa de olho humano no meio de uma tabela cheia de itens já aceitos automaticamente. Implementado como um botão-pílula clicável na barra de revisão da pergunta, que filtra a tabela direto pra 'a conferir' e rola até ela — reaproveitando 100% do filtro de situação que já existia (não foi preciso lógica nova)."
---

# PEND-10: Atalho "ver as N a conferir"

## Contexto
Rodei o conselho de IAs (`jumppi/_general/conselho`, 4 personas, 2 rodadas — transcrição completa em
`jumppi/_general/conselho/rodadas/20260925_161309_dado-o-estado-atual-do-tabulador-app-flask-de-categorizacao-.md`)
perguntando qual a próxima melhoria de maior valor pra investir, dado o estado atual do Tabulador.

O Arquiteto propôs uma "Fila de Revisão" cross-projeto/cross-pergunta; o Crítico apontou dois furos reais
(quebra de contexto cognitivo ao pular de projeto, e a complexidade real de unificar bancos por
projeto — nem todo mundo usa a nuvem Turso); o Pragmático cortou pro "menor passo real": um filtro
"Apenas para revisar" na própria tela da pergunta, reaproveitando o que já existe. O Rubber Duck fez a
pergunta certa: como o usuário sabe se o filtro tá ligado (risco de "ver só 5 e achar que terminou,
quando tem 195 escondidas")?

## O que eu descobri ao investigar o código (antes de implementar)
O app já tinha muito mais infraestrutura de filtro do que o conselho sabia (eles não tinham acesso ao
código, só ao meu resumo do estado do projeto): `state.filtro.situacao` já é um filtro existente com o
valor `"pendente"` já mapeado exatamente para "classificado mas ainda não conferido" (nem confirmado
nem corrigido) — `coding.situacao_revisao()`. Também já existe o mecanismo de "congelar a ordem" pra
uma linha não sumir/saltar quando o usuário confirma algo (preocupação que o Crítico levantou na rodada
2, achando que seria um problema novo — já estava resolvido).

Por isso o "menor passo real" ficou ainda menor do que o conselho imaginou: não precisei de nenhuma
lógica de filtro nova, só expor o que já existia com um atalho de um clique.

## Implementado
Botão-pílula `👁 ver as N a conferir` na barra de revisão (`renderAcoesCod()`), visível só quando há
pendentes (`V.n_codificadas - V.n_revisadas > 0`). Ao clicar: seta `state.filtro.situacao = "pendente"`
(mesmo valor que o dropdown "Situação" já usava), reseta a paginação, re-renderiza e rola suavemente até
a tabela. O contador "N a conferir" já fica sempre visível na barra de revisão mesmo sem clicar —
resolve a preocupação do Rubber Duck sem precisar de nada além do que a barra já mostrava.

Decisão consciente que diverge do debate do conselho: não implementei persistência do filtro entre
perguntas (ele volta a "todas" ao trocar de pergunta, comportamento já existente e inalterado) —
mantive o comportamento padrão atual em vez de arbitrar a divergência Arquiteto (reset por segurança)
vs. Crítico (manter ligado por fluidez) sem dado real de uso; fácil revisitar depois se incomodar na
prática.

Testado: `node --check`, suíte completa (75 testes, 0 falhas), e no navegador com Claude in Chrome
contra dados reais do SESI (copiados pra pasta isolada via `TABULADOR_OUTPUT`, nunca tocando o Turso de
produção) — cliquei no botão na pergunta Q30 (109 pendentes) e confirmei que o filtro aplicou, o
dropdown sincronizou e a contagem bateu (109), sem erro no console.
