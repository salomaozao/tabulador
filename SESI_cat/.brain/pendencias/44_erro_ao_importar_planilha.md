---
id: PEND-44
titulo: Erros ao importar a planilha (relatado em 02/10, sem o texto do erro)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, src/load.py, src/coding.py, app.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "O Gabriel disse no fim de 02/10 que 'deu uns erros na hora de importar a planilha', sem dizer qual botão nem a mensagem. Não reproduzido: /api/load com a planilha real funciona em modo isolado (5.624 respondentes, 8 s) e a exportação/importação do revisao.xlsx passa nos testes. Antes de mexer no código, PERGUNTAR ao Gabriel: qual botão, qual mensagem, e em qual instância (5000 real ou 5001 de teste)."
---

# PEND-44: Erros ao importar a planilha

- **Candidatos (por ordem de probabilidade):**
  1. **"Ler a planilha agora" / "Recarregar planilha"** (`POST /api/load`, `src/load.py`). Se foi na instância de TESTE (porta 5001, `TABULADOR_OUTPUT` temporário), o ambiente era artificial: a planilha tinha sido copiada para a worktree e, por um clique indevido num botão escondido, a instância entrou em "modo teste" (IA simulada, pasta `*_teste`). Esse estado não existe mais (instância encerrada, `.env` apagado).
  2. **Importar o `revisao.xlsx`** (`coding.importar_revisao`). Havia um bug: a planilha exportada ganhava uma coluna `congelada` com um dicionário em texto. Corrigido em `23907ed`; agora a coluna diz "sim" e a importação ignora a linha congelada e conta `_congeladas_ignoradas`.
  3. **Assistente de projeto novo** (`/api/novo/*`): os testes passam, mas o formato da planilha do usuário pode ser diferente do gabarito.
- **O que já foi verificado:** `POST /api/load` real (modo isolado) = 200, `n=5624`; suíte da main = 192 passam.
- **Próximo passo:** obter o texto do erro. Se for um traceback, ele sai no JSON de erro (`trace`) e na caixa de erro da tela.
