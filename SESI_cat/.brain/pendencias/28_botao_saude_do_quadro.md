---
id: PEND-28
titulo: Botão colorido "Saúde do quadro" ao lado de "Revisar por categoria", que abre uma ilha com diagnóstico e melhorias propostas
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, static/app.js, static/app.css, src/aprendizado.py, app.py]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
data_resolucao: 2026-10-01
resumo: "A caixa 'Saúde do quadro' estática foi removida do topo da tabela. No lugar dela, um botão '🩺 Saúde do quadro (N)' foi adicionado ao lado de '🗂 Revisar por categoria' (tanto no cabeçalho de Categorias quanto na barra de supervisão). Ao clicar, abre o modal de Saúde do Quadro que aglomera os problemas por categoria, consolida confusões de fronteira em resumos limpos com destinos, e apresenta soluções concretas aprováveis na hora: propor nova definição com IA (com prévia diff), adicionar ressalva de exclusão, remover palavra-chave ambígua, adicionar palavras aprendidas, e tabela compacta para mesclar/excluir categorias raras (< 1%)."
---

# PEND-28: Ilha "Saúde do quadro"

## O que foi implementado:
1. **Botão na Interface:**
   - Botão `🩺 Saúde do quadro (N)` inserido imediatamente ao lado de `🗂 Revisar por categoria` no cabeçalho de Categorias e na barra de ações/supervisão de revisão.
   - Pílula colorida dinâmica: verde quando 100% saudável, amarela/destaque quando há alertas críticos de amplitude, fronteira ou saturação de Outros.
   - A caixa estática amarela e crua inline foi removida de cima da tabela de categorias.

2. **Aglomeração por Categoria & Diagnóstico Estruturado (`src/aprendizado.py`):**
   - Função `diagnostico_saude_de(...)`: agrupa os alertas por categoria afetada em vez de listar frases desconexas.
   - Condensa 10+ avisos repetitivos de confusão de saída em um único sumário analítico com destinos e volumes de respostas corrigidas.
   - Agrupa categorias raras (< 1%) em seção dedicada e compacta.

3. **Soluções Propostas com Aprovação Humana:**
   - **Reescrita de Definição com IA:** Novo endpoint `POST /api/pergunta/<qid>/frame/propor-definicao` que usa IA e o dossiê de erros reais para propor redação concisa que delimita fronteiras; modal exibe card de prévia com justificativa e botão `✓ Aprovar esta definição`.
   - **Ressalva Imediata:** Botão `✓ Adicionar ressalva à definição` adiciona cláusula de não-inclusão das categorias concorrentes com 1 clique.
   - **Remoção de Palavra Ambígua:** Botão `✓ Remover palavra ambígua` para resolver sobreposição de termos entre categorias.
   - **Termos Aprendidos:** Botão `✓ Adicionar palavras sugeridas` para incorporar termos de alto lift do aprendizado.
   - **Mesclagem de Raras:** Tabela compacta com dropdown e botão `✓ Aprovar mesclagem` (ou `🗑️ Excluir` para quem tem 0 respostas).
   - **Aprendizado Manual:** Botão `🧠 Aprender com a revisão agora` com transparência de quantas revisões faltam ou quantas keywords foram salvas.
