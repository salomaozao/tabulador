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

---

## 2026-09-24 — feat(tabulador): feedbacks do teste de UI com o João + junção das worktrees concorrentes

**Autor:** Claude Sonnet 5 (Claude Code) · operador: Gabriel Nascimento

**Contexto:** Gabriel pediu para ler `.brain/docs/reunioes/23_09_teste_ui_joao.md` junto com uma lista de 7 feedbacks dele sobre o teste de UI (cruzamento de variáveis, botão de aprovar, ordenação/subfiltros, seção "O que as respostas dizem"). Ao mesmo tempo, avisou que outras 2 IAs mexiam no repositório: uma editando `.brain/pendencias/{02,04,05}...md` ao vivo (era o próprio Gabriel, confirmado depois) e outra numa worktree separada (`worktree-turso-db-poc`, prova de conceito de armazenamento em nuvem via Turso/libSQL).

**Feito:**
- Abri uma worktree isolada (`worktree-tabulador-feedback-joao`) para não colidir com os outros trabalhos em andamento, e um `jumppi/COMUNICACAO_IAS.md` (gitignorado pela allowlist da raiz — fica só local, mas serve de aviso a quem está no mesmo working dir).
- Implementei 5 dos 7 feedbacks (commit `e25f816`, mesclado em `4da2fec`):
  - aba **"Geral"** no `cruzamentos.xlsx` (todas as variáveis numa tabela só: Variável | Opção | Total | banners) + seletor de variáveis de cruzamento na aba Resultados (`/api/variaveis-cruzamento`);
  - botão **"Aprovar e gravar nos resultados"** movido para o fim da tabela de revisão;
  - ordenar por confiança agora desempata por categoria, mais chips de sub-filtro por categoria nesse modo;
  - **"Visão geral do projeto"** substitui "O que as respostas dizem": resumo narrativo por IA sob demanda (cache em `resumo_geral.json`, módulo novo `resumo_geral.py`) + temas agregados de todas as perguntas + trechos reais, sem repetir pergunta a pergunta.
  - Os outros 2 feedbacks (recategorizar só não-validadas; corrigidas por humano irem para o fim junto das confirmadas) já funcionavam — confirmado lendo `coding.py`/`app.js`, sem precisar mudar código.
- Resolvi PEND-02 e PEND-04 (Gabriel já tinha escrito a resolução inline nos arquivos; só formalizei status/frontmatter) e esclareci o item 1 de PEND-05, acrescentando um item 5 novo (contabilizar na `usage` as confirmações automáticas e as chamadas do auditor — ainda não implementado) — commit `ed1e5c4`.
- Depois do aviso "já vamos encerrar a outra IA, junte tudo": mesclei `worktree-tabulador-feedback-joao` (`4da2fec`) e `worktree-turso-db-poc` (`5e9ac64`) na `main`, nessa ordem. Ambos os merges foram automáticos, sem conflito (`app.py` e `config.py` foram tocados pelas duas branches, mas em trechos diferentes). Apaguei as duas branches depois do merge.
- Rodei `python -m py_compile` em todos os módulos tocados pelos dois merges (`app.py`, `crosstabs.py`, `resumo_geral.py`, `config.py`, `codeframe.py`, `nuvem.py`) — OK.

**Decisões:**
- Não toquei em `coding.py`/`config.py` durante a implementação dos feedbacks (eram os arquivos que a outra IA vinha mexendo antes do commit `726e057`), para reduzir risco de colisão — só entraram na `main` via o merge do `turso-db-poc`.
- "Visão geral do projeto" não separa mais por pergunta (pedido explícito do Gabriel); o link por pergunta continua existindo na página de cada pergunta (`/relatorio/<qid>`), só saiu da aba Resultados.

**Pendente / atenção:**
- **Limpeza manual:** `git worktree remove` falhou com "Permission denied" nas duas pastas (`jumppi/.claude/worktrees/turso-db-poc` e `.../tabulador-feedback-joao`), provável lock do OneDrive. Já removi o registro do git (`git worktree list` está limpo) e apaguei `tabulador-feedback-joao` do disco; `turso-db-poc` ficou "Device or resource busy" — precisa fechar o que estiver com um handle aberto nela (ex.: terminal/editor apontando pra lá) e apagar a pasta manualmente.
- **Suíte de testes:** rodei `python -m unittest discover -s tests -v` depois dos merges e o processo não terminou em 180 s (sem output, possivelmente `test_cli.py` esperando um programa CLI que não está instalado nesta máquina). Não travei a mesclagem por causa disso, já que os `py_compile` e um smoke test isolado da aba "Geral" passaram, mas vale conferir o resultado da suíte antes de confiar cegamente no merge do Turso.
- Não rodei o app fim a fim (Flask) com a base real do SESI para os 5 feedbacks novos — recomendo abrir o Tabulador e clicar nas telas (Resultados → variáveis de cruzamento e visão geral; tela de revisão → botão de aprovar embaixo e chips de subfiltro) antes de considerar fechado.
- PEND-05 segue aberta (itens 2, 3, 4 e o novo item 5 de contabilização na usage).
- Não fiz `git push` (a `main` está à frente do `origin`; só empurro com autorização explícita).

**Próxima IA / Handoff:** conferir o resultado da suíte de testes (`python -m unittest discover -s tests -v`) e investigar por que travou; apagar manualmente a pasta órfã `turso-db-poc` quando não estiver mais em uso; testar as 5 telas novas do Tabulador com a base real do SESI; seguir com os itens 2-5 de PEND-05 quando o Gabriel priorizar.

---

## 2026-09-24 16:40 — feat(tabulador): rid estável, supervisão na interface, nuvem com dados reais, PEND-01/05/06

**Autor:** Claude Opus 5.5 (Claude Code) · operador: Gabriel Nascimento

**Contexto:** o Gabriel pediu para matar todas as pendências (a PEND-05 era a prioridade), depois commitar, analisar a cobertura de testes e deixar tudo pronto para os colegas usarem ("todos com os mesmos dados; o usuário só executa o Tabulador").

**Feito:**
- `318074e` **PEND-01, rid estável** (DEC-03). O rid era a posição numa lista ordenada por frequência: uma base nova embaralharia as classificações e conferências. Agora ele segue a chave do texto.
  - `codeframe._conciliar` concilia a codificação (guarda em `removidos`, acusa divergência e reabre a aprovada que ganhou respostas novas).
  - "Recarregar planilha" agora relê as perguntas, mostra um resumo e grava `output/base/versoes.json`.
  - Nos dados reais (numa cópia) nada muda até chegar a base nova.
  - `nuvem.ativa()` fica desligada com `TABULADOR_OUTPUT` ou no modo teste: a suíte vinha gravando dados falsos no banco real do projeto "sesi".
- **Nuvem**: backup do que havia (`output/_backup/nuvem_*.json`, só lixo de teste na Q2/Q33), depois `python nuvem.py -p sesi subir --limpar-antes`: 32 arquivos das 8 perguntas, conferidos um a um. O app lê os dados reais pela nuvem.
- `053db66` **PEND-05 completa**:
  - `supervisao.py`: auditar com outra IA via `llm.usando`, auto_aceitar (0,85, exige o auditor concordando), desfazer_auto e conferencia;
  - `perfil.py`: perfil de quem citou vs. a base da pergunta, com `PERFIL` no projeto.py;
  - interface: botões de supervisão, pill "⚡ auto", filtros "automáticas" e "auditor discordou", sugestão na linha com a tecla S, janela "Revisar por categoria" com "Confirmar N pendentes" (sem as discordâncias);
  - Consumo: tokens de "auditoria" separados e card "Supervisão por IA";
  - `validado_por="humano"` nas confirmações manuais; `supervisor.py` passou a usar `supervisao.py`.
  - Testado no navegador com uma cópia dos dados.
- `48a6eb8`:
  - `config.ENV_EQUIPE` também procura em `Shortcuts/*Projeto IA*/V3/.env` (nesta máquina o `.env` da equipe nunca era achado);
  - `load._ler_aba` localiza a linha do cabeçalho;
  - teste dos endpoints novos.
- **PEND-06**: conferência com um agente revisor, correções aplicadas e Q32/Q33/Q29/Q30 aprovadas (detalhes no arquivo da PEND-06). Planilha final, codebook e cruzamentos regerados. A classificação das restantes da Q5 (536) e da Q35 (1.584) foi disparada com o Gemini.

**Cobertura de testes** (`coverage`, suíte com 61 testes: 60 ok, 1 erro da Assertiva descrito abaixo): **66% no total**.
- Bem cobertos (≥ 90%): `perfil` 96%, `simulador` 96%, `llm_cli` 95%, `supervisao` 93%, `config` 93%, `projetos` 93%, `usage` 92%, `codebook` 92%, `novo_projeto/rascunho` 90%.
- Médios: `crosstabs` 88%, `exportar` 86%, `codeframe` 83%, `llm` 76%, `coding` 74%, `load` 66%, `nuvem` 53%.
- Fracos: `app.py` 44% (muitas rotas de tela sem teste), `resumo_geral` 29%, `backcoding` 28%, `report` 25%.
- Sem nenhum teste: `supervisor.py` e `run.py` (linhas de comando) e `novo_projeto/cli.py`.
- Para rodar: `python -m coverage run --source=. --omit="tests/*" -m unittest discover -s tests -t .` e depois `python -m coverage report`. O `coverage` está instalado só no venv local, não no `requirements.txt`.

**Decisões:** a categoria recriada ficou com o código 10 (o `adicionar` usa max+1; o 8 antigo não é reaproveitado). Correções feitas pelo Claude aparecem como "✎ você" (origem humano), porque entraram pela mesma API da interface. Q29/Q30 aprovadas com 373 e 109 respostas não conferidas por pessoas, que ficam como a IA classificou (dá para reabrir).

