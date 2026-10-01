---
id: PEND-22
titulo: Erro "servidor demorou mais de 35s" ainda aparece - a correção nunca foi commitada; publicar e cobrir toda chamada de IA
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, static/app.js, src/llm.py, git]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
prazo: 2026-10-02
resumo: "A correção de 29/09 (sem timeout nas operações com progresso, 4 min nas demais, TABULADOR_LLM_TIMEOUT=240) está só na árvore de trabalho desta máquina. O HEAD e o GitHub ainda têm 'opts.timeout || 35000', então quem roda pelo GitHub (Sara, João) ou com app.js em cache continua vendo o erro. Além disso, chamadas de IA sem barra de progresso (gerar categorias, 'Pedir ajuste à IA') ficam limitadas a 4 min. Ação: separar os hunks e commitar o trabalho de 29-30/09; toda chamada que envolve IA passa a usar progresso (sem corte no navegador)."
---

# PEND-22: Publicar o timeout e o trabalho sem commit

- **Diagnóstico (01/10):**
  - `git show HEAD:tabulador/static/app.js` → `const timeoutMs = opts.timeout || 35000;`
  - árvore de trabalho → `opts.timeout ?? (progresso ? 0 : 240000)`.
  - São cerca de 1.500 linhas sem commit, de duas sessões (Antigravity 29/09 e Claude 30/09, PEND-18). Isso já é, por si, um risco de perda de código (ver OBJ-03).
- **Passos:**
  1. Rodar `python -m unittest discover -s tests` e anotar as falhas que já existiam (4, de `test_sesi`/`test_novo_projeto`, por causa da contagem de 84 para 135).
  2. Fazer commits atômicos com `git add` cirúrgico:
     - (a) timeout/progresso;
     - (b) PEND-18 aprendizado;
     - (c) histórico/curva;
     - (d) botão aprovar.
     Push em seguida.
  3. Em `induzir`, `refinar`, `aprender` e no teste de IA, passar `progresso=true` (ou um `timeout` explícito longo) e fazer o backend reportar etapa em `progresso`.
  4. A versão da página (`/api/versao`) já força o recarregamento quando o servidor muda. Conferir que o aviso "recarregue" aparece para quem está com o app.js velho.
- **Critério:** classificar e auditar a Q35 inteira pelo navegador da Sara, com o código puxado do GitHub, sem nenhum erro de tempo.

## Andamento (01/10, Claude Sonnet 5.5)

- **Feito:** backup completo da nuvem antes de tudo (`output/_backup/nuvem_20261001_141438.json`, 35 linhas, 7 perguntas classificadas). Suíte rodada antes e depois: 4 falhas conhecidas (contagem 84 → 135), nenhuma nova.
- **Commits locais** (3, por camada; os hunks se entrelaçam entre aprendizado, parada e timeout, então não dá para isolar um commit só do timeout): `141e5c7` módulos novos, `161108c` backend, `841a48f` front (sem o corte de 35 s).
- **Falta:** (1) `git push` — **não feito**, depende de o Gabriel confirmar; (2) passo 3: `progresso=true` em `induzir`, `refinar`, `aprender` e teste de IA; (3) passo 4: conferir o aviso de "recarregue"; (4) critério final: Q35 inteira no navegador da Sara.
- **Fora dos commits de propósito:** `tabulador/SALVAR.txt`, o `.mp4` e `base_processamento_nova.xlsx` (dado de cliente).
