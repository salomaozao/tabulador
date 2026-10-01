---
id: PEND-34
titulo: Status "alterada" para respostas confirmadas afetadas por mudancas no quadro (reconferecia humana)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, codeframe, coding, protecao, aprendizado, static/app.js, static/app.css]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
data_resolucao: 2026-10-01
resumo: "Quando uma categoria do codeframe tem sua definicao alterada, e mesclada, removida ou refatorada (via Saude do Quadro ou acao direta), respostas previamente aprovadas/confirmadas por humanos recebem o status 'alterada' com metadados do motivo, data e categoria anterior. Respostas alteradas deixam de figurar como ancoras ou lift de aprendizado e exigem reconferencia na interface ('⚠️ N a reconferir'). A arquitetura foi preparada para receber futuros gatilhos (ex.: mudanca no nome da categoria ou diretrizes gerais)."
---

# PEND-34: Status "alterada" e reconferência de respostas afetadas por mudanças no codeframe

## Contexto & Dor:
Ao aprovar melhorias de definições, mesclagens ou remoções de categorias (seja na aba "Saúde do quadro" ou na edição direta do frame), respostas que já haviam sido confirmadas por pesquisadores humanos corriam o risco de:
1. Ter seu enquadramento semântico alterado sem que a equipe percebesse ou revalidasse.
2. Contaminar o loop de aprendizado ativo (`aprendizado.py`) fornecendo exemplos (few-shot) ou keywords desatualizados com a nova fronteira da categoria.

## O que foi implementado:
1. **Rastreamento e Transição de Status (`src/codeframe.py`):**
   - Função `marcar_respostas_alteradas(qid, codigos=None, motivo="Categoria alterada", rids=None)`: varre a codificação e marca respostas já validadas/conferidas com `alterada=True`, `alterada_motivo`, `alterada_em` e `alterada_de`.
   - Disparado em `renomear()` quando a `definicao` da categoria é alterada.
   - Disparado em `_remapear_codificacao()` em operações de fusão (`fundir`), remoção (`remover`), refino com IA (`refinar`) e desfazimento (`desfazer_refino`).
   - Preparado gancho extensível para futuros gatilhos (ex.: alteração de nome de categoria ou diretrizes de pergunta).

2. **Isolamento no Aprendizado Ativo (`src/aprendizado.py`):**
   - Itens com `alterada=True` são explicitamente ignorados na seleção de poucas amostras (few-shot anchors) e no cálculo de lift de palavras-chave, garantindo pureza de sinal até a reconferência.

3. **Guarda de Integridade e Proteção (`src/protecao.py`):**
   - `conferido_por_humano()` considera itens com `alterada=True`, impedindo que a proteção recuse gravações legítimas ou descarte itens em reconferência.

4. **Ciclo de Vida e Métricas no Backend (`src/coding.py`):**
   - `situacao_revisao(item)` retorna `"alterada"` quando `item.get("alterada")` for verdadeiro.
   - `resumo_revisao(qid)` reporta `n_alteradas` e exclui temporariamente itens alterados de `n_revisadas` até que sejam reconferidos.
   - `atualizar_item()` e `validar()` limpam as flags de `alterada` no momento da confirmação/correção pelo usuário, reincorporando o item como `"confirmada"` ou `"corrigida"`.

5. **Interface de Revisão Ergonômica (`static/app.js` e `static/app.css`):**
   - Botão e alerta de destaque na sticky bar de revisão: `⚠️ N a reconferir`, filtrando instantaneamente a lista de respostas.
   - Botão de atalho em ferramentas de revisão: `⚠️ Reconferir alteradas (N)`.
   - Visual destacado na tabela: classe `tr.alterada` com borda lateral amarela, pílula `⚠️ alterada`, exibição do motivo da mudança abaixo da resposta (`⚠️ Reconferir: Categoria alterada`) e botão direto `Reconferir` com atalho `Enter`.

## Pensamentos Futuros / Extensibilidade:
- Gatilho por mudança de nome de categoria (avaliar impacto e sensibilidade).
- Gatilho por mudança na instrução/enunciado da pergunta ou codebook geral.
- Opção na "Saúde do Quadro" para o usuário escolher se a mudança deve forçar reconferência ou manter as confirmações anteriores.
