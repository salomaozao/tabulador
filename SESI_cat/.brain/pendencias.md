# Sumário Executivo de Pendências e Backlog

Este arquivo é o inventário de pendências ativas, bloqueios e itens a monitorar no projeto **SESI Minas — Categorização (Satisfação das Escolas)**.

Para aprofundamento técnico, plano de ação e responsáveis de cada item, consulte os arquivos individuais no diretório [`pendencias/`](pendencias).

---

## Pendências Abertas / Em Andamento

| ID | Assunto / Pendência | Responsável | Criticidade | Status | Resumo e Ação Necessária | Detalhes |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **[PEND-01](pendencias/01_base_parcial_novas_entrevistas.md)** | **Base parcial - incorporar novas entrevistas até o fim do campo** | Gabriel Nascimento / Jucimara | **Alta** | `Aberto` | A base recebida (3.743 respostas, ~70%) não é a final; devem entrar ~500 entrevistas (disparos de e-mail em 22/09 e 24/09) até o fim do campo em 25/09. Recategorizar só as respostas novas mantendo as validadas. | [Abrir](pendencias/01_base_parcial_novas_entrevistas.md) |
| **[PEND-03](pendencias/03_entrega_processamento.md)** | **Entregar base categorizada para o processamento (PPT + Power BI)** | Gabriel Nascimento | **Alta** | `Aberto` | O processamento começa em 28/09, logo depois do fim do campo. A planilha categorizada (Q*_CAT preenchidas) precisa estar pronta para alimentar o relatório em PPT e Power BI. | [Abrir](pendencias/03_entrega_processamento.md) |
| **[PEND-08](pendencias/08_joao_nao_sincronizado.md)** | **João baixou o Tabulador do GitHub e não vê a revisão sincronizada (falta .env/credenciais da nuvem)** | Gabriel Nascimento | Media | `Aberto` | João clonou o tabulador direto do GitHub, que só traz código (não traz .env nem SESI_cat/data, gitignorados de propósito). Sem as credenciais TABULADOR_TURSO_URL/TOKEN da equipe (ou o atalho OneDrive do SharePoint que o config.py acha sozinho), o app dele grava local e vazio: as respostas antigas da revisão ainda não sincronizaram com o banco da equipe. | [Abrir](pendencias/08_joao_nao_sincronizado.md) |

---

## Pendências Concluídas / Resolvidas

| ID | Assunto | Conclusão | Data Resolução | Registro |
| :--- | :--- | :--- | :---: | :---: |
| *PEND-02* | *Conferir lista de perguntas abertas (7 no pedido x 8 no projeto.py)* | Na planilha, 7 colunas Q*_CAT estão em amarelo (Q2, Q4, Q5, Q29, Q32, Q33, Q35). A Q30_CAT existe, mas não está em amarelo, e o projeto.py a inclui. Perguntar à Jucimara se a Q30 deve ser categorizada. | 2026-09-24 | [Abrir](pendencias/02_conferir_lista_perguntas_abertas.md) |
| *PEND-04* | *Trocar chaves de API expostas (Gemini)* | A GEMINI_API_KEY da variável de ambiente (AIza…oWW8) foi bloqueada pelo Google como vazada. A chave do .env do categorizador (AQ.A…QgzA) funciona, mas apareceu completa numa saída de comando. Gerar chave nova, trocar no ⚙ Configurar IA e apagar a variável antiga. | 2026-09-24 | [Abrir](pendencias/04_trocar_chaves_api.md) |
| *PEND-05* | *Janela dinâmica para aprovar categorias (perfil informativo) + supervisor na interface* | Levar o fluxo do supervisor.py (IA classifica, um segundo modelo audita, aceita sozinho o que tem confiança >= 0,70 com auditoria concordando) para a interface, com uma janela de aprovação que mostre por categoria o perfil de quem citou (NPS, satisfação, retenção, escola) e amostras, para aprovar em bloco. Fazer em commit separado. | 2026-09-24 | [Abrir](pendencias/05_janela_aprovacao_dinamica.md) |
| *PEND-06* | *Conferir quadros de categorias aprovados pelo Claude (Q32/Q33 unificado, Q35) e a fila de revisão* | Na sessão de 23/09 o Claude aprovou quadros sem o pesquisador: Q32 e Q33 com um quadro único de 9 categorias (inclui 'Insatisfação geral' e 'Remete a resposta anterior'; o quadro antigo da Q32 está em output/_backup) e Q35 (14 categorias). Conferir os quadros, revisar as pendentes de cada pergunta e aprovar a codificação para gerar a planilha final. | 2026-09-24 | [Abrir](pendencias/06_conferir_quadros_aprovados_pelo_claude.md) |
| *PEND-07* | *Avaliar guardar a base inteira (não só a revisão) na nuvem, para rodar só o Tabulador sem pasta de projeto local* | Ideia do Gabriel: subir também a base (planilha-fonte/base processada), não só o loop de revisão, para o Turso — assim bastaria rodar o `tabulador` (a pasta `SESI_cat` poderia até ficar dentro dele) sem precisar sincronizar outra pasta de projeto. Avaliada pelo conselho de IAs em 25/09: descartada (over-engineering, risco de dado defasado silencioso e gargalo de upload); o problema real que motivou a ideia (PEND-08) já foi endereçado tornando o aviso de nuvem não configurada acionável. | 2026-09-25 | [Abrir](pendencias/07_base_inteira_na_nuvem.md) |
| *PEND-09* | *Identificação de quem está logado (pessoa ou IA) e sidebar mostrando onde cada um está no projeto* | Ideia do Gabriel: hoje o Tabulador identifica quem está usando a máquina pelo login do Windows (config.USUARIO, usado só para avisar de edição simultânea numa mesma pergunta — ver a presença por pergunta implementada em 2026-09-24). Faltava: (1) identificação explícita na tela inicial; (2) uma sidebar mostrando, para todo o projeto, onde cada pessoa/IA está agora. Desenhado pelo conselho de IAs e implementado em 25/09: nome autodeclarado + sessão por aba + lista de presença no painel lateral esquerdo (não direito — ver nota de escopo); presença de IA via CLI ficou deliberadamente fora, é gambiarra sem heartbeat real de processo. | 2026-09-25 | [Abrir](pendencias/09_identificacao_e_sidebar_presenca.md) |

---

## Como Operar o Backlog
- Para **abrir uma nova pendência**: crie um arquivo `PEND-XX` em `pendencias/` e execute `python .brain/scripts/manage_brain.py sync`.
- Para **resolver uma pendência**: altere `status: resolvido` no frontmatter, adicione `data_resolucao: AAAA-MM-DD` e execute `python .brain/scripts/manage_brain.py sync`.