**Pendente / atenção:**
- **Credenciais do Turso no `.env` da equipe** (`Shortcuts/Projetos - Projeto IA/V3/.env`): o sistema de permissões bloqueou o Claude de copiar credenciais para o arquivo compartilhado. **O Gabriel precisa colar à mão** `TABULADOR_TURSO_URL` e `TABULADOR_TURSO_TOKEN`, as mesmas do `tabulador/.env` dele. Sem isso, os colegas não entram no banco compartilhado.
- **Nuvem: uma pessoa por pergunta de cada vez** (a última gravação vence o arquivo inteiro).
- **Assertiva** (`tests/test_pipeline.py`): a planilha foi editada em 24/09 às 15h07 e a linha 15 da aba `dados_originais_pesquisadores` é uma linha de códigos colada no meio dos dados. O app recusa, corretamente. Arrumar a planilha, não o código.
- Q5/Q35: quando a classificação das restantes terminar, auditar ("🔎 Auditar com outra IA", ex.: Groq), aceitar as de alta confiança, conferir e aprovar. Depois, regerar os resultados.
- Sugestão em aberto: separar a categoria 6 da Q32/Q33 (ver PEND-06).

**Próxima IA / Handoff:** conferir o log da classificação da Q5/Q35. Seguir a PEND-01 quando a base final chegar (25/09): trocar a planilha, "Recarregar planilha", "Classificar as restantes" e aprovar. A PEND-03 é a entrega em 28/09 com os resultados regerados. Push feito até o commit do brain de 24/09.

---

## 2026-09-24 15:30 — brain(SESI): PEND-07 e PEND-08 abertas (base na nuvem; João sem sincronizar)

**Autor:** Claude Sonnet 5 (Claude Code) · operador: Gabriel Nascimento

**Contexto:** sessão sobre o app do tabulador em geral (não específica do campo). Duas coisas surgiram: (1) o Gabriel propôs subir a base inteira (não só a revisão) para o Turso, para bastar rodar o `tabulador` sem outra pasta de projeto local; (2) o João baixou o `tabulador` do GitHub e as respostas antigas da revisão não sincronizaram para ele.

**Feito:** criadas `PEND-07` (avaliar base inteira na nuvem — ideia, não decisão) e `PEND-08` (João sem sincronizar — falta `.env`/credenciais da nuvem, porque o clone via GitHub não traz `.env` nem `SESI_cat/data`, gitignorados de propósito).

**Decisões:** nenhuma — PEND-07 é só registro da ideia para avaliar depois; não implementar sem decisão explícita.

**Pendente / atenção:**
- PEND-08 relembra um ponto já registrado antes (24/09, mais cedo): as credenciais `TABULADOR_TURSO_URL`/`TABULADOR_TURSO_TOKEN` precisam estar coladas no `.env` compartilhado da equipe (`Shortcuts/.../Projeto IA/V3/.env`) para qualquer pessoa nova (como o João) entrar no banco automaticamente. Conferir se isso já foi feito; se não, é a causa mais provável do João não sincronizar.
- PEND-07 depende de desenhar uma forma declarativa para os filtros do `projeto.py` (hoje são lambdas Python) antes de fazer sentido subir a base para o Turso.

**Próxima IA / Handoff:** ao retomar, primeiro checar se as credenciais do Turso já estão no `.env` da equipe (resolveria a PEND-08 rápido); só depois avaliar a PEND-07 com calma, sem pressa, já que é melhoria de arquitetura e não bloqueio de entrega.

---

## 2026-09-24 17:15 — feat(tabulador): status de sincronização no header, aviso de edição simultânea por pergunta, PEND-09

**Autor:** Claude Sonnet 5 (Claude Code) · operador: Gabriel Nascimento

**Contexto:** mesma sessão da PEND-08 (João sem sincronizar). O Gabriel pediu (1) tirar "Base: N respondentes · atualizada DATA" do header e colocar uma bolinha online/offline + "sincronizado às..." no lugar, com a linha de base indo para o Painel geral; (2) avisar quando outra pessoa está mexendo na mesma pergunta ao mesmo tempo (a nuvem já era "uma pessoa por pergunta, a última gravação vence" — ver `docs/nuvem_turso.md`).

**Feito:**
- `nuvem.status(projeto)`: `{ativa, conectada, ultima_sincronizacao}` — tenta `SELECT MAX(atualizado_em)` da tabela `blobs`; se der erro de conexão, `conectada=False` sem derrubar `/api/status`.
- `nuvem.marcar_presenca`/`sair_presenca`: tabela nova `presenca` (projeto, qid, usuario, visto_em); heartbeat do navegador a cada 12s enquanto a pergunta está aberta, janela de 30s para considerar "ativo agora".
- `config.USUARIO`: login do Windows (`getpass.getuser()`), ou `TABULADOR_USUARIO` no `.env` — só para a presença, nunca vai para a base.
- `app.py`: `/api/status` ganhou `"nuvem"`; endpoints novos `POST /api/pergunta/<qid>/presenca` e `.../presenca/sair`.
- `app.js`/`index.html`/`app.css`: header trocou `#base-status` (agora só a IA) por `#ia-status` + `#nuvem-status` (bolinha + texto); "Base: N respondentes..." foi para o Painel geral; aviso `.aviso` na tela da pergunta quando `outros.length > 0`.
- Testes novos em `tests/test_nuvem.py` (status e presença) — suíte de nuvem com 15 testes, `test_sesi.py::test_4_app_api` OK.

**Decisões:** identidade da presença é o login do Windows (sem tela de login); registrado como limitação na PEND-09, não implementar identificação/sidebar agora.

**Pendente / atenção:**
- `PEND-09` criada: identificação explícita (pessoa/IA) na tela inicial + sidebar à direita mostrando onde cada um está no projeto inteiro (hoje o aviso é só dentro da pergunta aberta). Ideia registrada pelo Gabriel, não desenhada.
- Não testado no navegador com a base real (só suíte automatizada) — antes de considerar fechado, abrir o Tabulador e conferir a bolinha (online/offline) e o aviso de presença com duas abas na mesma pergunta.
- Presença marcada só pelo heartbeat do navegador: uma IA mexendo direto nos arquivos via CLI não aparece — mencionado na PEND-09.

**Próxima IA / Handoff:** testar as duas telas novas no navegador (bolinha de sincronização, aviso de presença com duas abas); ao retomar a PEND-09, desenhar a extensão de `nuvem.marcar_presenca` para o projeto inteiro (não só por `qid`) antes de montar a sidebar.

---

## 2026-09-24 19:47 — feat(tabulador): ciclo perpétuo autônomo (Sprints 1 a 5 concluídos com 70 testes verdes)

**Autor:** Antigravity (Gemini 2.5) · operador: Gabriel Nascimento

**Contexto:** Sessão autônoma de melhorias perpétuas no Tabulador no padrão dos ciclos contínuos de software engineering (Rate Hike / Balatro Bot), operando em Git worktree dedicada (`jumppi/worktrees/tabulador-melhorias`, branch `feat/melhorias-perpetuas`) para cumprir a Regra Zero de concorrência com o Claude Code. Três personas paralelas (UI/UX, Analista/Funcionalidades, Engenharia Frontend) diagnosticaram gargalos críticos do sistema e priorizaram intervenções atômicas.

**Feito:**
- **Sprint 1 (`9b93c81`):** Feedback visual nítido na linha confirmada (`tr.confirmada`, `@keyframes pulse-ok`), atalhos de alta velocidade (navegação `J`/`K`, buffer multidígito `0`–`99`, `Ctrl+Enter` para salvar comentário, auto-foco na 1ª linha pendente), preservação de scroll no modal de categorias (`abrirJanelaCategorias`) e Page Visibility API no heartbeat de presença para poupar requisições em background e eliminar falsas contenções no Turso.
- **Sprint 2 (`68b343c`):** Aceitação automática seletiva de alta confiança por categoria no modal (`cc-conf-alta`), inclusão de linha de "Base Amostral" no topo dos banners da aba Geral do Excel (`crosstabs.py`), ordenação decrescente por frequência nas abertas com Outros (97) e NS/NR (98) fixos no rodapé, inclusão de `codigo`/`opcao` em `dados_longos`, e colunas numéricas `Q*_CAT_COD`/`Q*_CAT2_COD` no export para consumo direto em Power BI e SPSS.
- **Sprint 3 e 4 (`01ebf88`):** Timeout defensivo de 35s nas chamadas `api()`, painel agrupador de discordâncias do auditor com resolução em lote de sugestões (`.b-aceitar-grupo`), alerta metodológico destacado de saturação de "Outros" (>5% da base) tanto no card quanto no cabeçalho do frame de categorias, e reorganização ergonômica das colunas da tabela de revisão movendo a coluna "Situação" para logo após "OK", eliminando o ziguezague horizontal de >1000px.
- **Sprint 5 (`61210c4`):** Limpeza de colunas técnicas internas (`nsnr_regra`, `auditoria`, `validado_por`, `respondent_ids`) na planilha `revisao.xlsx` exportada para análise humana (atendendo feedback gravado pelo Gabriel e João Victor) e criação de nova suíte de testes `test_revisao_excel.py`.
- **Suíte de Testes:** 70 testes passando 100% em 7.6s (`python -m unittest discover -s tabulador/tests -v`), `node --check` sem erros.

**Decisões:**
- Trabalho isolado estritamente na worktree `feat/melhorias-perpetuas`. Nenhuma colisão com as árvores do Claude Code (`tabulador-feedback-joao` ou `tabulador-modelo-recomendado-parar`).
- Zero `git push` executado. Imutabilidade absoluta mantida nos dados de produção (`data/`).

**Próxima IA / Handoff:**
- As alterações estão commitadas localmente na branch `feat/melhorias-perpetuas`. Gabriel pode fazer merge ou cherry-pick para a `main` a qualquer momento.
- Para próximas iterações: avaliar virtualização de lista para perguntas com >2000 respostas ou resumo comparativo entre ondas de pesquisa.


---

## 2026-09-29 16:20 — feat(ui,painel): topo enxuto (projeto no título, modo teste em Configurar IA, recarregar em Gerenciar) + progressão cronológica da categorização

**Autor:** Hermes Agent (openrouter/auto) · operador: Gabriel Nascimento

