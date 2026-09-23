---
id: PEND-01
titulo: Base parcial - incorporar novas entrevistas até o fim do campo
modulo_afetado: [data, categorizacao]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento / Jucimara
data_abertura: 2026-09-22
resumo: "A base recebida (3.743 respostas, ~70%) não é a final; devem entrar ~500 entrevistas (disparos de e-mail em 22/09 e 24/09) até o fim do campo em 25/09. Recategorizar só as respostas novas mantendo as validadas."
---

# PEND-01: Base parcial - incorporar novas entrevistas

## Situação
- Base atual: 3.743 respondentes, cerca de 70% do total esperado.
- Jucimara vai enviar versões atualizadas conforme as respostas chegarem (disparos de e-mail em 22/09 e 24/09). A estimativa é de mais 20%, cerca de 500 entrevistas.
- O campo termina na sexta-feira, 25/09. O processamento começa na segunda-feira, 28/09.

## Ação necessária
- Ao receber cada nova `base_processamento.xlsx`, trocar o arquivo em `data/` e conferir se o app preserva as categorizações e validações já feitas (casar por `respondent_id`), classificando só as respostas novas.
- Registrar em `dialogo_ias.md` a data e o N de cada versão da base.
