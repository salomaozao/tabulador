---
id: PEND-06
titulo: Conferir quadros de categorias aprovados pelo Claude (Q32/Q33 unificado, Q35) e a fila de revisão
modulo_afetado: [output/perguntas]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-23
resumo: "Na sessão de 23/09 o Claude aprovou quadros sem o pesquisador: Q32 e Q33 com um quadro único de 9 categorias (inclui 'Insatisfação geral' e 'Remete a resposta anterior'; o quadro antigo da Q32 está em output/_backup) e Q35 (14 categorias). Conferir os quadros, revisar as pendentes de cada pergunta e aprovar a codificação para gerar a planilha final."
---

# PEND-06: Conferir quadros aprovados pelo Claude e a fila de revisão

## O que mudou sem o pesquisador
- **Q32 e Q33** ("por que vai trocar de escola"): quadro único, para as duas perguntas poderem ser somadas no relatório.
  O quadro antigo da Q32 (6 categorias, gerado pelo Groq) juntava formatura com motivos externos e não tinha
  "remete a resposta anterior", que o `projeto.py` pede. As 50 classificações antigas foram para
  `output/_backup/Q32_codificacao_frame_antigo.json` (nenhuma tinha sido conferida).
- **Q35**: quadro induzido pelo Claude Code (sonnet) e aprovado (`aprovado_por` no frame.json).
- Backup completo de antes da sessão: `output/_backup/perguntas_20260923_antes_supervisao/`.

## Como revisar
- Interface: as confirmadas automaticamente aparecem como conferidas (fim da tabela). A justificativa das que
  o auditor corrigiu começa com `[revisor claude: ...] IA tinha: ...`.
- Linha de comando: `python supervisor.py -p sesi fila Q5 -n 60`.
- Para desfazer as confirmações automáticas de uma pergunta: `python supervisor.py -p sesi desfazer-auto Q5`.
