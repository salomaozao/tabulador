---
id: PEND-13
titulo: Painel mede RESPOSTAS revisadas (não perguntas) e mostra quantas faltam
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js, src/historico.py, static/app.css, tests/test_historico.py]
criticidade: alta
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
prazo: 2026-10-02
data_resolucao: 2026-10-01
resumo: "O cabeçalho do projeto diz '% das perguntas revisadas'. O Gabriel (01/10) e a Sara (30/09, US-05 do PRD feedbacks_sara) querem o número de RESPOSTAS revisadas, para ter um panorama de quantas faltam. Destaque primário: 'X% · N de M respostas conferidas · faltam K'; perguntas viram métrica secundária. A curva de progressão ganha a série em respostas."
---

# PEND-13: Painel por respostas revisadas

Arquivo estava vazio no disco (criado em 30/09, conteúdo perdido). Reescrito em 01/10 a partir do PRD `ciclos/2026-09-30_feedbacks_sara` (US-05) e do pedido do Gabriel.

- **Onde:** `cabecalhoProjeto()` e `graficoProgresso()` em `static/app.js`, além da série diária em `src/historico.py`.
- **Mudança implementada em 01/10:**
  - `src/historico.py`: `estado_perguntas` e `resumo` calculam respostas únicas (`n_unicas`), classificadas, revisadas (com divisão explícita de `revisadas_humano` e `revisadas_auto`), e `faltam`. A série traz contagem absoluta de respostas conferidas e total de respostas do projeto.
  - `static/app.js`: `cabecalhoProjeto` exibe destaque primário em respostas únicas conferidas, `faltam K` destacado em aviso, barra empilhada separando manual (`.rev-hum`) de automática (`.rev-auto`), e perguntas concluídas como linha secundária. `graficoProgresso` plota a contagem absoluta de conferidas e total de respostas com escala dinâmica e sem queda fictícia de curva ao entrar base nova.
  - `tests/test_historico.py`: testes atualizados e passando 100% cobrindo contagens de respostas e evolução na série.
