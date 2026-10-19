---
id: PEND-24
titulo: Snapshots automáticos e guarda contra perda da base classificada (nuvem e local)
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, src/nuvem.py, src/codeframe.py, app.py]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
prazo: 2026-10-02
resumo: "Com a nuvem ativa, nuvem.gravar faz upsert (substitui) e _remover apaga de vez, sem lixeira. Um bug pode zerar milhares de respostas conferidas sem deixar rastro. Três camadas: (1) guarda em _gravar: recusa gravar codificacao.json que perca itens validados por humano ou encolha mais de 20% sem liberação explícita; (2) tabela blobs_historico no Turso, append-only, com a versão anterior de codificacao/frame a cada N minutos ou antes de toda operação em massa; (3) backup diário automático do projeto inteiro em output/_backup ao abrir o app, mais uma tela 'Restaurar versão'."
linear: JUM-12
---

# PEND-24: Snapshots e guarda contra perda

- **Camada 1, guarda (barata, fazer primeiro):**
  - em `codeframe._gravar` (e `nuvem.gravar`), quando `nome == "codificacao.json"`, comparar com a versão atual:
    - se `n_validados_humano` cair, ou se `n_itens` cair mais de 20%, levantar `GravacaoSuspeita`;
    - a exceção não ocorre se quem chamou passou `permitir_reducao=True` (apagar, reabrir, desfazer automáticas).
  - Registrar a tentativa em `output/_backup/bloqueios.log`.
  - Teste: `tests/test_protecao.py`.
- **Camada 2, histórico na nuvem:**
  - `CREATE TABLE blobs_historico (projeto, qid, arquivo, dados, gravado_em, por, motivo)`;
  - snapshot antes de toda operação em massa (classificar, reclassificar, auditar, auto-aceitar, mesclar, apagar, aprovar) e no máximo a cada 15 min durante a revisão manual, para não gravar a Q35 inteira a cada ✓;
  - retenção de 7 dias completos, depois um por dia por 60 dias.
- **Camada 3, backup e restauração:**
  - ao iniciar o app, se o último backup em `output/_backup/nuvem_*.json` tiver mais de 24 h, rodar o mesmo `backup` que já existe em `nuvem.py _main`;
  - tela "Restaurar versão" (por pergunta), que lista os snapshots e mostra o diff de contagens antes de restaurar (a restauração também gera um snapshot).
- **Ajustes da revisão do plano (01/10):**
  - O invariante que importa é "**conferidas por humano não diminuem**" sem liberação explícita. Os 20% são secundários: só pegam o desastre grande.
  - PEND-24, PEND-25, PEND-26 e PEND-31 mexem no mesmo ponto (`_gravar` de `codificacao.json`). Fazer **uma única porta de gravação** (guarda + checagem de versão + evento de telemetria + política de snapshot), em vez de quatro remendos em sequência.
  - **Ordem com a PEND-22:** fazer o backup da nuvem **antes** de publicar o código acumulado para as outras máquinas, porque publicar código novo é justamente o risco "uma alteração no código apaga a base".
  - O restaurar precisa ter teste de ponta a ponta: um backup que nunca foi restaurado não está provado.
- **Pré-requisito do PEND-25** (apagar com filtros).
- **Agora:** rodar já um backup manual da nuvem (`python -m src.nuvem backup` ou equivalente) antes de qualquer mudança grande.

## Andamento (01/10, Claude Sonnet 5.5) — commit `e927b01`

- **Camada 1 (guarda): feita.** `src/protecao.py`; `codeframe._gravar/_remover` é a porta única. Recusa gravar `codificacao.json` que perca respostas conferidas por pessoa (compara por `rid`, não por contagem) ou encolha mais de 20% (só acima de 10 itens). Recusas vão para `output/_backup/bloqueios.log`. Reduções intencionais usam `permitir_reducao=True`: desmarcar ✓ (`validar`, `atualizar_item`), desfazer aceite automático, apagar pergunta.
- **Camada 2 (versões): feita.** Tabela `blobs_historico` (nuvem) e `output/_backup/versoes/` (local). Snapshot da versão anterior no máximo a cada 15 min na revisão e sempre antes de classificar, reclassificar, auditar, aceitar/desfazer automático, mesclar, aprovar quadro e apagar. Retenção: 7 dias completos, 1 por dia até 60.
- **Camada 3 (backup/restauração): parcial.** Backup diário ao abrir o app (guarda os 14 mais recentes); rotas `GET /versoes` e `POST /restaurar`; restauração testada de ponta a ponta nos dois modos. **Falta a tela "Restaurar versão" no front.**
- **Testes:** `tests/test_protecao.py`, 17 testes. Suíte completa: 124, só as 4 falhas conhecidas.
- **Limites conhecidos:** a guarda só cobre `codificacao.json`; um bug que zere o `frame.json` ou o `respostas.json` não é recusado (o frame tem snapshot; respostas não). O throttle de 15 min é por processo. Quem escreve direto no Turso, sem passar por `_gravar`, não é protegido.
- **Não validado com o Turso de verdade**, só com SQLite local (mesmo cliente). Vale uma rodada contra a nuvem antes de confiar.

## Andamento (02/10, Claude Sonnet 5.5)
- **Tela "Restaurar versão" feita:** botão `🕘 Versões` na barra de revisão da pergunta (`abrirJanelaVersoes` em `static/app.js`). Lista as versões da classificação e do quadro (quando, antes de quê, conteúdo) e restaura com confirmação que mostra quantas conferidas se perdem. Usa `GET /versoes` e `POST /restaurar` que já existiam. Suíte completa passa.
- **Backup manual da nuvem rodado** (`python src/nuvem.py -p sesi backup`): `tabulador/projetos/sesi_cat/output/_backup/nuvem_20261002_135625.json`. O backup diário automático não tinha deixado arquivo novo em `SESI_cat/output/_backup` desde 24/09 (conferir para onde o `backup_se_preciso` grava).
- **Ainda não validado:** snapshot e restauração contra o Turso real (só SQLite local nos testes), e clique na tela em navegador.

## Estado no fim de 02/10
- **O Gabriel disse que vai validar** a tela 🕘 Versões e a restauração (camada 3). Nada a fazer até ele reportar.
- Já feito: guarda de gravação, versões (nuvem e local), backup diário ao abrir o app, tela Versões, backup manual da nuvem em `tabulador/projetos/sesi_cat/output/_backup/nuvem_20261002_135625.json` e `..._141754.json`.
- Ainda não provado: snapshot e restauração contra o **Turso real** (só SQLite local nos testes). O backfill de telemetria (PEND-26) gravou snapshots reais em `blobs_historico` ("telemetria: carimbo estimado do modelo"): dá para usá-los como cobaia da restauração.
- Dúvida aberta: o backup diário automático não deixou arquivo novo em `SESI_cat/output/_backup` desde 24/09; conferir para onde `protecao.backup_se_preciso` grava (provável: `tabulador/projetos/sesi_cat/output/_backup`).