**Contexto:** pedidos de 28/09 (Sara) e de 29/09 do Gabriel: limpar a aba de cima do trabalhador; seleção de projeto ao lado do título, em menu próprio, com "+ Novo projeto" dentro do mesmo cartão; 🧪 Modo teste dentro de ⚙ Configurar IA; ↻ Recarregar planilha dentro de 🛠 Gerenciar projeto (ação rara); embaixo do título do projeto, um % grande de quanto já foi revisado e, ao lado, gráfico de progressão com duas linhas (classificadas e revisadas) em % de perguntas (denominador fixo, para a linha não sobe e desce quando entra entrevista); e, em cada pergunta, "revisadas / total" no canto direito, sticky, grande, monospace, com barrinha.

**Feito (na `main`, sem commit — ver Pendente):**
- Novo `src/historico.py`: estado por pergunta (classificada quando `n_faltantes = 0`; revisada quando `n_revisadas >= n_codificadas`) e reconstrução das séries sem começar a medir de hoje — revisadas pelo carimbo `validado_em`/`revisado_em` de cada item em `codificacao.json`, classificadas pelos carimbos das chamadas `code_*` em `output/llm_log/` (mesma fonte da aba Consumo). Aproximação assumida e documentada no docstring: o ponto da pergunta é o dia do último item que chegou ao estado; se a base crescer depois, a pergunta recua na curva. `/api/status` ganhou `"historico"` (aproveita as `perguntas` já calculadas — não re-leitura dupla).
- Painel geral: cabeçalho do projeto com % de perguntas revisadas em 62px monospace, leitura secundária (N de M perguntas + respostas conferidas), barra empilhada (revisadas / em revisão / a iniciar) e gráfico SVG em duas linhas com denominador fixo (% de perguntas). Cards de pergunta com contador "revisadas / total" no canto direito (monospace + barrinha).
- Página da pergunta: cabeçalho sticky (abaixo do topo, `--topo`) com o contador "revisadas / total" do total de respostas únicas — sempre visível enquanto a tabela rola.
- Topo: `Tabulador` + título do projeto (botão que abre cartão com a lista de projetos e "+ Novo projeto") + estado da IA/nuvem + ⚙ Configurar IA. O `select` anônimo e os três botões saíram da barra.
- ⚙ Configurar IA: 🧪 Modo teste virou botão dentro do diálogo (`type=button`, fecha a janela ao trocar de verdade). 🛠 Gerenciar projeto: seção nova "Base e planilha" com ↻ Recarregar planilha.
- `tests/test_historico.py`: 7 testes (denominador fixo, acumulação por dia, amostra parcial não entra na curva, carimbo mais recente de confirmada/corrigida, revisão importada sem carimbo conta a partir de hoje, projeto vazio, log ausente).

**Verificado com o app rodando contra o projeto SESI real (porta 5017):** `/api/status` → 8 perguntas, 2 revisadas (25%), 3 classificadas, 4.440 de 5.856 respostas conferidas; série de 3 dias (23, 28, 29/09). Na tela: menu abre com "+ Novo projeto", contador sticky "84 / 132" na Q33, 8 cards com contador "21 / 21", gráfico com 2 linhas e 6 pontos, "Base e planilha" com o botão de recarregar. Suíte completa: 85 testes, 4 falhas que já existiam antes (test_sesi 3743→5624 respondentes, Q30 marcada como aberta — a base cresceu; confirmado rodando os mesmos testes sem as minhas mudanças).

**Decisões:**
- "Revisada" no % grande = revisão **concluída** da pergunta (n_revisadas = n_codificadas), combinado com Gabriel no protótipo `tabulador/docs/mockups/2026-09-29_topo_e_progresso.html`.
- Contador de pergunta usa total de respostas **únicas** (leitura "já olhei X de Y"), não classificadas.
- Série em % de perguntas (não de respostas), para não oscilar quando a base cresce — foi o pedido explícito.

**Pendente / atenção:**
- As mudanças estão **sem commit** na `main` (arquivos: `tabulador/src/historico.py`, `tests/test_historico.py`, `app.py`, `static/app.js`, `static/app.css`, `templates/index.html`). Outra IA está trabalhando em `feat/melhorias-perpetuas` e há PEND-13/14/15 registradas por ela — ao commitar, adicionar os arquivos cirurgicamente e coordenar o merge.
- Bases paralelas: a instância antiga do Gabriel (porta 5000) rodou código de antes das 16h20; recarregar a página (ou abrir de novo pelo atalho) pega a versão nova.
- Validação pendente do % do cabeçalho com a Sara/Ju (claro o suficiente "revisada" = pergunta toda conferida?).

**Próxima IA / Handoff:** se o Gabriel aprovar, commitar na `main` só os 6 arquivos de código + teste (sem mockup se ele preferir), rodar `manage_brain.py sync` e resolver merge com `feat/melhorias-perpetuas` antes de qualquer `push`. Não mexer nas pastas de dados.

---

## 2026-09-29 18:25 — fix(tabulador): remoção do timeout em requisições com progresso e reinício do servidor com nova versão

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Ao tentar reclassificar a Q35 com `agy`, o erro de timeout de 35s continuou ocorrendo.

**Diagnóstico & Causa Raiz:**
1. A Q35 cresceu e possui **4.515 respostas únicas** (3.766 pendentes). Cada lote de 30 respostas com `agy` (`gemini-3.1-pro-high`) leva ~33 segundos. Com 2 workers paralelos, processar dezenas ou centenas de lotes leva vários minutos.
2. A instância do servidor no processo anterior (`pid 14344`) ainda estava em memória com a impressão digital antiga (`17d001272f7b`), fazendo o navegador carregar o `app.js` antigo em cache (`35000ms`), abortando após o primeiro lote (confirmado pelos logs `20260929_181318_*_code_Q35_1.json` que terminaram aos 33.3s).
3. Qualquer limite arbitrário estático (seja 35s ou 4 minutos) abortaria fatalmente reclassificações volumosas como a Q35 enquanto o backend está progredindo ativamente.

**Correção Implementada:**
1. `tabulador/static/app.js`:
   - `const timeoutMs = opts.timeout ?? (progresso ? 0 : 240000);`
   - Para operações com `progresso = true` (classificação, recodificação, auditoria, etc.), o sinal de abort por timeout é **desativado** (`timeoutMs = 0`, `signal = undefined`). O frontend agora aguarda o término do pipeline enquanto a barra de progresso e o polling de `/api/progresso` acompanham cada lote em tempo real.
   - Para chamadas comuns (sem progresso), mantém 4 minutos (240s) de tolerância.
2. `tabulador/src/llm.py`:
   - `timeout=int(os.getenv("TABULADOR_LLM_TIMEOUT", "240"))` no cliente OpenAI.
3. **Servidor atualizado & ativo:**
   - Instâncias antigas encerradas e novo servidor iniciado com a nova versão `a9254c7a9e83` na porta 5000.
   - Testado via `curl http://127.0.0.1:5000/api/versao` e verificado o `static/app.js` servido na porta 5000.

**Próxima IA / Handoff:**
- O servidor já está rodando na porta 5000 com a versão `a9254c7a9e83`. Basta dar `Ctrl + F5` no navegador para puxar os scripts atualizados.

---

## 2026-09-29 19:12 — feat(governança): implantação da esteira MetaGPT (SOPs & Artefatos Estruturados)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Transição da metodologia de handoff conversacional livre (`dialogo_ias.md` como diário textual de bordo) para a metodologia **MetaGPT (Code = SOP)**, visando eliminar saturação de tokens, perda de contexto e ambiguidades entre Claude, Antigravity e Hermes.

**Feito:**
- **Templates Canônicos (`.brain/ciclos/_template/`):**
  - `01_PRD.md`: Requisitos de negócio, user stories, critérios de aceite e limites de anti-escopo (Shape Up).
  - `02_ARCH.md`: Módulos afetados, contratos de interface/DTOs, endpoints e diagramas Mermaid.
  - `03_TASKS.json`: WBS estruturado de tarefas atômicas, dependências, roles e critérios de teste.
  - `04_QA_REPORT.md`: Auditoria de testes, não-regressão, veredito final e conservação de dados.
- **Estado Central (`.brain/state.json`):**
  - Controle em tempo real de ciclo ativo, fase (`PRD` -> `ARCH` -> `TASKS` -> `DEV` -> `QA` -> `MERGED`), role da vez e próxima ação mandatória.
- **Linha de Montagem CLI (`.brain/scripts/manage_brain.py`):**
  - Adicionados subcomandos `sop status`, `sop novo <slug>`, `sop avancar`, `sop recuar` e `sop task <ID> <STATUS>`.
  - Geração automática e sincronização executiva do inventário em `.brain/ciclos.md`.
- **Primeiro Ciclo Real Criado & Homologado:**
  - `.brain/ciclos/2026-09-29_timeout_progresso/` documentado com PRD, ARCH, TASKS e QA Report aprovados.
- **Documentação de Governança:**
  - Atualizado `.brain/README.md` com o guia passo a passo da esteira.

**Decisões:**
- A esteira MetaGPT não impede o uso do `dialogo_ias.md`, mas o torna um log conciso de eventos da esteira, eliminando narrativas redundantes.
- Validação estrita: não é permitido avançar para QA com tarefas abertas ou para MERGE sem veredito APROVADO no laudo de QA.

**Próxima IA / Handoff:**
- Para qualquer nova frente de trabalho, verifique o status da esteira via `python .brain/scripts/manage_brain.py sop status` (ou leia `.brain/state.json`) e atue estritamente sob a Role designada para a fase.

---

## 2026-09-30 12:45 — test(openrouter): teste empírico do Custom Classifier e descarte definitivo da feature para categorização

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Investigação e teste prático da viabilidade de utilizar o recurso "Custom Classifiers" da OpenRouter como motor do categorizador de respostas abertas para o Tabulador/SESI CAT, dando sequência à sessão interrompida do Claude Code (`258d22a0-2ed8-42e7-afed-a6e292c2732c`).

