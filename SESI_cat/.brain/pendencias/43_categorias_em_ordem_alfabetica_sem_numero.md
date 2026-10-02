---
id: PEND-43
titulo: Categorias nos menus de escolha em ordem alfabética e sem o número
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
data_resolucao: 2026-10-02
resumo: "Pedido do Gabriel (02/10): ao escolher a categoria de uma resposta, listar em ordem alfabética e sem o número (pouco útil para o analista). Mergeado na main em 02/10 (merge geral pedido pelo Gabriel); suíte integrada: 188 passam. Ainda não validado na tela."
---

# PEND-43: Menus de categoria sem número e em ordem alfabética

- **Onde:** menus de categoria principal e secundária de cada resposta, filtro 'todas as categorias' e os menus 'mesclar em…' (`optsCategorias` em `static/app.js`). Ordem: alfabética (pt-BR, sem distinguir acento) com **Outros e NS/NR no fim**.
- **Não mudou:** o atalho de teclado que digita o código (0–99) na linha da resposta, a tabela de categorias do quadro e a janela 'Revisar por categoria', que continuam mostrando o número.
- **Pergunta aberta:** se quiser o número escondido também nesses outros lugares, ou o atalho de teclado trocado por busca por nome.
