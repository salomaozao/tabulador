---
id: PEND-12
titulo: Cache curto de leitura na nuvem (troca de aba mais rápida) + distribuição de status sempre visível
modulo_afetado: [tabulador, src/nuvem.py, static/app.js]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-25
data_resolucao: 2026-09-25
resumo: "Dois pedidos diretos do Gabriel: (1) ver a distribuição de status das perguntas (conferidas manual, auditadas/confirmadas por IA, etc.) depois de concluída; (2) trocar de aba/pergunta mais rápido. Investigando o código: com a nuvem ativa, cada arquivo lido (respostas/frame/codificacao.json) é uma chamada de rede ao Turso, e abrir 1 pergunta já fazia 6 chamadas pra só 3 arquivos (cada um lido duas vezes por redundância em codeframe.py/coding.py). Corrigido com cache curto (TTL 5s, write-through). A distribuição de status só aparecia durante a revisão e sumia ao aprovar — extraída pra um bloco sempre visível, e replicada como resumo por card no painel geral."
---

# PEND-12: Cache de leitura na nuvem + distribuição de status persistente

## Pedido original (2026-09-25)
> "queremos que dê pra ver após conclusão a distribuição dos status das perguntas (conferidas /
> auditadas por IA, manual, etc...)"
> "Queremos também deixar mais rápido a mudança entre abas"

## Investigação: por que a troca de aba/pergunta é lenta
`codeframe._ler(qid, nome)` — usado por praticamente tudo (frame, respostas, codificação) — quando a
nuvem está ativa, faz `nuvem.ler()`, que é uma consulta HTTP ao Turso, não uma leitura de disco. Sem
nenhum cache, cada chamada a `CF.frame(qid)`, `CD.codificacao(qid)`, `CF._ler(qid,"respostas.json")` é
uma ida e volta de rede — e pior: `CD.tabela(qid)` (chamado por `_payload_pergunta` em `/api/pergunta/<qid>`
e por `report.status_pergunta`) chama de novo `CF.respostas`, `CF._exigir_frame` e `codificacao`, que
**releem os mesmos 3 arquivos pela segunda vez**. Resultado: abrir uma única pergunta fazia 6 chamadas
de rede pra só 3 arquivos distintos; o painel geral (`/api/status`, que chama `status_pergunta` pra
todas as 8 perguntas) multiplicava isso por 8.

## Solução
Cache em `nuvem.py` (`_cache`, chave `(projeto, qid, arquivo)`, TTL de 5 segundos):
- `ler()`/`existe()` consultam o cache antes de ir à rede.
- `gravar()`/`remover()` atualizam o cache na hora (write-through) — as próprias mudanças de quem está
  usando nunca ficam desatualizadas; só a leitura de mudança feita por **outro processo** pode esperar
  até 5s, prazo comparável ao heartbeat de presença (12s) que a interface já usa.
- Testado: chamadas repetidas dentro do TTL não vão à rede (`test_ler_repetido_nao_bate_de_novo_na_rede`);
  gravação sempre atualiza o cache (`test_gravar_atualiza_cache_na_hora_write_through`); cache expirado
  vai à rede de novo (`test_cache_expira_depois_do_ttl`).

## Distribuição de status
O resumo (`Revisão: X de Y conferidas · ✓ N confirmadas por pessoas · ⚡ N automáticas · ✎ N corrigidas
· a IA acertou N%`) só era renderizado dentro de `renderAcoesCod()`, que só roda **antes** de aprovar
(`frameOk && !codOk`). Extraído pra `renderRevbar()`, chamada sempre que existe codificação — continua
visível depois de aprovada, que é justamente quando o pedido dizia "após conclusão". O painel geral
(visão de todas as perguntas) ganhou a mesma quebra (manual/automáticas/corrigidas) como uma linha
compacta em cada card, em vez de só "revisadas por você" sem detalhar como.

## Não fiz (fora de escopo por ora)
Não toquei a granularidade do cache nem virou um mecanismo de invalidação em tempo real (ex.: avisar a
aba aberta quando outra pessoa grava) — 5s de TTL já cobre a maior parte da lentidão relatada (releituras
redundantes dentro da mesma navegação) sem mexer no modelo de consistência da nuvem.
