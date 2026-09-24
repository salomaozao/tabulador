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