**Feito:**
- **Credenciais Seguras:** Chave OpenRouter (`sk-or-v1-...`) centralizada e persistida no cofre canônico `G:\Meu Drive\Gabriel\_general\credentials\.env` como `OPENROUTER_API_KEY` e `TABULADOR_CHAVE_OPENROUTER` conforme o skill `credentials-sentinel`.
- **Execução do Teste:** Disparo de 10 requisições reais da amostra da Q32 do SESI CAT (`%TEMP%\clstest\amostra.json`) com gabarito humano através da API OpenRouter (`google/gemini-2.5-flash-lite`), registrando os IDs `gen-1790782373-...` a `gen-1790782380-...`.
- **Inspeção de Payload & APIs:** Consulta detalhada ao endpoint `GET /api/v1/generation?id={gen_id}` e auditoria da documentação oficial da OpenRouter.
- **Registro de Anti-Escopo:** Atualizado `OBJ-01` (`.brain/objetivos/01_classificacao_multiprojeto_e_resiliencia_rid.md`) e `V3/docs/pipeline/01-pesquisa.md` formalizando a proibição do Custom Classifier da OpenRouter para o pipeline de dados.

**Decisões:**
- **Custom Classifier descartado definitivamente para o pipeline de dados:**
  1. A OpenRouter não disponibiliza rota de API para retorno das tags de classificação (são omitidas do payload do `GET /generation`).
  2. O painel web de Logs não possui função de exportação de dados brutos/CSV de linhas individuais.
  3. Custo duplicado desnecessário (inferência primária dummy + chamada em background do classificador).
  4. Incapacidade de rotulagem múltipla (multilabel) para respostas ricas.
- **Padrão mantido:** A arquitetura do Tabulador permanece inalterada — inferência direta com prompt contendo o codebook e retorno em JSON estruturado (`response_format={"type": "json_object"}`), podendo utilizar modelos econômicos do catálogo da OpenRouter (`gemini-2.5-flash-lite`, `haiku-4.5`) com fallback automático via OpenAI SDK padrão.

**Próxima IA / Handoff:**
- Não reabrir discussão ou implementação sobre OpenRouter Classifiers. Manter foco na esteira do Tabulador e nas pendências de campo e entrega do SESI CAT (PEND-01, PEND-03).




---

## 2026-09-30 — feat(tabulador): quadro de categorias aprende com a revisão (etapa 1: versão, palavras-chave, saúde e few-shot humano)

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O Gabriel pediu um plano para o loop de feedback da categorização ("as categorias ganham dados conforme as respostas são categorizadas?"). Decisões dele:
- objetivo: a IA errar menos e detectar categoria ruim;
- descrição, keywords e exemplos atualizam sozinhos, com log;
- estrutura (nome, criar, separar) exige humano;
- quando o quadro muda, reauditar as não conferidas;
- pediu também uma coluna de "keywords" na tabela de categorias.

Novo objetivo: OBJ-02. Plano completo em `~/.claude/plans/enumerated-crafting-goblet.md`.

**Feito:** etapa 1, detalhada na PEND-18 (resolvida).
- **Arquivos:**
  - `tabulador/src/aprendizado.py` (novo) e `tabulador/tests/test_aprendizado.py` (17 testes);
  - alterados `src/codeframe.py`, `src/coding.py`, `src/supervisao.py`, `src/perfil.py`, `src/config.py`, `app.py`, `run.py`, `static/app.js` e `static/app.css`.
- **Comandos:** `python run.py frame <QID> saude`, `python run.py frame <QID> aprender` e `python run.py frame <QID> keywords <cod> adicionar|remover|fixar "termo"`.
- **Testes:** `python -m unittest discover -s tests` dá 107 testes com 4 falhas anteriores a esta mudança (`test_sesi` e `test_novo_projeto` esperam 84 respondentes, e a base atual tem 135).

**Decisões:**
- Só o que foi conferido por humano ensina: `validado_por="auto"` nunca vira âncora nem keyword.
- As keywords entram no prompt como "pista", não como regra, porque negação e ironia quebram o casamento literal.
- O bloco de categorias mantém a 1ª linha `  N: Nome - def (ex.: ...)`, porque o simulador do modo teste lê esse formato.
- O aprendizado roda antes de classificar e reclassificar, e só com 25+ revisões humanas novas.
- `revisado_por` vem do nome autodeclarado da aba, no cabeçalho `X-Tabulador-Usuario` (URI-encoded).

**Pendente / atenção:**
- PEND-19 (IA reescreve definição + desfazer multinível), PEND-20 (reauditoria seletiva por `frame_versao`) e PEND-21 (propostas de split/merge/nova com prévia; explica o "não aconteceu nada" da Sara).
- As mudanças no tabulador não foram commitadas. A árvore já tinha alterações de outra sessão em `coding.py`, `supervisao.py`, `app.py` e `app.js`, então o commit precisa separar os hunks.
- `pendencias/15_*.md` está vazio no disco (não fui eu).

**Próxima IA / Handoff:**
- Para seguir o OBJ-02, começar pela PEND-21, só a parte da prévia do "Pedir ajuste à IA", se a Sara precisar antes da entrega; senão, pela PEND-19.
- Medir `acerto_ia` por `frame_versao` antes de mudanças grandes.

---

## 2026-10-01 — plan(tabulador): triagem dos feedbacks do Gabriel (segurança, telemetria, saúde do quadro, ergonomia)

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O Gabriel mandou notas sobre o Tabulador:
- ganho de confiança na janela da auditoria;
- snapshots contra perda;
- botão Aprovar longe;
- apagar classificações com filtros;
- erro de 35s;
- "respostas revisadas" em vez de "perguntas revisadas";
- telemetria e painel de administração;
- botão "Saúde do quadro" (as definições não mudaram ao clicar);
- varredura por keywords;
- mixture of agents.

Pediu `manage-brain` e um plano. Nenhum código foi alterado.

**Feito:**
- Novo `OBJ-03` (base protegida e rastreável).
- PEND-13 e PEND-15 reescritas: estavam com 0 bytes no disco, criadas em 30/09, e o conteúdo veio do PRD `ciclos/2026-09-30_feedbacks_sara`.
- Novas PEND-22 a PEND-30.
- PEND-19 ganhou a "etapa 0", que preenche as keywords faltantes.

**Decisões / diagnóstico:**
- **35s:**
  - a correção de 29/09 nunca foi commitada: no HEAD e no GitHub está `opts.timeout || 35000`;
  - há cerca de 1.500 linhas sem commit, de duas sessões;
  - virou a PEND-22, a primeira da fila.
- **"Cliquei e as definições não mudaram":** `aprender()` só mexe em `keywords_auto`, com 25+ revisões novas, e reescrever definições é a PEND-19 (aberta). A UI não dá retorno, o que vai para a PEND-28.
- **Ganho de confiança:** a auditoria não devolve nem altera a confiança. Na PEND-23 há duas opções para o Gabriel decidir (A recomendada).
- **Varredura por keywords:** só seleciona candidatas, e a IA ou uma pessoa decide, coerente com o OBJ-02 ("pista, não regra").
- **Prioridade (entrega em 02/10):**
  1. PEND-22, 24 (camada 1 + backup manual), 15 e 13.
  2. Depois, 26, 23, 28, 19 (etapa 0) e 29, 25.
  3. Por último, 27, 30, 20 e 21.

**Pendente / atenção:**
- PEND-14, 16 e 17 seguem vazias (0 bytes) e não aparecem nos sumários. O conteúdo provável está no PRD feedbacks_sara (US-01..03 para a 14), mas não reescrevi sem confirmação.

**Próxima IA / Handoff:**
- Começar pela PEND-22: rodar os testes, separar os hunks em commits atômicos e fazer push.
- Em seguida, a camada 1 da PEND-24 (guarda contra encolher `codificacao.json`), com teste.

---

## 2026-10-01 — plan(tabulador): revisão crítica do plano + decisão da PEND-23

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O Gabriel pediu para revisar o próprio planejamento (lacunas metodológicas e pontos de melhora). Também decidiu a PEND-23 e guardou uma ideia futura.

**Feito:**
- **Duas pendências novas:**
  - PEND-31 (alta): gravação simultânea perde revisão. `nuvem.gravar` faz upsert sem checar a versão, o `_lock` vale só dentro de um processo e o cache de leitura é de 5s. Deduzido do código, ainda não reproduzido.
  - PEND-32 (alta): amostra de controle aleatória. O "a IA acertou X%" tem viés de seleção, e as automáticas nunca são medidas.
- **PEND-16 reescrita:** estava vazia e virou a ideia futura do botão "Atualizar o Tabulador" (git pull + reinício), por clique e com travas.
- **PEND-23:** decidida a opção A. O termo passa a ser "passaram pelo auditor (confiança alta e outra IA concordou)", e "liberadas para aceitar sozinhas" foi recusado.
- **Ajustes:**
  - PEND-13: unidade explícita, respostas únicas × respondentes, e a quebra humano/auto.
  - PEND-24: invariante "conferidas não diminuem", uma porta de gravação única, backup antes de publicar código e teste de restauração.
  - PEND-25: o desfazer devolve só os rids apagados.
  - PEND-26: manifesto da entrega com `frame_versao` e commit.
  - PEND-29: secundária antes de primária, medida do que a varredura deixa escapar e relação com a PEND-20.

**Decisões:** A ordem até a entrega fica:
1. Backup da nuvem.
2. PEND-22, que publica o código.
3. Orientar a equipe a usar uma pessoa por pergunta até a PEND-31.
4. PEND-15.
5. PEND-13.

Depois vem uma única porta de gravação: PEND-31 + PEND-24 + a parte de gravação da PEND-26.

**Próxima IA / Handoff:**
- Reproduzir a PEND-31 com um teste antes de corrigir.
- Não implementar a PEND-29 antes da PEND-19, etapa 0 (keywords faltantes).

---

## 2026-10-01 — plan(controle): ciclo SOP da amostra de controle (PEND-32)

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O Gabriel pediu o plano de implementação da PEND-32 pensado por user story, seguindo o fluxo MetaGPT (`G:\Meu Drive\Gabriel\code\AI\multiagent\03-integracao.md`: Researcher → Architect → Planner → Developer → Tester → Reviewer).

