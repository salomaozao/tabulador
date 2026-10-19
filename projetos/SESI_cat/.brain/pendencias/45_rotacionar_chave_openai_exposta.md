---
id: PEND-45
titulo: Rotacionar a chave da OpenAI que apareceu na saída do terminal em 02/10
objetivo_relacionado: OBJ-03
modulo_afetado: [credenciais]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Ao conferir um .env gerado por engano dentro de uma worktree, o conteúdo (com a chave TABULADOR_CHAVE_OPENAI da equipe) foi impresso no terminal da sessão do Claude porque a ocultação com sed não funcionou. A cópia local foi apagada e nenhum arquivo com a chave existe mais na worktree, mas a chave ficou registrada no histórico da conversa. A conta já estava sem créditos (a PEND-04 teve um incidente parecido). Recomendação: gerar chave nova e atualizar na Central Canônica."
linear: JUM-29
---

# PEND-45: Rotacionar a chave da OpenAI

- **Origem:** um clique por script num botão escondido do app (instância de teste na worktree) ativou o "modo teste", e o app gravou `tabulador/.env` na worktree com a chave copiada do `.env` da equipe. Ao listar o arquivo, o terminal mostrou a chave.
- **Contenção feita:** `.env` da worktree apagado; worktree removida; nada foi commitado (o `.env` é ignorado pelo git); nenhuma outra cópia encontrada.
- **Ação (Gabriel):** gerar chave nova na OpenAI, atualizar no `.env` da equipe / Central Canônica (`G:\Meu Drive\Gabriel\_general\credentials\`) e revogar a antiga.
- **Prevenção:** ao inspecionar `.env`, nunca imprimir valores; usar `grep -c` ou listar só os nomes das variáveis. O app grava `.env` na pasta do código quando se liga o modo teste: não clicar em botões por script sem identificar qual é.
