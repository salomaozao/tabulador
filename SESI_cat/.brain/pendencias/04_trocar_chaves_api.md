---
id: PEND-04
titulo: Trocar chaves de API expostas (Gemini)
modulo_afetado: [categorizador, .env]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-23
resumo: "A GEMINI_API_KEY da variável de ambiente (AIza…oWW8) foi bloqueada pelo Google como vazada. A chave do .env do categorizador (AQ.A…QgzA) funciona, mas apareceu completa numa saída de comando. Gerar chave nova, trocar no ⚙ Configurar IA e apagar a variável antiga."
---

# PEND-04: Trocar chaves de API expostas

## Situação
- A variável de ambiente do Windows `GEMINI_API_KEY` (`AIza…oWW8`) é recusada pelo Google: *"Your API key was reported as leaked"* (403).
- A chave do Gemini no `_laterais/categorizador/.env` (`AQ.A…QgzA`) funciona, mas apareceu completa na saída de um comando numa sessão do Claude Code em 23/09.

## Ação
1. No Google AI Studio, revogar as duas chaves e gerar uma nova.
2. Colar a nova em ⚙ Configurar IA → Google Gemini e clicar em **Testar conexão**.
3. Apagar a variável de usuário `GEMINI_API_KEY` ou trocar o valor dela.
