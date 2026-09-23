# Sumário Executivo de Pendências e Backlog

Este arquivo é o inventário de pendências ativas, bloqueios e itens a monitorar no projeto **SESI Minas — Categorização (Satisfação das Escolas)**.

Para aprofundamento técnico, plano de ação e responsáveis de cada item, consulte os arquivos individuais no diretório [`pendencias/`](pendencias).

---

## Pendências Abertas / Em Andamento

| ID | Assunto / Pendência | Responsável | Criticidade | Status | Resumo e Ação Necessária | Detalhes |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **[PEND-01](pendencias/01_base_parcial_novas_entrevistas.md)** | **Base parcial - incorporar novas entrevistas até o fim do campo** | Gabriel Nascimento / Jucimara | **Alta** | `Aberto` | A base recebida (3.743 respostas, ~70%) não é a final; devem entrar ~500 entrevistas (disparos de e-mail em 22/09 e 24/09) até o fim do campo em 25/09. Recategorizar só as respostas novas mantendo as validadas. | [Abrir](pendencias/01_base_parcial_novas_entrevistas.md) |
| **[PEND-02](pendencias/02_conferir_lista_perguntas_abertas.md)** | **Conferir lista de perguntas abertas (7 no pedido x 8 no projeto.py)** | Gabriel Nascimento / Jucimara | Media | `Aberto` | Na planilha, 7 colunas Q*_CAT estão em amarelo (Q2, Q4, Q5, Q29, Q32, Q33, Q35). A Q30_CAT existe, mas não está em amarelo, e o projeto.py a inclui. Perguntar à Jucimara se a Q30 deve ser categorizada. | [Abrir](pendencias/02_conferir_lista_perguntas_abertas.md) |
| **[PEND-03](pendencias/03_entrega_processamento.md)** | **Entregar base categorizada para o processamento (PPT + Power BI)** | Gabriel Nascimento | **Alta** | `Aberto` | O processamento começa em 28/09, logo depois do fim do campo. A planilha categorizada (Q*_CAT preenchidas) precisa estar pronta para alimentar o relatório em PPT e Power BI. | [Abrir](pendencias/03_entrega_processamento.md) |
| **[PEND-04](pendencias/04_trocar_chaves_api.md)** | **Trocar chaves de API expostas (Gemini)** | Gabriel Nascimento | **Alta** | `Aberto` | A GEMINI_API_KEY da variável de ambiente (AIza…oWW8) foi bloqueada pelo Google como vazada. A chave do .env do categorizador (AQ.A…QgzA) funciona, mas apareceu completa numa saída de comando. Gerar chave nova, trocar no ⚙ Configurar IA e apagar a variável antiga. | [Abrir](pendencias/04_trocar_chaves_api.md) |

---

## Pendências Concluídas / Resolvidas

| ID | Assunto | Conclusão | Data Resolução | Registro |
| :--- | :--- | :--- | :---: | :---: |


---

## Como Operar o Backlog
- Para **abrir uma nova pendência**: crie um arquivo `PEND-XX` em `pendencias/` e execute `python .brain/scripts/manage_brain.py sync`.
- Para **resolver uma pendência**: altere `status: resolvido` no frontmatter, adicione `data_resolucao: AAAA-MM-DD` e execute `python .brain/scripts/manage_brain.py sync`.