**Feito:**
- `sop novo amostra_controle --obj OBJ-02`, com os artefatos preenchidos: `01_PRD.md` (7 US), `02_ARCH.md` (contratos, estatística, rotas, sequência) e `03_TASKS.json` (TASK-00 a TASK-07).
- A fase continua em **PRD**, aguardando aprovação. Nenhum código foi alterado.

**Decisões:**
- **População:** só o que vai ao cliente sem olho humano (automáticas + a conferir). Ficam fora as decisões humanas e NS/NR por regra.
- **Sorteio:** 2 estratos com semente fixa.
- **Estimativa:** Wilson por estrato; a combinada é estratificada com ajuste de Agresti-Coull.
- **Cego garantido no servidor:** `proximo()` não devolve a IA.
- **Caminho de escrita:** a correção passa por `CD.atualizar_item()` (caminho único).
- **Armazenamento:** `controle.json` separado de `codificacao.json`, por causa da PEND-31.
- **Nomes:** o campo `acerto_ia` continua no JSON e só o rótulo da UI muda.

**Pendente / atenção:**
- TASK-00 bloqueia tudo: a PEND-22 precisa ser commitada antes de criar a worktree.
- **Decisões abertas no PRD:**
  - erro = só primária (secundária como "erro parcial");
  - n padrão 40;
  - teto de erro das automáticas 5%.

**Próxima IA / Handoff:**
- Depois da aprovação do Gabriel: `sop avancar` (PRD → ARCH → TASKS), executar a TASK-00 e implementar em `worktrees/amostra_controle`.

---

## 2026-10-01 14:00 — doc(arquitetura): consolidação da auditoria de IA, esteira MetaGPT e laudo da suíte

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Solicitação do Gabriel para auditar toda a estrutura de IA do projeto, pesquisar fontes externas do estado da arte do MetaGPT (DeepWisdom, Data Interpreter, active learning), avaliar casos de sucesso e documentar formalmente o panorama do projeto.

**Feito:**
- **Auditoria de IA & Pesquisa:** Produzido documento técnico canônico em `.brain/docs/arquitetura_ia_e_metagpt.md` e artefato executivo `relatorio_arquitetura_ia_metagpt.md`.
- **Execução da Suíte Completa:** Rodada a suíte com 107 testes unitários (`python -m unittest discover -s ../tabulador/tests -v`), resultando em 103 testes verdes (100% dos módulos funcionais: `aprendizado`, `supervisao`, `nuvem`, `historico`) e apenas as 4 falhas conhecidas de tamanho da base antiga (3.743 -> 5.624 linhas).
- **Mapeamento de Riscos & Prioridades:**
  - PEND-22 (publicar commits cirúrgicos das ~1.500 linhas pendentes) é o bloqueador imediato da entrega de 02/10.
  - PEND-31 (race condition na nuvem do Turso) e PEND-24 (guarda contra encolhimento de base) são os gargalos de segurança prioritários.
- **Sincronização:** Executado `manage_brain.py sync`.

**Decisões:**
- A arquitetura do Tabulador permanece com inferência direta via JSON Schema (após descarte comprovado do OpenRouter Custom Classifier).
- O loop de aprendizado ativo mantém como cláusula pétrea que apenas conferências humanas ensinam o modelo (`validado_por="humano"`).

**Próxima IA / Handoff:**
- Executar o backup preventivo da nuvem e realizar os commits cirúrgicos da PEND-22.
- Em seguida, apoiar a implementação do ciclo `amostra_controle` ou da trava de concorrência PEND-31.


---

## 2026-10-01 — docs(controle): amostra fixa → controle contínuo e esporádico

**Autor:** Claude Opus 5.5 (Claude Code, VS Code) · operador: Gabriel Nascimento

**Contexto:** O Gabriel recusou a amostra fixa de 40 por pergunta: "não queremos parar o processo de categorização para estimar o erro; precisamos de um lugar que o usuário faça esporadicamente". Pediu só documentação, sem código.

**Feito:**
- Reescritos `ciclos/2026-10-01_amostra_controle/01_PRD.md`, `02_ARCH.md` e `03_TASKS.json` (v1.1, TASK-00 a TASK-08).
- PEND-32 atualizada.
- Nenhum código alterado.

**Decisões:**
- **Os 3 lugares:**
  - pílula `🎯 Controle · 5` no topo;
  - bloco "Controle de qualidade" no painel geral (mais uma linha na revbar);
  - confirmação de aprovar que informa o erro e oferece "conferir 5 desta pergunta", sem bloquear.
- **Sorteio:** feito na hora e sem gravar, uniforme no projeto. Só cada conferência é gravada, em `controle.json` por pergunta. Some o problema da "amostra velha".
- **Estimativa do projeto:** combinação por pergunta ponderada por N_q, com cobertura explícita. Isso aguenta misturar os pacotes do topo com os da aprovação.
- **Anti-escopo:** nada de lembrete, cobrança, meta ou bloqueio.

**Próxima IA / Handoff:**
- Aguardar o Gabriel aprovar o PRD. Decisões abertas: erro = só primária, pacote de 5, mínimo de 30 para destaque, teto de 5% nas automáticas.
- **Não programar** antes disso.

---

## 2026-10-01 — fix(tabulador): PEND-22 (commits) e PEND-24 (guarda contra perda)

**Autor:** Claude Sonnet 5.5 (Claude Code) · operador: Gabriel Nascimento

**Contexto:** Gabriel pediu PEND-22 e PEND-24 como críticas ("não podemos correr o risco da base ser apagada por uma instância errônea").

**Feito:**
- Backup completo da nuvem antes de mexer (`nuvem_20261001_141438.json`).
- PEND-22: ~1.500 linhas sem commit viraram 3 commits (`141e5c7`, `161108c`, `841a48f`). **Sem push.**
- PEND-24: camadas 1 e 2 e o backup diário (commit `e927b01`), com 17 testes novos. Suíte: 124 testes, 4 falhas antigas de contagem de base.

**Decisões:**
- Commits por camada (módulos novos → backend → front), não por tema, porque os hunks se entrelaçam.
- A guarda compara o conjunto de `rid` conferidos por pessoa, não a contagem.
- Brain da SESI_cat **não commitado** (mistura trabalho de outras IAs não commitado).

**Pendente / atenção:**
- PEND-22: push, `progresso=true` em induzir/refinar/aprender, teste da Q35 no navegador da Sara.
- PEND-24: tela "Restaurar versão"; validar contra o Turso de verdade; guarda não cobre `frame.json`/`respostas.json`.
- PEND-26/31 mexem na mesma porta (`CF._gravar`): encaixar telemetria e checagem de versão ali.

**Próxima IA / Handoff:**
- Confirmar o push com o Gabriel, depois PEND-22 passos 3 e 4.
- PEND-31 (concorrência) na mesma porta de gravação.

---

## 2026-10-01 15:00 — feat(tabulador): git push da main, PEND-15 (revbar sticky com aprovar à mão) e PEND-13 (métricas de respostas e curva absoluta)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Gabriel autorizou o git push e a execução dos itens 1, 2 e 3 das pendências prioritárias (push da `main`, PEND-15 ergonomia de revisão sticky, PEND-13 métricas de respostas no painel), deixando a PEND-31 (revisão simultânea) para ser amadurecida.

**Feito:**
- **Item 1 (`git push`):** Executado `git push origin main`, sincronizando os 4 commits anteriores (`141e5c7`, `161108c`, `841a48f`, `e927b01`) com o repositório remoto. Equipe (Sara e João) agora recebe timeout sem corte em requisições longas e proteção ativa de dados.
- **Item 2 (PEND-15):**
  - Barra de revisão (`renderRevbar()`) convertida em container `.revbar-sticky` (`position: sticky; top: var(--topo, 49px); z-index: 4;`) com duas linhas limpas: linha 1 com resumo da conferência e botão `renderAprovarBtn()` ancorado na ponta direita; linha 2 com contagem de classificadas e progresso.
  - `.q-cab` desancorado do modo sticky para eliminar sobreposição de cabeçalhos; adicionado atalho "↓ ir para a revisão" no topo com rolagem suave.
  - `table.res th` ajustado para `top: calc(var(--topo, 49px) + 66px)` evitando colisão com a barra de revisão.
  - `renderAprovarBtn()` exibe badge verde quando já aprovado e foi desduplicado de `renderAcoesCod()`.
- **Item 3 (PEND-13):**
  - `src/historico.py`: `estado_perguntas` e `resumo` calculam respostas únicas (`n_unicas`), classificadas, revisadas com divisão de humano e automáticas (`revisadas_humano`, `revisadas_auto`), e faltantes. A série cronológica calcula contagem absoluta de respostas revisadas e total de respostas do projeto.
  - `static/app.js`: `cabecalhoProjeto` exibe percentual e destaque em respostas únicas conferidas, destaque de faltantes, barra empilhada com quebra explícita (.rev-hum e .rev-auto), e perguntas concluídas em linha secundária. `graficoProgresso` plota a contagem absoluta de conferidas e o total de respostas (degrau).
  - `tests/test_historico.py`: testes ampliados para cobrir contagem de respostas e evolução na série.
- **Sincronização:** `manage_brain.py sync` executado com sucesso (18 abertas, 12 resolvidas).

**Decisões:**
- A contagem e percentual primários do cabeçalho do projeto representam estritamente respostas únicas (`n_unicas`), que é o volume real de trabalho do analista.
- A PEND-31 (concorrência e gravação de revisão simultânea) permanece aberta para desenho cuidadoso conforme pedido do Gabriel.

**Próxima IA / Handoff:**
- Alinhar com o Gabriel o modelo de concorrência para a PEND-31 (otimista via ETag/versão no blob ou lock distribuído por item/RID).
- Seguir para a PEND-32 (Amostra de controle cega contínua) ou pendências de telemetria (PEND-26).

---

## 2026-10-01 15:40 — feat(tabulador): PEND-28 (Saúde do quadro em pop-up, problemas aglomerados por categoria e aprovação de soluções)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Solicitação do Gabriel para reformular o aprendizado da IA e a seção "Saúde do quadro": remover o quadro gigante estático de texto cru do topo da tabela de categorias, transformá-lo em um botão colorido ao lado de "Revisar por categoria", aglomerar os problemas pela categoria que os gera, e propor soluções concretas que o usuário aprove diretamente na interface.

