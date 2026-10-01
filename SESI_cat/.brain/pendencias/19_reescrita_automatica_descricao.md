---
id: PEND-19
titulo: Aprendizado do quadro, etapa 2B (IA reescreve definição, inclui/não inclui e keywords a partir do dossiê, com log e desfazer)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/aprendizado.py, src/codeframe.py]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
resumo: "aprendizado.atualizar_descricoes(qid): manda à IA o dossiê só das categorias com sinal (confusão, auditor, 25+ revisões novas). O schema é restrito: só definicao, inclui, nao_inclui e keywords por código existente, sem estrutura. Aplica sozinho, registra antes/depois + evidências (rids) no histórico, avisa na tela e permite reverter para a versão N (desfazer multinível no lugar do frame_anterior.json)."
---

# PEND-19: Reescrita automática da descrição

- **Etapa 0, keywords faltantes (pedido de 01/10, pré-requisito da PEND-29):**
  - os quadros induzidos antes da PEND-18 não têm keywords, e as `keywords_auto` só nascem com 25+ revisões humanas, então várias categorias seguem sem nenhuma;
  - comando "Completar palavras-chave": a IA propõe de 3 a 8 keywords por categoria vazia, a partir da definição, dos exemplos e das respostas conferidas;
  - as keywords entram como sugestão tracejada (fixar ou descartar), nunca como fixas.

- **Gatilho:** junto com o `aprender()` que já existe, antes de classificar, quando há sinal.
- **Guardas:**
  - definição de no máximo 2 frases;
  - `nao_inclui` só pode citar códigos existentes;
  - não mexe nas keywords fixas ou bloqueadas por humano;
  - saída inválida é descartada e registrada.
- **Tela:** "Descrições atualizadas automaticamente (vN → vN+1) · ver mudanças · desfazer".
- **Desfazer multinível:** reconstruir a versão N a partir do histórico. Hoje o histórico já guarda o antes e o depois das definições e das keywords.
- **Antes de fazer:** conferir o rabbit hole de deriva da descrição (OBJ-02 §5).
