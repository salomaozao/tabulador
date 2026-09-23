---
id: DEC-02
titulo: Versionamento restrito e dados de cliente fora do git
modulo_afetado: [git, data, output]
data_decisao: 2026-09-22
status: ativo
autor: Gabriel Nascimento / Claude
resumo: "Git na raiz jumppi/ com .gitignore de lista de permissão (só _laterais/categorizador e SESI_cat). Nunca versionar .env, credenciais, SESI_cat/data nem output*; buscar chaves antes de cada commit."
---

# DEC-02: Versionamento restrito e dados de cliente fora do git

## Decisão
- Repositório privado `github.com/salomaozao/jumppi-categorizador`, com raiz na pasta `jumppi/`.
- O `.gitignore` é uma lista de permissão: entram só `_laterais/categorizador/` e `SESI_cat/`.
- Nunca versionar: `.env`, `credentials.json`, `token.json`, `SESI_cat/data/` (planilha com respostas), `output*/`, `llm_log/`.
- Antes de cada commit, buscar chaves de API no diff.
- A tag `v0-base-antes-melhorias` marca a versão anterior às melhorias de usabilidade.
- O modo teste (IA simulada) grava em `<saída>_teste`, separado da entrega.