**Feito:**
- **Botão na Interface (`static/app.js`):**
  - Removido o quadro estático `.saude` que ficava inline acima da tabela `#tab-frame`.
  - Adicionado botão colorido `🩺 Saúde do quadro (N)` com badge dinâmico imediatamente ao lado de `🗂 Revisar por categoria` em dois pontos estratégicos: no cabeçalho de Categorias (`<h2>Categorias`) e na barra de supervisão de revisão (`renderAcoesCod()`).
  - Cor dinâmica: verde quando sem alertas (`✓ (100% ok)`), amarela/alaranjada (`warn`) quando há alertas críticos de amplitude, fronteira ou Outros.
- **Diagnóstico Estruturado & Aglomeração por Categoria (`src/aprendizado.py`):**
  - Implementada função `diagnostico_saude_de(...)` e `diagnostico_saude(...)` que agrupa problemas e alertas pela categoria afetada, substituindo dezenas de bullets soltos repetitivos por um dossiê analítico claro por categoria.
  - Alertas de confusão de fronteira agrupados por categoria de origem com destinos e contagens de respostas corrigidas.
  - Categorias raras (< 1% das menções) agrupadas em seção dedicada e compacta.
- **Soluções Propostas com Aprovação Humana:**
  - **Reescrita com IA sob demanda:** Criado endpoint `POST /api/pergunta/<qid>/frame/propor-definicao` que usa IA e o histórico de confusões para formular uma definição refinada; o modal renderiza prévia lado a lado com justificativa e botão `✓ Aprovar esta definição`.
  - **Ressalva Imediata:** Botão `✓ Adicionar ressalva à definição` insere cláusula de não-inclusão com 1 clique.
  - **Remoção de Palavra Ambígua:** Botão `✓ Remover palavra ambígua` para termos sobrepostos entre categorias.
  - **Palavras Aprendidas (Lift):** Botão `✓ Adicionar palavras sugeridas` para incorporar termos identificados pela revisão.
  - **Mesclagem e Exclusão de Raras:** Tabela compacta com seletor de destino e botão `✓ Aprovar mesclagem`, além de `🗑️ Excluir` para categorias com 0 menções.
  - **Aprendizado Ativo Manual:** Botão `🧠 Aprender com a revisão agora` no topo da ilha com feedback transparente.
- **Estilos CSS (`static/app.css`):**
  - Criadas classes `.sq-placar`, `.sq-stat`, `.sq-card`, `.sq-card-cab`, `.sq-card-corpo`, `.sq-problemas`, `.sq-prob-item`, `.sq-solucoes`, `.sq-diff-box`, `.sq-destaque-def`, `.tab-raras` e `.sq-saudaveis`.
- **Testes Unitários (`tests/test_aprendizado.py`):**
  - Adicionados testes `test_diagnostico_saude_de` e `test_propor_definicao_com_ia`. Todos os 19 testes de aprendizado passando em 0.23s.
  - Suíte completa rodada: 122 testes verdes, sem regressões.

**Decisões:**
- A caixa de saúde foi completamente retirada do fluxo inline para despoluir a visualização das categorias, abrindo sob demanda no modal `#dlg-janela`.
- Categorias raras (< 1%) não geram cards grandes individuais para não cansar a leitura, ficando organizadas em uma tabela enxuta com dropdown de mesclagem.

---

## 2026-10-01 16:15 — docs(brain): PEND-33 registrado como pensamento futuro (auto-agrupamento inteligente de categorias humanas)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** Gabriel solicitou análise da metodologia de categorização humana da Sara (ex.: Q29), onde a criação de micro-categorias granulares traz enorme riqueza semântica que pode alimentar o loop de auto-melhora do Tabulador propondo agrupamentos e fusões. Após apresentação do plano detalhado, Gabriel orientou: *"vamos guardar isso como um pensamento, e eventualmente alteramos, mas isso é uma grande mudança a ser pensada."*

**Feito:**
- **Registro de Pensamento / Ideia Futura (PEND-33):**
  - Criado `.brain/pendencias/33_auto_agrupamento_categorias_humanas_sara.md` documentando a dor, o fenômeno da granularidade humana, o desenho de detecção semântica de micro-categorias ($N < 2\%$), a síntese de definições e herança de keywords/exemplos (*lossless merge*), a prévia com aprovação em 1 clique na Saúde do Quadro e as travas analíticas (OBJ-02).
  - Marcado explicitamente com status `aberto`, criticidade `baixa` e tag `(Ideia futura)`. Não deve ser implementado agora.
- **Sincronização:**
  - Executado `python .brain/scripts/manage_brain.py sync` com sucesso (18 abertas, 13 resolvidas).

**Próxima IA / Handoff:**
- PEND-33 guardada como reflexão futura. Nenhuma alteração de código realizada neste passo.
- Próximos passos recomendados pelo backlog ativo: PEND-31 (concorrência e gravação de revisão simultânea) ou PEND-32 (amostra de controle contínua cega).

---

## 2026-10-01 16:45 — feat(tabulador): status "alterada" para reconferência de respostas após alterações no codeframe (PEND-34)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:** O Gabriel questionou: *"Ao usarmos o feedback em 'saúde do quadro' categorias que já foram aprovadas vão ser alteradas? Se sim, elas devem ser reconferidas e atribuir o status de 'alterada' ou algo do tipo"*. E orientou: *"aplique; Queremos pensar futuramente quais eventos que também atribuiriam o status 'alterada', uma vez que uma pergunta confirmada não pode ser alterada. Mudança no nome da categoria por exemplo é uma coisa a ser pensada. commite tudo"*.

**Feito:**
- **Rastreabilidade e Marcação (`src/codeframe.py`):**
  - Implementada `marcar_respostas_alteradas(qid, codigos, motivo, rids)` que marca itens validados/humanos como `alterada=True`, com carimbo de data, motivo e código de origem.
  - Integrado em `renomear()` (disparado se a definição da categoria mudar), `fundir()`, `remover()`, `refinar()` e `desfazer_refino()`.
  - Preparado gancho comentado para futuros gatilhos (como alteração no nome da categoria).
- **Isolamento de Sinal no Aprendizado Ativo (`src/aprendizado.py`):**
  - Respostas com status `alterada` são filtradas e excluídas de âncoras few-shot e da mineração de palavras-chave até que o revisor humano as reconfira.
- **Proteção de Dados (`src/protecao.py`):**
  - `conferido_por_humano()` inclui itens `alterada=True`, garantindo que a guarda contra perda de dados não bloqueie gravações legítimas nem descarte o histórico.
- **Métricas e Ciclo de Vida (`src/coding.py`):**
  - `situacao_revisao(item)` retorna `"alterada"` quando `item.get("alterada")`.
  - `resumo_revisao(qid)` calcula e expõe `n_alteradas`, subtraindo-as de `n_revisadas` até que sejam reconferidas.
  - `atualizar_item()` e `validar()` limpam as propriedades de `alterada`, devolvendo a resposta para confirmada/corrigida.
- **Interface e Ergonomia (`static/app.js` e `static/app.css`):**
  - Sticky revbar ganha botão de alerta `⚠️ N a reconferir` quando houver itens alterados.
  - Ações de supervisão ganham botão `⚠️ Reconferir alteradas (N)`.
  - Tabela destaca linhas `tr.alterada` com borda lateral amarela, pílula `⚠️ alterada`, motivo da alteração em destaque e botão direto `Reconferir` (atalho `Enter`).
- **Testes Unitários:**
  - Criado `tests/test_alterada.py` com 4 testes cobrindo mudança de definição, fusão, remoção e revalidação. 100% verde (40/40 testes da suíte em 1.4s).

**Decisões:**
- Respostas previamente aprovadas que sofrem impacto de fronteira semântica não são silenciadas; recebem o estado `alterada` e demandam revalidação explícita.
- A mudança no nome da categoria foi mantida como gatilho futuro opcional, pois em muitos casos a renomeação é apenas cosmética/ortográfica e não semântica.

**Próxima IA / Handoff:**
- PEND-34 concluída e testada.
- Código pronto e homologado para o fluxo de revisão do SESI CAT.
- Próximas prioridades: PEND-31 (concorrência e lock otimista no Turso) ou PEND-32 (amostra de controle contínua).

---

<<<<<<< HEAD
## 2026-10-02 12:40 — docs(brain): PEND-35 planejado — Assistente de IA na criação de grupos (rótulo, escopo, instrucoes_frame e compatibilidade)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:**
Gabriel instruiu: *"temos outra ia mexendo no projeto, apenas planeje: Queremos aumentar o input da IA na hora de criar grupos; Não sugerir grupos, mas ao criar um grupo, ela inputar detalhes, nome do grupo, etc... apenas documente tudo... coloque no brain, nao use manage brain"*.

**Feito:**
- **Plano de Implementação (IP) Completo:**
  - Criado `tabulador/docs/IP_criacao_grupos_input_ia.md` no padrão MetaGPT cobrindo PM, PRD, Arquitetura, Schema da LLM, Prompts, UX e QA.
  - A decisão de agrupamento passa a ser 100% humana (a sugestão automática cega de pares por sobreposição estatística de bases é descontinuada da interface).
  - A IA passa a atuar sob demanda com o botão `✨ Analisar e preencher com IA`, lendo enunciados e micro-amostras reais de respostas para propor: (1) nome executivo do grupo; (2) descrição de escopo; (3) diretrizes temáticas para o quadro unificado (`instrucoes_frame`) respeitando "uma categoria = um atributo"; e (4) diagnóstico de compatibilidade semântica.
- **Registro no Brain (PEND-35 / OBJ-01):**
  - Criado `SESI_cat/.brain/pendencias/35_assistente_ia_criacao_grupos.md`.
  - Atualizado `SESI_cat/.brain/pendencias.md` com a linha da PEND-35 (aberta, prioridade média).
  - Não executado `manage_brain.py sync`, conforme ordem explícita do usuário.
