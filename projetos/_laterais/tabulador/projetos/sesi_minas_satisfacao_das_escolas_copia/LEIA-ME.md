# SESI Minas — categorização das perguntas abertas

**Para usar:** dê dois cliques em `Abrir Tabulador.bat`. O navegador abre sozinho no projeto SESI.
Na primeira vez: instala o que precisa (1–3 min) e pede a chave da OpenAI (botão **⚙ Configurar IA**).

- `data/base_processamento.xlsx` — planilha-fonte (não é alterada)
- `projeto.py` — configuração do projeto: perguntas abertas (Q2, Q4, Q5, Q29, Q30, Q32, Q33, Q35),
  instruções fixas para a IA, filtros e banners dos cruzamentos
- `output/` — tudo que o programa gera; a entrega principal é
  `output/base_processamento_categorizada.xlsx` (colunas `Q*_CAT` preenchidas, secundária em `Q*_CAT2`)

O passo a passo do loop de validação está no próprio programa (barra lateral) e em
`tabulador/README.md`.
