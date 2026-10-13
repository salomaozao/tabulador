# IP — Relatório Síntese Visual em Resultados (Ideias, Perfis e Verbatins)

Plano de implementação no formato MetaGPT (PM → Arquiteto → Engenheiro → QA).
Data: 2026-10-02 · Origem: alinhamento com Gabriel Nascimento · Memória: `tabulador-relatorio-sintese`.

---

## 1. Requisitos & Visão de Produto (PM)

### 1.1 Contexto e Dor Real
Após categorizar e aprovar as perguntas abertas de um projeto, a aba **Resultados** hoje entrega:
1. Indicadores de processo (nº de perguntas aprovadas, total de classificadas, acerto da IA).
2. Arquivos brutos para download (Planilha categorizada, Codebook, Tabelas de cruzamento e Base).
3. Uma seção tímida "Visão geral" com parágrafo corrido de IA e algumas barras soltas.

**A Lacuna:**
O pesquisador ou consultor conclui a categorização mas **ainda não tem um produto visual pronto para leitura rápida ou para apresentar ao cliente**. Ele é forçado a baixar o Excel de cruzamentos e montar gráficos do zero no PowerPoint para responder perguntas básicas de diretoria: *"O que eles mais falaram? Quem são os insatisfeitos? Quais frases ilustram isso?"*.

### 1.2 Premissas & Escopo
- **Visual e Simples:** 100% web direto no navegador (sem dependências pesadas de PDF backend, WeasyPrint ou headless browser).
- **Print & Slide Ready:** Layout modular em blocos e cards CSS prontos para Ctrl+P ou prints limpos para colar em apresentações.
- **Conexão Ideias + Perfis:** Não sintetizar apenas ideias genéricas ou perfis demográficos frios, mas sim a relação **[Perfil] $\rightarrow$ [Temática/Dor] $\rightarrow$ [Frase Emblemática]**.
- **Controle de Custo / Token:** Chamada de IA sob demanda com cache local persistido em `output/relatorio_sintese.json`.

---

## 2. PRD — Requisitos Funcionais & Estrutura da Página

### 2.1 Os 4 Pilares da Síntese
1. **Sumário Executivo Estratégico (IA):**
   - **Alavanca Principal:** O maior ponto forte / promotor identificado na pesquisa.
   - **Alerta Crítico:** A maior fricção / gargalo com impacto no negócio.
   - **Narrativa Global:** Síntese de 2 a 3 parágrafos objetivos articulando os achados de todas as perguntas abertas aprovadas.
2. **Mapa de Ideias & Polaridade:**
   - Elogios / Forças (Perguntas de satisfação e motivos positivos).
   - Dores / Queixas (Perguntas de insatisfação, motivos de detração).
   - Sugestões & Demandas de Futuro (Perguntas de melhoria).
   - Exibição em barras percentuais e volume absoluto ponderado.
3. **Perfis & Segmentos (Quem Diz o Quê):**
   - Cruzamento visual imediato das temáticas abertas com as variáveis-chave do projeto:
     - Promotores vs. Neutros vs. Detratores (quando houver pergunta numérica/NPS).
     - Segmentos/Banners de perfil configurados no projeto (ex.: Cargo, Região, Área).
   - Apontamento de contrastes estatísticos (ex.: *"Grupo Operacional foca 3x mais em infraestrutura que a Liderança"*).
4. **Voz do Respondente (Verbatins Vivos):**
   - Seleção curada das citações mais expressivas e representativas para cada grande tema.
   - Tags associadas em cada card de citação: Categoria + Perfil/Segmento do respondente.

---

## 3. Desenho de Arquitetura & Backend (Arquiteto)

### 3.1 Módulo `src/relatorio_sintese.py`
Responsável por consolidar os dados das perguntas aprovadas e comunicar-se com o provedor LLM.

- `_consolidar_dados_projeto() -> dict`:
  - Varre `_perguntas_aprovadas()`.
  - Agrupa temas e frequências relativas ponderadas.
  - Se houver banners definidos em `variables.BANNERS_PADRAO` ou variável com flag `nps: True`, extrai tabelas de contingência resumidas.
  - Seleciona candidatos a verbatins (respostas longas, ricas e bem classificadas).
- `_SCHEMA_RELATORIO`:
  ```json
  {
    "type": "object",
    "properties": {
      "alavanca_principal": {"type": "string"},
      "alerta_critico": {"type": "string"},
      "narrativa_geral": {"type": "string"},
      "destaques_por_perfil": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "perfil": {"type": "string"},
            "foco_principal": {"type": "string"},
            "comentario": {"type": "string"}
          },
          "required": ["perfil", "foco_principal", "comentario"]
        }
      },
      "citacoes_curadas": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "tema": {"type": "string"},
            "texto": {"type": "string"},
            "segmento": {"type": "string"}
          },
          "required": ["tema", "texto", "segmento"]
        }
      }
    },
    "required": ["alavanca_principal", "alerta_critico", "narrativa_geral", "destaques_por_perfil", "citacoes_curadas"],
    "additionalProperties": false
  }
  ```
- `sintese() -> dict`: Leitura de cache em `output/relatorio_sintese.json` + dados numéricos em tempo real.
- `gerar_sintese() -> dict`: Chamada estruturada `llm.chamar_json()` e gravação de cache com data/hora.

### 3.2 Rotas na API (`app.py`)
- `GET /api/relatorio/sintese`: Retorna estado atual do relatório.
- `POST /api/relatorio/sintese/gerar`: Dispara geração/atualização via IA com lock de progresso.

---

## 4. Frontend & Interface (Engenheiro UI)

### 4.1 Navegação em Resultados
Na tela de Resultados (`renderResultados` em `static/app.js`), criar alternância de sub-visões no topo:
- `[ 📊 Relatório Executivo ]` (Default após aprovações)
- `[ 📥 Arquivos & Exportações ]` (Planilhas, Codebook, Cruzamentos)

### 4.2 Componentes Visuais
- **Header:** Título do projeto, data de geração, botões `[🔄 Atualizar Síntese]`, `[📋 Copiar Resumo]` e `[🖨️ Imprimir / Salvar PDF]`.
- **KPI Cards Hero:** Dois cards de largura total ou 50/50 com badges verde (Alavanca) e vermelho/laranja (Ponto Crítico).
- **Grid de Temas:** Gráficos de barras nativos em CSS com barra de progresso colorida e contagem.
- **Matriz de Perfis:** Tabela ou cards comparativos contrastando percepções por público.
- **Mural de Citações:** Grid de cards com fundo suave, aspas estilizadas e rodapé com atributos do respondente.

---

## 5. Plano de Entrega e Coordenação Multi-Agente
1. **Isolamento de Branch:** Implementação ocorrerá na branch `feat/relatorio-sintese` ou após merge das tarefas de grupos (`feat/grupos-fase1`).
2. **Regressão Zero:** Nenhuma alteração afetará o motor de exportação de planilhas (`src/cruzamentos.py`, `src/planilha_final.py`).
