---
id: PEND-06
titulo: Conferir quadros de categorias aprovados pelo Claude (Q32/Q33 unificado, Q35) e a fila de revisão
modulo_afetado: [output/perguntas]
criticidade: alta
status: resolvido
data_resolucao: 2026-09-24
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

## Resolução (24/09, a pedido do Gabriel: "resolva tudo")
A conferência foi feita pelo Claude, com um agente revisor que só leu os dados. As correções entraram pela API do app, que grava na nuvem.
- **Q32/Q33: faltava "Remete a resposta anterior"**, que o projeto.py exige. Ela tinha sido removida em 23/09 (20h50/20h56) depois da aprovação, e por isso o Outros da Q32 estava em 7,3%. A categoria foi recriada como **código 10** nas duas perguntas, que continuam com quadro idêntico.
  - Q32: 15 respostas foram de 97 para 10 (a 183 ficou com secundária 5), a 224 foi de 9 para 97 e a 198 de 97 para 6.
  - Q33: a 57 foi de 97 para 10.
  - As duas perguntas foram reaprovadas.
- **Q35**: entraram as categorias **15 "Inclusão e alunos com necessidades especiais"** (115 e 662 movidas) e **16 "Horário, ensino integral e contraturno"** (9 respostas que estavam em Outros). Também: a 4 foi de 2 para 98, a 1311 de 98 para 2 e a 242 de 98 para 97.
- **Q5**: a 103 e a 794 foram de 97 para 14 ("Elogio geral"), a 1268 ficou 14 com secundária 1, e a 1256 foi de 8 para 98 (a nota não era ponto forte).
- A Q29 e a Q30 (100% classificadas, 924 e 175 confirmadas automaticamente pela supervisão) foram aprovadas.
- A classificação das restantes da Q5 e da Q35 foi disparada. Ver o handoff de 24/09.
- **Sugestão que ficou em aberto**: a categoria 6 da Q32/Q33 mistura mudança de cidade com busca por curso técnico ou escola federal (rids 29, 36, 67, 80, 85, 128, 202, 234, 243) e com a falta de integral ou horário (94, 160, 162, 193, 194). Dá para separar pela janela "Revisar por categoria" se o relatório precisar.
