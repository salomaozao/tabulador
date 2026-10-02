---
id: PEND-26
titulo: Telemetria - qual modelo classificou cada resposta, quem e quando criou/alterou cada categoria, quem revisou o quê
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, src/coding.py, src/codeframe.py, src/supervisao.py, src/nuvem.py]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Hoje cada item tem origem, frame_versao e revisado_por; o 'modelo' fica só no topo do codificacao.json (sobrescrito a cada rodada); o histórico do frame tem quando/acao/versao, mas não quem nem o modelo. Ação: carimbar em cada item classificado_por (provedor:modelo) e classificado_em, revisado_em; nas categorias, criada_por/criada_em/criada_com (modelo ou pessoa) e a autoria em cada entrada do histórico do frame; mais um log de eventos append-only (quem, quando, ação, rid/código, de→para, modelo, frame_versao), base do painel de administração (PEND-27)."
---

# PEND-26: Telemetria

- **Por resposta (`codificacao.json` → itens):**
  - `classificado_por`, `classificado_em` (em `coding.py`, no `novo = {...}`, onde hoje já entra `frame_versao`);
  - `revisado_em` junto de `revisado_por` (`_quem`);
  - a auditoria já tem `por`/`em`.
- **Por categoria (`frame.json`):**
  - `criada_por` (nome da pessoa ou `ia:<provedor>:<modelo>`), `criada_em`, `alterada_em`;
  - cada entrada do `historico` ganha `por` e `modelo` quando houver.
- **Log de eventos:**
  - tabela `eventos` no Turso, append-only, com `(projeto, qid, quando, quem, acao, alvo, de, para, modelo, frame_versao)`; no modo local, `output/eventos.jsonl`;
  - é ela que responde "quem revisou qual categoria".
- **Backfill:**
  - itens antigos recebem `classificado_por` estimado a partir de `output/llm_log` (lote → modelo), com `classificado_por_estimado: true`;
  - o que não der para estimar fica `desconhecido`.
- **Reprodutibilidade da entrega (revisão do plano, 01/10):**
  - toda geração de `base_processamento_categorizada.xlsx` registra, por pergunta, a `frame_versao` e o commit do código num arquivo ao lado (ex.: `entrega_manifesto.json`);
  - o formato do xlsx não muda (anti-escopo do OBJ-02);
  - assim dá para responder "com qual quadro saiu a entrega de 02/10?".
- **Não fazer aqui:** o painel (PEND-27). Esta pendência só registra.
- **Também alimenta:** a medição de `acerto_ia` por modelo e por `frame_versao` (OBJ-02 §3) e a avaliação de mixture of agents (PEND-30).

## Andamento (02/10, Claude Sonnet 5.5)
- **Por resposta:** `classificado_por` (`provedor:modelo`) e `classificado_em` em toda classificação nova (`coding.py`); `revisado_em` agora também na confirmação (✓), não só na correção.
- **Por categoria:** `criada_por` (`humano:<nome>` ou `ia:<provedor>:<modelo>`), `criada_em` e `criada_com` (induzir, adicionar, categorias novas do ajuste com IA). `atualizado_por/em` já existiam e passam a usar o nome da aba. Cada entrada de `frame.historico` ganhou `por` (e `modelo` quando a IA participou).
- **Log de eventos:** `src/eventos.py`, tabela `eventos` no Turso (criada sozinha) ou `output/eventos.jsonl`. Registra classificar, reclassificar, corrigir (de→para), confirmar (e em bloco), auditar (com o modelo do auditor), aceitar/desfazer automático, aprovar, restaurar versão, gerar planilha e todas as ações do quadro (`quadro:*`). O nome vem do cabeçalho da aba (`before_request` em `app.py`).
- **Manifesto da entrega:** `exportar.gerar` acrescenta uma entrada em `entrega_manifesto.json` (ao lado da planilha): data, commit do código (e se havia código não commitado), e por pergunta `frame_versao`, nº de respostas, conferidas por pessoa, aceitas automaticamente e modelos que classificaram. O formato do xlsx não mudou.
- **Backfill:** `python src/telemetria_backfill.py -p sesi [--aplicar]`. Só carimba quando o `llm_log` traz o mesmo rid com a mesma categoria, confiança e justificativa; marca `classificado_por_estimado: true`. Simulação no SESI (02/10): ~5.800 de ~7.300 respostas casam; o resto fica "desconhecido". **Ainda não aplicado** na base real (nuvem): aguarda o OK do Gabriel.
- **Testes:** `test_supervisao.py` (test_9, 10, 11). Suíte: 179 passam.
- **Fica para a PEND-27:** painel e tela para ler os eventos; guardar o resumo de cada auditoria no `historico` da pergunta (PEND-23).

## Backfill aplicado na base real (02/10, ~14:20)
- Backup da nuvem antes: `tabulador/projetos/sesi_cat/output/_backup/nuvem_20261002_141754.json` (mais o snapshot por pergunta que o próprio backfill guarda em `blobs_historico`).
- Aplicado em **Q2, Q4, Q5, Q29, Q30, Q32, Q33** (projeto `sesi`), uma pergunta por vez, conferindo depois de cada uma: mesmos rids, nenhum campo alterado além dos 3 novos, conferidas por pessoa e status iguais. Carimbadas: Q2 19, Q4 646, Q5 1.882, Q29 1.301, Q30 268, Q32 312, Q33 119.
- **Q35 NÃO aplicada:** a Sara estava revisando nela na hora (presença), e escrever a pergunta inteira ao mesmo tempo pode apagar os ✓ dela (PEND-31). Aplicar quando ninguém estiver em Q35: `python src/telemetria_backfill.py -p sesi Q35 --aplicar` (simulação: 1.244 casam).
- O projeto `sesi_categorias_novas` não foi tocado.
- **A PEND-26 fica `aberta` para a finalização** (decisão do Gabriel: guardar para depois).
