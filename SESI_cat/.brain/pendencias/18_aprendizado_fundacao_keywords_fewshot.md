---
id: PEND-18
titulo: Aprendizado do quadro, etapa 1 (versão do frame, coluna de palavras-chave, dossiê/saúde e few-shot com a revisão humana)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/aprendizado.py, src/codeframe.py, src/coding.py, src/supervisao.py, static/app.js]
criticidade: alta
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
data_resolucao: 2026-09-30
resumo: "Etapa 1 do OBJ-02: o frame ganhou versão, histórico com antes/depois e uma coluna de palavras-chave (fixas + aprendidas com a revisão, com fixar/descartar). O novo src/aprendizado.py calcula por categoria o dossiê (confusões, auditor, confiança, âncoras humanas, casos-limite) e os alertas de saúde. O prompt da IA e o do auditor passam a levar exemplos conferidos por humano e casos já corrigidos."
---

# PEND-18: Aprendizado do quadro, etapa 1

## O que mudou (tabulador)
- **Frame (`codeframe.py`):**
  - `versao` sobe em toda edição (`_registrar`).
  - `renomear` guarda a definição antes/depois; a ação vira `definir` quando só a definição muda.
  - Categoria ganha `keywords`, `keywords_auto`, `keywords_bloqueadas`, `atualizado_em` e `atualizado_por`.
  - A indução e o refino pedem keywords à IA. O refino preserva o que a revisão ensinou.
  - `editar_keywords()` adiciona, remove (e bloqueia) ou fixa.
- **`src/aprendizado.py`:** cálculo puro.
  - `dossie_de`: volume, matriz `corrigido_de → primaria`, discordância do auditor, confiança, âncoras e casos-limite.
  - `keywords_sugeridas_de`: termos com maior lift nas respostas conferidas.
  - `saude_de`: alertas `outros`, `ampla`, `confusao`, `auditor`, `keyword_compartilhada` e `rara`.
  - `bloco_categorias`: o bloco de categorias do prompt.
  - `aprender()`: grava as keywords aprendidas.
- **Classificação (`coding.py`):**
  - O prompt usa `bloco_categorias` com âncoras **só de humano**; auto-aceitas nunca entram.
  - Cada item grava `frame_versao`.
  - `revisado_por` vem do nome autodeclarado na aba (cabeçalho `X-Tabulador-Usuario`).
  - Antes de classificar ou reclassificar, roda `aprender()` se entraram 25+ revisões humanas novas.
- **Auditor (`supervisao.py`):** recebe o mesmo bloco.
- **Tela:**
  - Coluna "Palavras-chave" na tabela de categorias: chip cheio = fixa; tracejado = aprendida (📌 fixa, × descarta).
  - Caixa "Saúde do quadro" com os alertas e o botão "🧠 Aprender com a revisão agora".
  - Keywords também aparecem nos cards de "Revisar por categoria".
- **API:**
  - `POST /frame/keywords`
  - `GET /aprendizado` (dossiê + alertas + keywords sugeridas)
  - `POST /frame/aprender`
  - payload da pergunta com `saude`
- **CLI:** `run.py frame <QID> keywords <cod> adicionar|remover|fixar ...`, `frame <QID> saude` e `frame <QID> aprender`.
- **Limiares:** em `config.py` (`FEWSHOT_*`, `KEYWORDS_*`, `APRENDIZADO_A_CADA`, `SAUDE_*`), sobrescrevíveis no `projeto.py`.

## Testes
- `tests/test_aprendizado.py`: 17 testes, sem IA e sem planilha.
- **Suíte completa:** 107 testes. As 4 falhas são anteriores a esta mudança (`test_sesi` e `test_novo_projeto` esperam 84 respondentes, mas a base atual tem 135).
- **Fumaça pela API** (pasta temporária, IA falsa): funcionaram `revisado_por` com acento, keywords com autor e versão, alertas no payload, prompt com âncoras e casos-limite, e `frame_versao` 1→2.

## Fica para as próximas etapas
PEND-19 (reescrita automática da descrição), PEND-20 (reauditoria seletiva) e PEND-21 (UI de propostas estruturais + split com prévia).
