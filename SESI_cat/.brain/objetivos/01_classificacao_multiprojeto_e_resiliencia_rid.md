---
id: OBJ-01
titulo: Classificação automatizada multi-projeto e resiliência de RID em nuvem
area: engenharia_dados
status: ativo
prioridade: alta
data_criacao: 2026-09-29
---

# OBJ-01: Classificação automatizada multi-projeto e resiliência de RID em nuvem

### 1. Contexto e Dor Atual (JTBD - Problem Space)
- **Cenário:** O tabulador/classificador do SESI CAT processa bases de acidentes e comunicações em escala multi-projeto.
- **A Dor Real:** Inconsistências de RID em sincronizações na nuvem e bugs de NaN no resumo geral paralisam pipelines de tabulação.
- **Impacto:** Atraso nas entregas de relatórios setoriais e risco de duplicidade de registros processados.

### 2. Ganhos Esperados (JTBD - Value & Relief)
- **Estabilidade:** Execuções repetíveis sem falhas de índice ou colunas nulas.
- **Isolamento multi-projeto:** Segurança de que o processamento de um cliente/projeto não afeta outros.
- **Transparência:** Resumos gerais limpos, sem valores espúrios.

### 3. Critérios de Vitória (DoD de Alto Nível)
- [ ] Módulo tabulador executando sem erros em todos os projetos mapeados.
- [ ] RIDs estáveis persistidos corretamente na nuvem.
- [ ] Tabela de resumo geral sem NaN ou cálculos quebrados.

### 4. Anti-Escopo / No-Gos (Shape Up - Limites Rígidos)
- ❌ Não alterar o formato de saída contratado sem alinhamento prévio.
- ❌ Não acoplar regras de um projeto específico no núcleo do categorizador genérico.
- ❌ **Não utilizar o "Custom Classifier" da OpenRouter:** Teste empírico de 30/09/2026 comprovou que é apenas um recurso de observabilidade para dashboards corporativos da nuvem. Não possui rota de API para retorno das tags para a aplicação, não permite exportação individual em CSV e impõe custo duplo de inferência. A categorização segue exclusivamente via inferência direta com prompt + JSON estruturado (`response_format={"type": "json_object"}`).

### 5. Rabbit Holes (Shape Up - Armadilhas Técnicas Conhecidas)
- ⚠️ **Colunas vazias no resumo geral:** Tratar adequadamente colunas ausentes em bases menores para não propagar NaN.
- ⚠️ **Concorrência de sincronização em nuvem:** Garantir atomicidade na escrita dos RIDs.

### 6. Validação dos Ganhos (Auditoria de Resultados)
- **Ganhos Obtidos vs Esperados:** [Preencher na conclusão].
- **Data de Validação:** Pendente
