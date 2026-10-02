---
id: PEND-37
titulo: (Ideia futura) Exibição de dados de uso do modelo, tokens e custo estimado por pergunta e no consolidado
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, usage, app.py, static/app.js, templates/index.html]
criticidade: baixa
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Ideia guardada para evolução: expor métricas de uso de IA (modelo utilizado, total de tokens de prompt e conclusão, tempo de execução e custo estimado em R$/US$) diretamente nos cards do Painel Geral, no cabeçalho de cada pergunta e na aba de Resultados/Exportações, permitindo auditoria de custo por projeto e transparência operacional."
---

# PEND-37: (Ideia futura) Exibição de dados de uso de modelo, tokens e custo estimado

## Contexto & Visão:
Hoje o Tabulador já possui um módulo interno de consumo (`src/usage.py` e aba `/api/usage`) que lê os logs em `output/llm_log/` e estima custos com base na tabela de preços por milhão de tokens. No entanto, essas informações estão confinadas a uma aba técnica separada ("Consumo da IA") e não estão visíveis no fluxo cotidiano do pesquisador nem nos relatórios de entrega.

O objetivo desta ideia é trazer a **transparência de consumo de IA para o primeiro plano**, integrando métricas de uso (qual modelo rodou, volume de tokens consumidos e custo financeiro estimado) diretamente onde o trabalho acontece.

## Ideias de Aplicação:
1. **No Card da Pergunta (Painel Geral e Cabeçalho Interno):**
   - Exibir uma pílula compacta de telemetria ao lado do status da pergunta:
     - Ex.: `⚡ gemini-2.5-flash · 42k tokens · ~R$ 0,18`.
   - Permite ao pesquisador saber instantaneamente o peso computacional de cada questão aberta.
2. **Na Aba Resultados e Relatórios Executivos:**
   - Adicionar uma seção ou bloco resumo: *"Investimento Computacional / IA"*:
     - Total de chamadas, volume total de tokens (entrada vs. saída), modelo(s) empregados e custo consolidado em R$.
     - Útil para prestação de contas, orçamentação de novas pesquisas e auditoria de margem de projetos.
3. **Na Barra Fixa de Revisão:**
   - Mostrar o custo acumulado daquela pergunta (indução do quadro + classificação + auditoria).
4. **Armazenamento Estruturado por Pergunta:**
   - Persistir em `codificacao.json` (ou metadados da pergunta) o consolidado da última rodada:
     ```json
     "telemetria_ia": {
       "modelo": "google/gemini-2.5-flash",
       "prompt_tokens": 35200,
       "completion_tokens": 6800,
       "custo_estimado_brl": 0.22,
       "tempo_total_segundos": 14.5
     }
     ```

## Status:
- Guardado como ideia futura / reflexão estratégica (OBJ-03).
- Não implementar imediatamente; amadurecer junto da telemetria detalhada de auditoria (PEND-26 / PEND-27).

## Requisito adicional (02/10): custo estimado "como se fosse API" para as IAs por CLI
- **Pedido do Gabriel:** ter um valor estimado de custo também para o uso das IAs por CLI (`cli_claude`, `cli_codex`, `cli_gemini`, `cli_agy`), que não cobram por token (usam a assinatura), para dar uma noção do que o mesmo trabalho custaria na API.
- **O que já existe:** `src/llm_cli.py` devolve tokens por chamada para Claude (`_uso_claude`, com `custo_usd_cli` do próprio programa) e Antigravity (`_uso_agy`); `src/usage.py` já calcula `usd` = tokens × `PRECOS[modelo]`. O que falta é o modelo dessas chamadas casar com a tabela `PRECOS` (hoje sem Claude, e o nome vem do CLI) e a tela mostrar o valor com o rótulo "estimado (equivale à API)", separado do gasto real das chaves de API.
- **Cuidados:** os tokens de prompt do CLI incluem ~25 mil tokens de prompt de agente por chamada (ver `llm_cli.py`), o que infla a estimativa; tokens em cache têm preço menor na API. Decidir se o valor usa só entrada e saída sem o prompt do agente, ou o total com cache. Codex e Gemini CLI podem não devolver tokens (conferir); sem tokens, estimar por caracteres, como já faz o modo teste.
- **Dependência:** esta ideia fica junto da PEND-26 (telemetria por modelo), para o custo ser por `classificado_por`.
