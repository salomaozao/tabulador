---
id: PEND-36
titulo: Relatório síntese visual na aba Resultados (ideias, perfis de respondentes e verbatins vivos)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, resultados, app.py, static/app.js, static/app.css]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Criação de um relatório executivo visual integrado à aba Resultados do Tabulador, dispensando PDFs ou planilhas para a primeira leitura. Sintetiza em cards e gráficos web a relação entre ideias (elogios, dores, sugestões) e perfis de respondentes (cruzamentos de controle e NPS), acompanhados por verbatins reais para uso direto em apresentações."
---

# PEND-36: Relatório Síntese Visual na aba Resultados

## Contexto & Dor:
- **Aba de Resultados puramente operacional:** Hoje a tela de Resultados foca em entregar arquivos brutos para download (planilhas Excel, codebooks e cruzamentos) e indicadores de processo.
- **Distância entre categorização e insight executivo:** Para extrair o panorama da pesquisa para diretoria ou clientes, o pesquisador precisa abrir o Excel de cruzamentos e montar gráficos do zero.
- **Dilema Perfis vs. Ideias:** Apenas listar temas gerais gera uma visão genérica; apenas tabelar variáveis demográficas perde o fator humano. O valor analítico real surge na conexão: *Qual perfil de respondente está associado a qual dor ou demanda, e como eles expressam isso em suas próprias palavras?*

## Decisão de Produto & Metodologia:
1. **Solução 100% Web (Sem PDF / Biblioteca pesada):** Layout direto no navegador utilizando o próprio sistema de estilos do Tabulador (`app.css`), permitindo impressão nativa (Ctrl+P) ou captura de tela limpa para slides.
2. **Quatro Blocos Executivos Estruturados:**
   - **Sumário Estratégico (IA):** Alavanca principal (ponto forte), alerta crítico (maior atrito) e narrativa global executiva.
   - **Mapa de Ideias & Polaridade:** Volume e distribuição percentual de elogios, queixas e sugestões de melhoria.
   - **Perfis de Respondentes (Quem diz o quê):** Cruzamento das temáticas com variáveis de controle chave (NPS, cargos, segmentos ou banners pré-configurados).
   - **A Voz do Respondente:** Mural com citações literais (verbatins) expressivas ancoradas aos perfis dos respondentes.
3. **Eficiência de Tokens e Cache:** Executado sob demanda pelo usuário (botão *"Gerar / Atualizar Síntese"*), com persistência em `output/relatorio_sintese.json`.

## Arquitetura & Implementação Planejada:
- **Documento de especificação detalhado:** [`tabulador/docs/IP_relatorio_sintese_resultados.md`](../../tabulador/docs/IP_relatorio_sintese_resultados.md).
- **Backend (`src/relatorio_sintese.py` e `app.py`):**
  - Módulo de agregação de contingência entre variáveis aprovadas e banners de perfil.
  - Chamada estruturada com JSON Schema para a LLM (`llm.chamar_json`).
  - Endpoints `GET /api/relatorio/sintese` e `POST /api/relatorio/sintese/gerar`.
- **Frontend (`static/app.js` e `templates/index.html`):**
  - Sub-abas na visualização `#resultados`: *Relatório Executivo* vs. *Arquivos para Baixar*.
  - Componentes de cards de destaque, barras de frequência CSS e mural de verbatins.
- **Coordenação Multi-Agente:**
  - Nenhuma linha de código de execução tocada durante a atuação concorrente de outra IA no motor de grupos (`IP_grupos_de_perguntas.md`). Implementação aguardará janela isolada ou worktree dedicada.
