---
id: PRD_2026-09-30_feedbacks_sara
ciclo: 2026-09-30_feedbacks_sara
data_criacao: 2026-09-30
autor: Product Manager (Antigravity)
objetivo_relacionado: OBJ-01
status: revisado
---

# PRD: Estabilidade de IA, Volumetria, Ergonomia e Métricas (Feedbacks Sara 30/09)

## 1. Contexto & Dor de Negócio (Problem Statement)
- **Problema:** Na sessão de testes reais de campo de 30/09/2026 entre Gabriel e Sara, falhas de chamadas à LLM gravaram centenas de respostas na categoria 'Outros' (97) com status `ERRO_LLM`, poluindo distribuições; perguntas volumosas (ex: Q35 com 4.515 respostas) dispararam lotes massivos sem confirmação nem abort limpo; respostas com erro ficaram presas em um limbo não listado nos filtros; o botão de aprovação ficava no final de páginas de 1.000+ linhas; as métricas do painel enfatizavam % de perguntas (38%) em vez de volume de respostas; e o menu de mesclagem bloqueava fundir categorias para NS/NR (98) ou Outros (97).
- **Impacto:** Risco de poluição da base do cliente, desperdício de dezenas de dólares em tokens de IA, lentidão e fricção ergonômica severa na reta final de entrega (prevista para sexta 02/10).
- **Ganhos Esperados:** Eliminação total de respostas falsas em Outros (zero perda de integridade), proteção com modal volumétrico antes de classificar >100 respostas, aprovação imediata no topo sticky, métricas do painel baseadas em volume de respostas conferidas e liberdade para mesclar em NS/NR.

## 2. User Stories & Requisitos Funcionais
- **US-01 (Integridade de Falha):** Como operador, se uma chamada de IA falhar ou for interrompida, quero que as respostas permaneçam pendentes puras sem código atribuído e sem poluir a categoria Outros (97).
- **US-02 (Guarda Volumétrica):** Como operador, ao clicar para classificar mais de 100 respostas, quero ver um modal de confirmação com quantidade de respostas, estimativa de tempo e de tokens antes de iniciar.
- **US-03 (Abort Resiliente):** Como operador, ao interromper um processamento em curso, quero que lotes concluídos sejam preservados e lotes pendentes sejam cancelados sem gerar erros gravados.
- **US-04 (Ergonomia de Aprovação):** Como revisor, quero que o botão de 'Aprovar e gravar nos resultados' fique no topo da tela (revbar sticky) para não precisar rolar até o fim da tabela.
- **US-05 (Métricas por Respostas):** Como gestor, quero ver no painel geral o % e a contagem de respostas únicas conferidas em destaque primário (ex: 76% · 4.440 de 5.856), com perguntas como métrica secundária.
- **US-06 (Mesclagem para NS/NR):** Como revisor, quero poder selecionar '98 · NS/NR' ou '97 · Outros' no menu de mesclar categoria.
- **US-07 (Refino com Split):** Como pesquisador, quero que o comando 'separe categoria X em Y e Z' desmembre o codeframe com feedback visual e confirmação de diff.

## 3. Requisitos Não-Funcionais
- **Performance:** Nenhuma lentidão na renderização da tabela ao fixar a revbar no topo.
- **Segurança & Privacidade:** Zero armazenamento de dados brutos ou credenciais em repositórios remotos.
- **Consistência:** Atualização atômica de arquivos locais e banco Turso com invalidação imediata de cache no frontend.

## 4. Anti-Escopo & No-Gos (Limites Rígidos)
- 🚫 **No-Go 1:** Não alterar o formato ou os nomes de colunas do arquivo final de entrega (`base_processamento_categorizada.xlsx`).
- 🚫 **No-Go 2:** Não reintroduzir Custom Classifiers da OpenRouter para o pipeline.
- 🚫 **No-Go 3:** Não fazer commits em lote (`git add .`); aplicar commits atômicos por sprint.

## 5. Critérios de Aceite
- [ ] Falha simulada de LLM não cria item em `codificacao.json` com `primaria: 97`.
- [ ] Modal de alerta aparece para lotes com mais de 100 pendentes.
- [ ] Dropdown de mesclagem exibe 97 e 98 como opções selecionáveis.
- [ ] Botão de aprovação renderizado na barra de revisão superior.
- [ ] Cabeçalho do painel geral destaca percentual de respostas revisadas.
- [ ] Suíte completa `unittest` executando com 100% de aprovação.

