---
id: PEND-16
titulo: (Ideia futura) Botão "Atualizar o Tabulador" - git pull + reinício, para todos rodarem a mesma versão
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, iniciar.bat, app.py]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
data_resolucao: 2026-10-01
resumo: "Ideia arquivada/concluída: mecanismo documentado para evolução futura de auto-update, sem necessidade de implementação imediata."
---

# PEND-16: Atualizar o Tabulador com um botão

- **Motivação:** o erro de 35s persistiu porque cada máquina roda uma versão diferente do código (PEND-22). Hoje ninguém sabe qual versão está rodando.
- **Esboço:**
  1. `GET /api/versao` passa a devolver também o commit local e se o `origin/main` está à frente (`git fetch` a cada X min).
  2. Aviso na tela "Há uma versão nova (3 mudanças) · Atualizar".
  3. Atualizar = `git pull --ff-only`, `pip install -r requirements.txt` se mudou, reiniciar o servidor e recarregar a página.
- **Travas (decidir antes de fazer):**
  - não atualizar com operação de IA em curso;
  - recusar se houver mudanças locais (`pull --ff-only` falha), mostrando o motivo;
  - atualizar só a partir de commits com os testes passando (tag `estavel` ou branch `release`), nunca a `main` crua;
  - backup da nuvem antes (PEND-24).
- **Anti-escopo:** não virar instalador nem auto-update silencioso. A atualização é sempre por clique, com a lista de mudanças visível.
