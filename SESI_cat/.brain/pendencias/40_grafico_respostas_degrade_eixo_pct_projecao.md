---
id: PEND-40
titulo: Gráfico de respostas conferidas com degradê verde, porcentagem no eixo Y e projeção de conclusão (3 cenários discretos)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js, static/app.css, src/historico.py]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "O gráfico de respostas conferidas no painel geral deve exibir a linha de evolução em verde com degradê escurecendo; inclusão de porcentagem no eixo Y e projeção em linha cinza com 3 cenários (otimista, neutro e pessimista) do ritmo de respostas, informando data estimada de conclusão de forma secundária e discreta."
---

# PEND-40: Gráfico de evolução de respostas com degradê, eixo percentual e projeção de ritmo

## Contexto & Motivação
No painel geral do Tabulador, o gráfico de progresso (`graficoProgresso` em `static/app.js`) plota a série cronológica de respostas únicas conferidas em relação ao total da base.
Atualmente, o gráfico conta com uma linha verde simples e marcações absolutas no eixo Y.
Para facilitar o acompanhamento do ritmo do projeto pela coordenação e pesquisadores, foi solicitada a adição de métricas visuais secundárias que permitam enxergar a tendência de entrega sem poluir a tela.

---

## Requisitos Detalhados

### 1. Linha de Evolução Verde com Degradê Escurecendo
- A linha de respostas conferidas (`var(--ok)`) deve ganhar um preenchimento em área inferior (polígono/área SVG) com degradê vertical (`linearGradient`).
- Efeito degradê com tonalidade verde suave escurecendo em direção à base (ou degradê de transparência), dando peso visual à evolução do trabalho já conferido sem ofuscar a grade de fundo.

### 2. Porcentagem no Eixo Y
- Adicionar leitura percentual correspondente no eixo Y (0%, 25%, 50%, 75%, 100%), permitindo ao usuário correlacionar diretamente o volume absoluto com a proporção da base concluída.
- A porcentagem pode ser posicionada no lado direito do gráfico (eixo Y secundário discreto) ou em conjunto com os rótulos numéricos do lado esquerdo (ex.: `1.200 · 50%`).

### 3. Projeção de Ritmo de Respostas (3 Cenários)
- **Base de cálculo:** calcular a cadência de produção (respostas conferidas por dia) a partir do histórico disponível em `serie`.
- **Cenários modelados:**
  - **Neutro:** ritmo médio de respostas/dia recente (média ponderada ou móvel dos últimos dias ativos).
  - **Otimista:** ritmo de dias de alta produtividade (ex.: percentil 75 ou melhor dia de produção).
  - **Pessimista:** ritmo de dias mais lentos (ex.: percentil 25 ou ritmo mínimo sustentado).
- **Representação visual:**
  - Linhas em cinza sutil (`stroke: var(--text-3)` ou cinza claro com opacidade), traço fino e pontilhado (`stroke-dasharray="2 3"`).
  - Projeção parte do último ponto realizado até alcançar a linha de 100% de respostas concluídas.
- **Data estimada de conclusão:**
  - Cálculo da data projetada de entrega: $\text{data\_atual} + \lceil \text{faltam} / \text{ritmo} \rceil$ para o ritmo atual/neutro (e faixa entre otimista e pessimista).
  - Exibição sucinta na legenda ou cabeçalho secundário: *"Previsão: DD/MM (ritmo atual)"*, com detalhes em tooltip ao passar o cursor sobre as linhas projetadas.

### 4. Discrição Visual e Não-Ocupação de Espaço (Informações Secundárias)
- As projeções e marcações percentuais têm caráter **secundário**: não devem disputar atenção com a linha real de conferência.
- Cores desaturadas (cinza neutro), linhas finas, tipografia pequena em monospace (`font-size: 9.5-10px`), sem criar poluição visual no gráfico.
- Tratamento gracioso para projetos novos ou com histórico insuficiente (< 2 dias com evolução): a projeção deve se ocultar automaticamente sem gerar erros de renderização.

---

## Critérios de Aceite
1. O SVG do painel renderiza a linha verde de evolução com preenchimento em degradê sutil.
2. O eixo Y apresenta de forma clara e limpa a porcentagem do total de respostas.
3. As 3 linhas de projeção (otimista, neutro, pessimista) aparecem em cinza discreto e informam a data estimada de conclusão.
4. Quando não houver dados suficientes de histórico para projetar, o gráfico se mantém íntegro exibindo os dados reais sem quebrar.
