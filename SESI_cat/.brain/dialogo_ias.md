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

---

## 2026-09-23 15:40 — feat(categorizador): IA por CLI (teste de conexão, lista de modelos, agy) + merge da apresentação

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** Ver o fluxo de novo projeto (app e skill), resolver o "Failed to fetch" e a falta de retorno no teste da IA, melhorar a escolha de modelo dos provedores CLI e incluir o Antigravity (`agy`). Também juntar o worktree `apresentacao-16h` na `main`.

**Feito:**
- Commit `cb77d33` (todo o trabalho pendente da `main`):
  - bloco "criar com uma IA (skill)" na aba Novo projeto;
  - botão **Testar conexão** com confirmação visível; quando falha, explica o que aconteceu e propõe a solução (`llm.diagnosticar`; `/api/config/testar` sempre devolve 200);
  - "Failed to fetch" virou uma mensagem clara;
  - lista fixa de modelos por provedor, com a opção "outro…";
  - `tests/test_cli.py`: testes sem custo mais 1 teste real opcional (`CATEGORIZADOR_TESTE_CLI=1`).
- Merge `950f8e4` do `worktree-apresentacao-16h` (progresso da IA, aba Resultados, gerenciar projeto). Conflitos resolvidos mantendo os dois lados; 48 testes OK. O ramo local foi apagado depois que o worktree foi fechado.
- **Sem commit:** provedor `cli_agy` (Antigravity). O `llm_cli.py` o encontra em `~/.gemini/bin` e manda o prompt pela entrada padrão (`--input-format stream-json`, mensagem `{"event":"user",...}`), com `--sandbox` e o schema em arquivo. O `config.py` traz os modelos de `agy models`, e há 4 testes novos. Teste real OK: 13 s, cerca de 27 mil tokens de entrada (16 mil em cache).
- App reiniciado na porta 5000 pelo `Abrir Categorizador.bat`.

**Decisões:**
- O teste de conexão devolve sempre HTTP 200 com `{ok, explicacao, solucao, erro}`, para a tela mostrar a explicação em vez de um erro genérico.
- Os provedores CLI usam o login ou a assinatura do programa, não chave de API (não há `ANTHROPIC_API_KEY` no ambiente). O "US$" informado pelo Claude Code é só uma estimativa.

**Pendente / atenção:**
- Commit do suporte ao agy: o usuário ia mostrar um "arquivo de conversa entre duas IAs" que usa o CLI gastando a cota da assinatura. Não foi encontrado; ele precisa informar o caminho. Depois disso, reiniciar o app.
- Lista de modelos do Gemini desatualizada: `gemini-2.5-pro` e `gemini-2.5-flash-lite` não estão disponíveis para usuários novos. O `gemini-2.5-flash` funciona.
- Chaves de API: ver PEND-04.
- Sem push: a `main` está 3 commits à frente do `origin`, e o ramo remoto `worktree-apresentacao-16h` ainda existe.

**Próxima IA / Handoff:** Perguntar ao Gabriel onde está o script de conversa entre IAs, adaptar o `llm_cli` se preciso, commitar o agy e reiniciar o app. Atualizar a lista de modelos do Gemini, testando cada um com `max_tokens` pequeno. Push só com autorização. As pendências de negócio continuam: PEND-01 (campo até 25/09), PEND-02 (Q30) e PEND-03 (entrega em 28/09).
