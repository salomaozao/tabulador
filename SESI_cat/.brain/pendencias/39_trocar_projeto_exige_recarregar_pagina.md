---
id: PEND-39
titulo: Ao trocar de projeto é preciso recarregar a página para a tela mudar
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Relato do Gabriel (02/10): ao escolher outro projeto no menu do topo, a tela continua mostrando o anterior até recarregar a página (F5). Esperado: a troca atualizar tudo sozinha (painel, barra lateral, perguntas, nome do projeto)."
---

# PEND-39: Trocar de projeto sem recarregar a página

- **Sintoma:** `trocarProjeto(slug)` (`static/app.js`) faz o `POST /api/projeto`, zera `state.qid`, recarrega o status e chama `rota()` ou `irPara(null)`. Mesmo assim, o que está na tela não reflete o projeto novo até o F5.
- **Hipóteses a verificar (ainda não investigado):** estado do front que sobrevive à troca (`state.P`, listas de perguntas, grupos, presença, cache do `fetch`); o cache de leitura de 5 s da nuvem (PEND-12) devolvendo dados do projeto antigo; a rota continuar em `#pergunta/<qid>` ou `#grupo/<nome>` que não existe no projeto novo.
- **Critério de pronto:** trocar de projeto a partir de qualquer aba (painel, pergunta, grupo, resultados, gerenciar) mostra o projeto novo sem F5, e voltar ao anterior também. Teste manual nos dois sentidos.
- **Solução de contorno enquanto não sai:** recarregar a página (F5).
