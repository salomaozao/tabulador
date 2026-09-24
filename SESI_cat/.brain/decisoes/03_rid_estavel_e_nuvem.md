---
id: DEC-03
titulo: Respostas identificadas pelo texto (rid estável) e revisão compartilhada na nuvem
modulo_afetado: [tabulador, codeframe, coding, nuvem, supervisao]
data_decisao: 2026-09-24
status: ativo
autor: Gabriel Nascimento / Claude
resumo: "O rid de cada resposta segue a chave do texto normalizado. Uma base nova preserva classificações e conferências, e as respostas novas ficam para classificar. A revisão (arquivos por pergunta) fica no Turso, compartilhada por todos; testes e modo teste nunca tocam no banco. Aceite automático só com confiança >= 0,85 (ajustável) e auditor (outra IA) concordando."
---

# DEC-03: rid estável, recarga da base e revisão compartilhada na nuvem

## Contexto
- O `rid` era a posição da resposta numa lista ordenada por frequência. Quando a base nova chegasse (PEND-01), as posições mudariam e as classificações, confirmações e auditorias cairiam em respostas erradas, sem aviso nenhum.
- "Recarregar planilha" não relia as perguntas, então os respondentes novos ficavam de fora da classificação.
- O banco Turso do projeto "sesi" tinha só dados falsos, gravados pela suíte de testes. O trabalho real estava só na máquina do Gabriel.

## Decisão
1. **rid estável**: a mesma resposta (chave = texto sem acento, sem caixa e sem pontuação final) mantém o rid, e as respostas novas ganham rids novos.
2. Ao reler a base, `codeframe._conciliar`:
   - grava a chave em cada item;
   - guarda em `removidos` o que saiu da base (nada é apagado);
   - acusa erro se a chave e o rid não baterem;
   - reabre a classificação aprovada que ganhou respostas novas.
   Cada versão da base fica registrada em `output/base/versoes.json`.
3. **Nuvem**: o Turso guarda os arquivos de cada pergunta (respostas, frame, codificação, instruções). Em 24/09 foram subidos os dados reais (32 arquivos, 8 perguntas, conferidos um a um) com `python nuvem.py -p sesi subir --limpar-antes`. O backup do que havia antes está em `output/_backup/nuvem_*.json`. Com `TABULADOR_OUTPUT` definido (testes e validação) ou no modo teste, o app **nunca** usa o banco real.
4. **Supervisão** (PEND-05):
   - O auditor é uma segunda IA escolhida na tela e grava `auditoria`.
   - O aceite automático exige confiança >= 0,85 (limiar ajustável) e o auditor concordando. Grava `validado_por: "auto"`.
   - Confirmação humana grava `validado_por: "humano"`.
   - A confirmação em bloco por categoria nunca inclui respostas em que o auditor discordou.

## Consequências
- Na recarga, respostas iguais a textos já classificados herdam a categoria sozinhas.
- A nuvem é "última gravação vence" por arquivo de pergunta. **Duas pessoas editando a mesma pergunta ao mesmo tempo se sobrescrevem.** Combinar para uma pessoa por pergunta de cada vez.
- A planilha-fonte, `base.json` e os resultados continuam locais. Cada pessoa precisa da planilha pelo OneDrive e de clicar em "Recarregar planilha" uma vez.
