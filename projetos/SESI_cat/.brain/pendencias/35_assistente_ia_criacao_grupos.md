---
id: PEND-35
titulo: Assistente de IA na criação de grupos (rótulo, escopo, instrucoes_frame e compatibilidade semântica)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, grupos_frame, app.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Substitui a sugestão estatística cega de pares de perguntas por um assistente de IA sob demanda na criação do grupo. O pesquisador seleciona as perguntas e a IA analisa enunciados e micro-amostras de respostas reais para gerar nome semântico, descrição, diretrizes metodológicas para o codeframe compartilhado (instrucoes_frame) e diagnóstico de compatibilidade."
linear: JUM-21
---

# PEND-35: Assistente de IA na criação e configuração de grupos de perguntas

## Contexto & Dor:
- **Heurística de pares cega:** Anteriormente, `grupos_frame.sugerir()` tentava adivinhar quais perguntas agrupar apenas procurando pares com bases quase disjuntas. Isso gerava ruído e sugestões irrelevantes, pois quem conhece a intenção analítica é o pesquisador.
- **Vácuo de assistência na configuração:** Ao criar o grupo manualmente, o pesquisador precisava redigir do zero o nome do grupo e as diretrizes do quadro compartilhado (`instrucoes_frame`), ou acabava com rótulos mecânicos concatenados (ex.: "Q32 / Q33").
- **Necessidade de taxonomia orientada:** Perguntas agrupadas compartilham o mesmo quadro de categorias. Sem boas instruções de indução, a IA corre o risco de criar categorias desbalanceadas ou misturar múltiplos atributos num mesmo código.

## Decisão de Produto & Metodologia:
1. **Seleção humana soberana:** O pesquisador marca na interface as perguntas que deseja unificar. A seção de "Sugestões de grupos" baseada em sobreposição estatística é descontinuada da UI.
2. **Aporte cognitivo da IA:** Quando 2 ou mais perguntas são marcadas, o botão `✨ Analisar e preencher com IA` é liberado. A IA recebe os enunciados, o contexto da pesquisa e uma micro-amostra de respostas reais tabuladas de cada pergunta, devolvendo:
   - **Nome / Rótulo do grupo:** nome executivo conciso em português (máx. 60 caracteres), sem códigos "Q".
   - **Descrição do grupo:** síntese de 1 a 2 frases destacando o construto em comum e as características de cada base.
   - **Instruções metodológicas (`instrucoes_frame`):** diretrizes temáticas para o codeframe unificado, exigindo a regra *"uma categoria = um atributo"* e tratando vocabulário e neutralidade.
   - **Diagnóstico de compatibilidade:** avaliação semântica apontando divergências de polaridade (ex.: positivo vs. negativo) ou discrepâncias de granularidade.
3. **Liberdade total:** O usuário pode editar qualquer campo sugerido antes de gravar o grupo.

## Arquitetura & Implementação Planejada:
- **Documento de especificação completo:** [`tabulador/docs/IP_criacao_grupos_input_ia.md`](../../tabulador/docs/IP_criacao_grupos_input_ia.md).
- **Backend (`src/grupos_frame.py` e `app.py`):**
  - Rota `POST /api/grupos/analisar-ia` recebendo `{"perguntas": ["Q32", "Q33"]}`.
  - Extração de micro-amostras de 10 a 15 respostas reais de cada pergunta via `codeframe.preparar()`.
  - Chamada estruturada `llm.chamar_json(system, user, SCHEMA_ANALISE_GRUPO, nome="analise_grupo")`.
- **Frontend (`static/app.js` e `static/app.css`):**
  - Remoção visual da lista de sugestões estatísticas da aba Grupos.
  - Inclusão do botão `✨ Preencher detalhes com IA` nos cards de novo grupo e edição.
  - Preenchimento assistido nos campos com display do box de compatibilidade semântica.
- **Isolamento Multi-Agente:**
  - A ser implementado em worktree dedicada (`worktrees/tabulador-grupos-ia-input` na branch `feat/grupos-ia-input`) sem sobreposição com a `tabulador-grupos-f1` (que cuida do motor de indução e aprovações por pergunta).
