---
id: DEC-01
titulo: SESI roda no Categorizador multi-projeto (código em _laterais/categorizador)
modulo_afetado: [projeto.py, categorizador]
data_decisao: 2026-09-22
status: ativo
autor: Gabriel Nascimento / Claude
resumo: "SESI_cat guarda só a definição do projeto (projeto.py, formato plano) e o lançador; todo o código do app fica em _laterais/categorizador, compartilhado com a Assertiva."
---

# DEC-01: SESI roda no Categorizador multi-projeto

## Contexto
O pedido da Jucimara (22/09, ver `../09_22_alinhamento_categorizacao.md`) é categorizar as perguntas abertas da base SESI. O categorizador Flask em `_laterais/categorizador`, que antes atendia só a Assertiva, virou multi-projeto (`projetos.json` + um `projeto.py` por projeto).

## Decisão
- `SESI_cat/projeto.py` define o projeto no formato **plano**: aba `base` (uma linha por respondente), aba `Codebook` (enunciados), id `respondent_id`.
- Perguntas abertas configuradas: Q2, Q4, Q5, Q29, Q30, Q32, Q33, Q35. Os filtros incluem quem respondeu fora do filtro, para nenhuma resposta ser descartada.
- Colunas de PII (`ip_address`, `email_address`, `first_name`, `last_name`) nunca entram na base, nas saídas nem nos prompts.
- Entrega: `output/base_processamento_categorizada.xlsx` (principal em `Q*_CAT`, secundária em `Q*_CAT2`).
- A interface continua em Flask + JS puro; React fica como "todo" futuro.
- Abrir sempre por `Abrir Categorizador.bat`, que fecha versões desatualizadas na porta.
