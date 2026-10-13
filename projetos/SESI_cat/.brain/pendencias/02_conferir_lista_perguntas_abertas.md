---
id: PEND-02
titulo: Conferir lista de perguntas abertas (7 no pedido x 8 no projeto.py)
modulo_afetado: [projeto.py]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento / Jucimara
data_abertura: 2026-09-23
data_resolucao: 2026-09-24
resumo: "Na planilha, 7 colunas Q*_CAT estão em amarelo (Q2, Q4, Q5, Q29, Q32, Q33, Q35). A Q30_CAT existe, mas não está em amarelo, e o projeto.py a inclui. Perguntar à Jucimara se a Q30 deve ser categorizada."
---

# PEND-02: Conferir lista de perguntas abertas

## Situação
Na transcrição de 22/09, a Jucimara conta sete perguntas para categorizar, marcadas em amarelo na base. O `projeto.py` configura oito: Q2, Q4, Q5, Q29, Q30, Q32, Q33 e Q35.

## Resolução (24/09)
Gabriel confirmou: a nova contagem (8 perguntas, incluindo a Q30) está correta.

## Verificação (23/09)
Cabeçalhos da aba `base` de `data/base_processamento.xlsx`:
- Em amarelo (FFFF00): Q2_CAT, Q4_CAT, Q5_CAT, Q29_CAT, Q32_CAT, Q33_CAT, Q35_CAT, ou seja, as 7 do pedido.
- A **Q30_CAT** existe, mas está em roxo como as demais colunas. A Q30 é a aberta de quem acha a escola inferior (filtro `inferior`), par da Q29.

## Ação necessária
- Perguntar à Jucimara se a Q30 também deve ser categorizada. A existência da coluna Q30_CAT sugere que a falta do amarelo foi esquecimento.
- Se ela não for pedida, tirar a Q30 do `projeto.py`, ou mantê-la e avisar que é um extra.