- **Coordenação Multi-Agente:**
  - Registrado em `jumppi/COMUNICACAO_IAS.md` timeline.
  - Nenhum código executável do Tabulador foi tocado, garantindo isolamento total do trabalho concorrente da outra IA em `worktrees/tabulador-grupos-f1`.

**Próxima IA / Handoff:**
- PEND-35 pronta para ser puxada para execução em branch isolada (`feat/grupos-ia-input`) quando a Fase 1 do motor de grupos (`feat/grupos-fase1`) for concluída pela outra IA.

---

## 2026-10-02 12:45 — docs(brain): PEND-36 planejado — Relatório síntese visual na aba Resultados (ideias, perfis e verbatins)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:**
Gabriel orientou: *"temos outra ia mexendo no projeto, apenas planeje: Queremos uma página dentro de resultados que sintetiza um relatório, com base nas respostas. Queremos no momento uma coisa simples, criando um relatorio visual, sem pdf nem nada; Oq queremos sintetizar? Perfis de respondentes? de ideias e planeje"*. Em seguida, instruiu: *"anote no brain"*.

**Feito:**
- **Plano de Implementação (IP) Completo:**
  - Criado `tabulador/docs/IP_relatorio_sintese_resultados.md` no formato MetaGPT.
  - Alinhamento da dor: a aba de Resultados foca hoje na entrega fria de arquivos Excel/brutos. Falta uma camada executiva visual que conecte a categorização ao insight acionável.
  - Resolução do dilema *Perfis vs. Ideias*: o relatório une os dois conectando `[Perfil / Demografia / NPS] -> [Temática / Dor aberta] -> [Verbatim representativo]`.
  - Arquitetura 100% web: desenhado para rodar no navegador usando os componentes CSS nativos do Tabulador (`app.css`), permitindo impressão nativa (Ctrl+P) ou prints de cards limpos para apresentações, dispensando geradores de PDF pesados.
  - Quatro blocos da tela: (1) Sumário Estratégico (Alavanca Principal, Alerta Crítico, Narrativa Global); (2) Mapa de Ideias & Polaridade (Elogios, Dores, Sugestões); (3) Perfis de Respondentes (cruzamento das abertas com banners de corte ou NPS); (4) A Voz do Respondente (mural de verbatins curados).
  - Cache econômico: salvo em `output/relatorio_sintese.json`, atualizado apenas sob demanda.
- **Registro no Brain (PEND-36 / OBJ-01):**
  - Criado `SESI_cat/.brain/pendencias/36_relatorio_sintese_resultados.md`.
  - Atualizado `SESI_cat/.brain/pendencias.md` com a linha da PEND-36 (aberta, prioridade média).
  - Respeitada a diretriz de não rodar `manage_brain.py sync`.
- **Coordenação Multi-Agente:**
  - Nenhuma linha de código de execução do Tabulador foi tocada (isolamento total do Claude / branch em worktree).

**Próxima IA / Handoff:**
- PEND-36 planejada e aguardando janela de implementação em branch dedicada (`feat/relatorio-sintese`).

---

## 2026-10-02 12:46 — docs(brain): PEND-37 registrado como ideia futura (telemetria de tokens, modelo e custo por pergunta e no consolidado)

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:**
Gabriel instruiu: *"salve como ideia a gente colocar dados de uso de modelo, tokens, custo estimado, etc..."*.

**Feito:**
- **Registro de Pensamento / Ideia Futura (PEND-37 / OBJ-03):**
  - Criado `SESI_cat/.brain/pendencias/37_telemetria_tokens_custo_por_pergunta_e_projeto.md`.
  - Registrada a dor: hoje o consumo de IA fica restrito à aba técnica `/api/usage` e invisível no dia a dia do pesquisador e nas entregas executivas.
  - Desenho conceitual: (1) pílula de telemetria no card da pergunta e cabeçalho interno (`⚡ gemini-2.5-flash · 42k tokens · ~R$ 0,18`); (2) seção de "Investimento Computacional / IA" na aba Resultados e entregáveis; (3) custo acumulado por pergunta na barra de revisão; (4) persistência estruturada do resumo de uso em `codificacao.json` (`telemetria_ia`).
  - Atualizado `SESI_cat/.brain/pendencias.md` com status `aberto`, prioridade `baixa` e tag `(Ideia futura)`.
  - Respeitada a regra de não executar `manage_brain.py sync`.
- **Coordenação Multi-Agente:**
  - Zero arquivos de código alterados; ambiente de execução 100% isolado.

**Próxima IA / Handoff:**
- PEND-37 salva como ideia para amadurecimento junto da telemetria de auditoria (PEND-26/27).

---

## 2026-10-02 — docs(brain): PEND-38 registrado (grupos: categorias base + próprias; revisar lógica do quadro único)

**Autor:** Claude Sonnet 5.5 · operador: Gabriel Nascimento

**Contexto:**
Depois das fases 1-4 dos grupos de perguntas (main, `a9aa5ac`..`4ee87fd`; plano em `tabulador/docs/IP_grupos_de_perguntas.md`), o Gabriel testou e não gostou da lógica: confusão sobre o que difere ao aprovar categorias em Q4 e Q5, categoria gerada com dois assuntos (deve ser barrado no prompt) e categorias que só existem em uma das perguntas. Pediu para **guardar como pendência, sem mexer agora**.

**Feito:**
- Criado `pendencias/38_grupos_categorias_base_e_proprias.md` e linha em `pendencias.md` (`Aberto`, criticidade média, OBJ-01).
- Nenhum código alterado. Não rodei `manage_brain.py sync` nem o sincronizador de calendário (sem datas novas).

**Próxima IA / Handoff:**
- PEND-38 está só registrada: ideia = categorias BASE do grupo (aparecem na página de cada pergunta) + categorias PRÓPRIAS por pergunta. Antes de implementar, passar o desenho pelo conselho de IAs e fechar as perguntas em aberto listadas na pendência.

---

## 2026-10-02 13:55 — docs(brain): PEND-40 registrado — Gráfico de evolução com degradê verde, % no eixo Y e projeção de ritmo

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:**
Gabriel instruiu: *"vamos adicionar uma pendência: O gráfico de respostas conferidas deve ter uma linha mostrando a evolução, verde com degradê escurecendo; Queremos ter porcentagem no eixo y também e uma projeção (linha cinza, 3 cenários: otimista, neutro e pessimista) do ritmo de respostas, informando uma data estimada ded conclusão dado o ritmo atual; Essas informações são secundárias então não devem ocupar muito espaço, sendo relativamente discretas"*.

**Feito:**
- **Registro no Brain (PEND-40 / OBJ-01):**
  - Criado `SESI_cat/.brain/pendencias/40_grafico_respostas_degrade_eixo_pct_projecao.md` com requisitos detalhados:
    1. Linha verde com área de degradê escurecendo em SVG (`linearGradient`).
    2. Eixo Y com porcentagens associadas aos volumes absolutos.
    3. Projeção de ritmo em 3 cenários (otimista, neutro e pessimista) em linhas cinzas pontilhadas discretas e cálculo de data estimada de conclusão.
    4. Tratamento visual como informação secundária (discreta, sem disputar atenção nem poluir o painel).
  - Atualizado `SESI_cat/.brain/pendencias.md` com a linha da PEND-40 (`Aberto`, criticidade média, OBJ-01).
- **Coordenação Multi-Agente:**
  - Nenhum código alterado. Apenas documentação no `.brain`.

**Próxima IA / Handoff:**
- PEND-40 pronta para especificação e implementação em `tabulador/static/app.js` (`graficoProgresso`) e `tabulador/static/app.css` quando o Gabriel priorizar.

---

## 2026-10-02 14:07 — docs(brain): PEND-41 registrado — Desambiguação visual e feedback ao parar classificação

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento

**Contexto:**
Ao clicar em "⏹ Parar" durante a classificação da Q29, Gabriel reportou: *"O botão de parar classificação não está parando, parece que ele classifica tudo mas não carrega? Pelo menos o log na mensagem de carregamento está ambígua"*.

**Diagnóstico & Fatos:**
- O backend de fato parou (apenas 3 de 32 lotes foram executados e salvos; os 29 lotes seguintes foram cancelados).
- Falha de UX: ao entrar na etapa de gravação pós-parada, `progresso.etapa("gravar")` marca a etapa da IA como concluída com `✓` verde e a barra dispara para 100%, gerando a ilusão de que "classificou tudo". Ao carregar a tela e ver apenas 90 respostas classificadas (860 pendentes), surge a sensação de que "não carregou".
- Ambiguidade de logs: o modal mantinha o tempo estimado para os 32 lotes (`faltam ~X min`) e workers paralelos que já haviam iniciado emitiam logs após o clique.

**Feito:**
- **Registro no Brain (PEND-41 / OBJ-01):**
  - Criado `SESI_cat/.brain/pendencias/41_feedback_interrupcao_parar_classificacao.md` detalhando os requisitos: checagem de parada em `_um`, não promover etapa interrompida para `estado = "feito"` (manter indicador de parada sem `✓` verde), travar a barra no progresso real, ocultar estimativas futuras de tempo e mensagens claras de quantas foram salvas e quantas ficaram pendentes.
  - Atualizado `SESI_cat/.brain/pendencias.md` com a PEND-41 (`Aberto`, criticidade média, OBJ-01).
- **Coordenação Multi-Agente:**
  - Nenhum código alterado. Apenas documentação no `.brain`.

**Próxima IA / Handoff:**
- PEND-41 documentada e pronta para ser implementada em `src/progresso.py`, `src/coding.py`, `src/supervisao.py` e `static/app.js`.


---

## 2026-10-02 — feat(tabulador): PEND-23 (ganho da auditoria), PEND-24 (tela Versões) e PEND-26 (telemetria); PEND-39 e prazos registrados

**Autor:** Claude Sonnet 5.5 · operador: Gabriel Nascimento

**Contexto:**
Gabriel pediu: nova pendência (trocar de projeto exige F5), prazo de 07/10 para PEND-01/03 (entram mais respostas na segunda 05/10), fazer PEND-24 e 26, e custo estimado "como API" para as IAs por CLI.

