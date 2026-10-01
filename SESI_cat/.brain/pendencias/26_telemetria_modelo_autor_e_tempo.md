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
