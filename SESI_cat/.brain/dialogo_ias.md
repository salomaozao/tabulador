# Diálogo entre IAs — SESI (categorização)

Log cronológico, só acrescentar no fim. Formato descrito em `README.md`.

---

## 2026-09-23 — chore(brain): cria a memória .brain do projeto SESI

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O SESI_cat não tinha `.brain/`. A skill manage-brain foi invocada, então a estrutura foi criada a partir do modelo do INSPER, com os fatos da conversa com a Jucimara (`09_22_alinhamento_categorizacao.md`) e do estado do categorizador (commits até `fd1d4b9`).

**Feito:**
- `.brain/` com README, `scripts/manage_brain.py` (cópia do INSPER com o nome do projeto trocado), DEC-01 e DEC-02, PEND-01 a PEND-03.
- `manage_brain.py sync` e o calendário geral (`coletar_eventos.py`, `gerar_ics.py`) executados.

**Decisões:** A PEND-03 usa `data_abertura: 2026-09-28` (início do processamento) para aparecer nesse dia no calendário geral, que usa essa data como data do evento.

**Pendente / atenção:**
- Campo termina em 25/09 (sexta); processamento começa em 28/09 (segunda). Devem entrar cerca de 500 entrevistas até lá (PEND-01).
- Lista de perguntas abertas: a planilha tem 7 colunas `_CAT` em amarelo. A Q30_CAT existe, mas não está em amarelo, e o `projeto.py` a inclui (PEND-02). Falta confirmar com a Jucimara.
- Google Calendar sincronizado (`sync_google.py`: 3 inseridos, 31 atualizados).

**Próxima IA / Handoff:** Fechar a PEND-02 quando a Jucimara responder sobre a Q30. Antes de trocar a base por uma versão nova, garantir que as validações já feitas sejam preservadas por `respondent_id` (PEND-01).

---

## 2026-09-23 — feat(categorizador): criação de projetos novos (assistente, skill e CLIs locais)

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O objetivo era criar projetos novos sem escrever um `projeto.py` à mão, com o mínimo de regras. O SESI serviu de gabarito, porque o `projeto.py` dele foi feito por IA e conferido.

**Feito (em `_laterais/categorizador`, ainda sem commit):**
- `novo_projeto/`: perfil da planilha, rascunho do `projeto.json` gerado sem IA, validador que roda a leitura real, registro, CLI e assistente.
- O `projetos.py` passa a aceitar `projeto.json` declarativo.
- Botão **+ Novo projeto** na interface.
- Skill `.claude/skills/novo-projeto` e `AGENTS.md`, para Codex e Antigravity.
- Provedor de IA "programa instalado no computador" (`llm_cli.py`). O Claude Code foi testado; o Codex e o Gemini CLI, não.

**Achados sobre o SESI:**
- O rascunho gerado sem IA a partir da planilha coincide com o `projeto.py` em tipos, opções, dados pessoais e filtros. Pela cor do `_CAT`, marca as 7 perguntas amarelas e deixa a Q30 de fora, o que confirma a PEND-02.
- Q3 = 0: das 40 pessoas que deram nota 0, nenhuma recebeu a Q4 nem a Q5. O `projeto.py` usa Q3 ≤ 7 como filtro da Q4, então essas 40 pessoas entram na base da Q4 sem terem recebido a pergunta. Vale confirmar com a Jucimara se o questionário pulava a nota 0.

**Próxima IA / Handoff:** revisar e fazer o commit das mudanças do categorizador; confirmar a Q30 (PEND-02) e a nota 0 com a Jucimara.
