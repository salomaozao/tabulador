---
id: PEND-29
titulo: Varrer a base pelas keywords de uma categoria e recategorizar candidatas (ex.: 'Ensino técnico' criada no meio da revisão)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/aprendizado.py, src/coding.py, app.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Cenário: no meio da revisão percebe-se que 'ensino técnico' é muito citado, mas essas respostas já estão em outras categorias. Ao criar ou ajustar uma categoria (ou pelo botão '🔍 Varrer a base' na linha dela), buscar fora dela as respostas que casam com as keywords (sem acento, radical simples), mostrar a prévia (quantas por categoria atual + exemplos) e mandar SÓ essas candidatas para a IA reclassificar com o quadro atual. As não conferidas mudam direto. As conferidas por humano não mudam e ganham uma sugestão '🔎 pode ser <nova categoria>' para alguém decidir."
---

# PEND-29: Varredura por keywords

- **Por que não aplicar a keyword direto:** as keywords são "pista, não regra" (decisão do OBJ-02). Negação e ironia quebram o casamento literal ("não tem curso técnico" ≠ elogio ao ensino técnico). A keyword só **seleciona candidatas**, e quem decide é a IA ou uma pessoa.
- **Fluxo:**
  1. Casar as keywords (fixas + auto) com os textos fora da categoria (`aprendizado` já normaliza para keywords).
  2. Prévia: "87 respostas citam 'técnico': 41 em Qualidade do ensino, 22 em Outros…", com uma amostra.
  3. "Reclassificar as 61 não conferidas": usa o caminho do `coding` com uma lista de rids (o mesmo de "Reclassificar comentadas") e guarda de volume acima de 100 respostas.
  4. Conferidas por humano: marca `sugestao_varredura = {codigo, em, keyword}` e um filtro "sugestão da varredura" na tabela (no padrão do "auditor sugere…", tecla S).
- **Ajustes da revisão do plano (01/10):**
  - **Secundária antes de primária:** quando a resposta cita o tema novo, mas a categoria atual também está certa, a IA deve poder pôr a nova como **secundária** em vez de mover a primária. O prompt da varredura pergunta as duas coisas.
  - **Limite de alcance:** a keyword só pega quem usa aquela palavra. "Curso profissionalizante", "SENAI" e "aprendiz" escapam de "técnico". Medir quanto escapa com 50 respostas sorteadas **sem** a keyword, mandadas à IA na mesma rodada. Se a taxa de achados for relevante, avisar "a varredura por palavra-chave pode estar deixando passar ~N".
  - **Consistência metodológica:** a varredura é um atalho. O correto, quando a estrutura do quadro muda, é que tudo que não foi conferido e tem `frame_versao` anterior seja reavaliado (PEND-20). Na tela, deixar claro que a varredura não substitui isso.
- **Pré-requisito:** todas as categorias com keywords (PEND-19, etapa 0, preenchimento das faltantes).
- **Relação:**
  - é a versão sob demanda da reauditoria seletiva (PEND-20);
  - é o "criar a partir de Outros" da PEND-21, generalizado para qualquer categoria de origem.