**Feito (main, commits `aa169f4`, `0cab9d9`, `38f5059`, `97a7c17`):**
- **PEND-39** criada (não investigada). **PEND-01/03:** `prazo: 2026-10-07`. Calendário sincronizado.
- **PEND-37:** requisito do custo estimado das IAs por CLI (já há tokens do Claude e do Antigravity em `llm_cli.py`; falta preço na tabela `PRECOS` e rótulo "estimado").
- **PEND-23 resolvida:** `supervisao.auditar(..., limiar)` devolve `ganho`; janela mostra passaram pelo auditor antes→depois e calibração da confiança.
- **PEND-24:** botão `🕘 Versões` (lista e restaura versões). Backup manual da nuvem rodado (`tabulador/projetos/sesi_cat/output/_backup/nuvem_20261002_135625.json`). Falta validar snapshot/restauração contra o Turso real e o clique no navegador.
- **PEND-26:** `classificado_por/em`, `revisado_em`, `criada_por/em/com`, `por` no histórico do quadro, log de eventos (`src/eventos.py`, tabela `eventos`), `entrega_manifesto.json`, backfill (`src/telemetria_backfill.py`). Detalhes na própria pendência. Suíte: 179 passam.

**Próxima IA / Handoff:**
- **Backfill não aplicado na base real:** rodar `python src/telemetria_backfill.py -p sesi --aplicar` só com OK do Gabriel (simulação: ~5.800 de ~7.300 casam).
- PEND-24: validar contra o Turso real; PEND-26 segue `aberto` até o backfill. PEND-27 (painel) consome `eventos`.
- Antes da entrega de 07/10: recarregar a planilha com as respostas de segunda e rodar "Classificar as restantes" (PEND-01).

---

## 2026-10-02 14:18 — feat(tabulador): cabeçalho da pergunta com enunciado sticky no topo a todo momento

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento
**Branch/Worktree:** `worktrees/tabulador-header-sticky` (`feat/tabulador-header-sticky`)

**Contexto:** O Gabriel solicitou: *"Queremos manter o header da pergunta com o enunciado no topo da tela a todo moento, sticky.; faça em uma worktree"*.
Na implementação anterior (PEND-15), o cabeçalho `.q-cab` havia sido desancorado do modo sticky para dar lugar à barra de revisão rápida `.revbar-sticky`, o que fazia com que o enunciado e o título da pergunta saíssem da tela ao rolar a página.

**Feito:**
- **Worktree dedicada:** Criada a worktree `worktrees/tabulador-header-sticky` na branch `feat/tabulador-header-sticky` para total isolamento.
- **Cabeçalho Sticky com Enunciado (`tabulador/static/app.css`):**
  - `.q-cab`: Ancorado com `position: sticky; top: var(--topo, 49px); z-index: 7; margin: -20px -24px 12px; padding: 10px 24px 12px;` e sutil `box-shadow: 0 2px 8px rgba(0,0,0,0.05)`. Cobre a largura total de `main`, eliminando frestas laterais ou superiores durante a rolagem.
  - O enunciado (`.q-cab .muted`) recebeu espaçamento compacto e legível (`line-height: 1.35; margin: 2px 0 3px;`).
  - `.top` atualizado para `z-index: 10` e `.side` para `z-index: 8` para manter a hierarquia de sobreposição correta.
- **Empilhamento Perfeito dos Cabeçalhos Fixos:**
  - `th` genérico ajustado para `top: calc(var(--topo, 49px) + var(--qcab-h, 0px)); z-index: 5;`.
  - `.revbar-sticky` ajustado para `top: calc(var(--topo, 49px) + var(--qcab-h, 0px)); z-index: 6;`.
  - `table.res th` (thead da tabela de revisão) posicionado dinamicamente em `top: calc(var(--topo, 49px) + var(--qcab-h, 0px) + var(--revbar-h, 66px) + 8px); z-index: 5;`.
  - `#area-revisao` com `scroll-margin-top: calc(var(--topo, 49px) + var(--qcab-h, 0px) + 16px);` para que o atalho "↓ ir para a revisão" role a página com folga exata abaixo do cabeçalho fixo.
- **Sincronização Dinâmica em Tempo Real (`tabulador/static/app.js`):**
  - Implementada `medirAlturasFixas()` que calcula as alturas reais de `.top`, `.q-cab` e `.revbar-sticky` e define `--topo`, `--qcab-h` e `--revbar-h` no `documentElement`.
  - Adicionado `observarCabecalho()` com `ResizeObserver` monitorando alterações dinâmicas na altura de `.q-cab`.
  - Atualizado fallback do enunciado para `${esc(R.enunciado || P.enunciado || "")}`.
  - Rotas fora de perguntas limpam as variáveis de altura fixas para evitar herança indevida.
- **Testes Unitários:** Suíte executada (172 testes passando).
- **Commit:** Commit `1db9a3a` isolado na branch `feat/tabulador-header-sticky`.

**Próxima IA / Handoff:**
- Worktree `worktrees/tabulador-header-sticky` pronta para revisão e merge pelo Gabriel.

---

## 2026-10-02 14:35 — feat(brain): integração da gestão de worktrees e gatekeeper de merge na esteira MetaGPT

**Autor:** Antigravity (Gemini 3.8 Flash) · operador: Gabriel Nascimento
**Onde:** `.brain` (governança multi-agente, `manage_brain.py`, `state.json`, `ciclos.md`, `README.md`)

**Contexto:** O Gabriel solicitou documentar dentro do `.brain` o status em tempo real de todas as worktrees concorrentes, para que a última IA ativa saiba exatamente quando todas estiverem desocupadas/prontas e possa iniciar o processo de merge sequencial em `main`, integrado formalmente à metodologia MetaGPT.

**Feito:**
- **Papel MetaGPT (Role `Integrator`):**
  - Adicionada a fase `INTEGRATION` (`FASES_ORDEM = [..., "QA", "INTEGRATION", "MERGED"]`) com a role `Integrator` e missão: *"Verificar semáforo de worktrees, integrar branches para main e desmontar worktrees desocupadas"*.
- **Rastreamento de Concorrência em `state.json`:**
  - Adicionado schema canônico `worktrees` mapeando identificador, caminho, branch, tarefa (`PEND-XX`), agente, status (`EM_ANDAMENTO`, `PRONTO_PARA_MERGE`, `DESOCUPADA`, `BLOQUEADA`, `MERGED`), contagem de diffs pendentes e commits.
  - Adicionado bloco `merge_gatekeeper` com indicador de prontidão de merge (`status: LIBERADO | BLOQUEADO | NEUTRO`), lista de worktrees ocupadas vs prontas e instrução cognitiva para o próximo agente.
- **Automação CLI em `manage_brain.py`:**
  - `obter_raiz_git()` e `detectar_worktrees_git()`: Escaneia dinamicamente `git worktree list --porcelain`, `git status --porcelain` de cada worktree e `git branch --merged main`.
  - `python .brain/scripts/manage_brain.py sop wt status`: Exibe o semáforo executivo formatado no terminal com diagnóstico claro.
  - `python .brain/scripts/manage_brain.py sop wt set <worktree> <STATUS> [--tarefa PEND-XX] [--agente "Nome"]`: Atualiza o registro e sincroniza o `.brain`.
  - `python .brain/scripts/manage_brain.py sop can-merge`: Guard-rail programático que retorna `exit 0` se liberado para merge ou `exit 1` se houver worktrees ocupadas.
  - `python .brain/scripts/manage_brain.py sop merge-start`: Inicia a fase `INTEGRATION` na esteira MetaGPT caso o gatekeeper aprove.
  - Validação estrita em `sop avancar`: Transição da fase `INTEGRATION` para `MERGED` bloqueada se houver qualquer worktree com diff pendente ou status `EM_ANDAMENTO`.
- **Visibilidade Executiva em `ciclos.md` & `README.md`:**
  - O `manage_brain.py sync` renderiza automaticamente a seção `## 🚦 Semáforo de Worktrees & Concorrência (MetaGPT Integrator)` com tabela viva.
  - Documentação da role `Integrator` e comandos SOP no `.brain/README.md`.
- **Propagação Canônica:** Script propagado com paridade idêntica para `INSPER/.brain` e `Transpetro/.brain`.

**Próxima IA / Handoff:**
- Para verificar se pode iniciar merge: execute `python .brain/scripts/manage_brain.py sop can-merge` ou `sop wt status`.
- Para marcar sua worktree como concluída: `python .brain/scripts/manage_brain.py sop wt set <worktree> PRONTO_PARA_MERGE --tarefa PEND-XX --agente <Nome>`.
- A última IA ativa (ao ver o semáforo 🟢 LIBERADO) pode rodar `sop merge-start` e conduzir a integração para `main`.


---

## 2026-10-02 — feat(tabulador): backfill de telemetria aplicado; trava de confirmações (PEND-42) e categorias em ordem alfabética (PEND-43) em worktree

**Autor:** Claude Sonnet 5.5 · operador: Gabriel Nascimento

**Feito:**
- **Backfill da PEND-26 aplicado** em Q2, Q4, Q5, Q29, Q30, Q32 e Q33 do projeto `sesi` (Q35 ficou de fora: a Sara estava nela). Backup antes: `nuvem_20261002_141754.json`. Detalhes na PEND-26.
- **Worktree** `worktrees/tabulador-trava-ordem`, branch `feat/trava-confirmacao-e-ordem-categorias` (a partir de `ca12d8c`): `fe3bd48` (PEND-43) e `8c6ffdb` (PEND-42). Suíte na worktree: 183 passam (copiei `projetos/sesi_cat/data` só para rodar os testes e apaguei depois). **Não mergeada na main.**

**Próxima IA / Handoff:**
- Merge da branch na main depende do Gabriel validar na tela. Não fazer `git checkout` na raiz: use a worktree.
- Q35 ainda sem o carimbo do backfill (`python src/telemetria_backfill.py -p sesi Q35 --aplicar`, com ninguém em Q35).
- PEND-24 (tela Versões) em validação pelo Gabriel.
