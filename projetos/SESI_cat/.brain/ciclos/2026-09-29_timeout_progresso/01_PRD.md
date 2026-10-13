---
id: PRD_2026-09-29_timeout_progresso
ciclo: 2026-09-29_timeout_progresso
data_criacao: 2026-09-29
autor: Antigravity (Gemini 3.8 Flash)
objetivo_relacionado: OBJ-01
status: concluido
---

# PRD: Remoção de Timeout em Requisições com Progresso e Resiliência de IA

## 1. Contexto & Dor de Negócio (Problem Statement)
- **Problema:** Ao tentar reclassificar perguntas volumosas (ex: Q35 com 4.515 respostas únicas e 3.766 pendentes) utilizando o provedor `agy`, a chamada AJAX era abortada pelo navegador após exatamente 35 segundos com erro de timeout no frontend, mesmo enquanto o backend continuava progredindo.
- **Impacto:** O operador não conseguia concluir lotes grandes de classificação/revisão pela interface web.
- **Ganhos Esperados:** Permitir execuções de longa duração em pipelines de lote que reportam progresso, mantendo feedback visual contínuo e eliminando aborts prematuros.

## 2. User Stories & Requisitos Funcionais
- **US-01:** Como operador executando uma recodificação volumosa via UI, quero que o frontend mantenha a requisição aberta enquanto houver progresso reportado, sem timeout artificial de 35s.
- **US-02:** Como operador disparando ações comuns sem polling de progresso, quero que haja um timeout defensivo de até 4 minutos (240s) para evitar travamento infinito caso o servidor pare.

## 3. Requisitos Não-Funcionais
- **Performance:** Nenhuma sobrecarga de memória no navegador durante o polling de progresso.
- **Cache Invalidation:** Nova versão do frontend deve ser automaticamente servida após reinício do processo Flask.

## 4. Anti-Escopo & No-Gos
- 🚫 **No-Go 1:** Não alterar o mecanismo de WebSocket ou polling existente em `/api/progresso`.
- 🚫 **No-Go 2:** Não tocar nos arquivos de dados de produção em `data/`.

## 5. Critérios de Aceite
- [x] Requisições com `progresso = true` não disparam sinal de `AbortController` por tempo decorrido.
- [x] Timeout do cliente OpenAI em `src/llm.py` compatível com o teto de 240s.
- [x] Servidor reiniciado e respondendo na porta 5000 com o hash novo de versão.
