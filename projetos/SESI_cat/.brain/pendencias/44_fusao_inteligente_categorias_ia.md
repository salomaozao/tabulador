---
id: PEND-44
titulo: Fusão inteligente de categorias com sugestão de IA e status alterada em mudanças de escopo
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, codeframe, coding, templates/index.html, static/app.js, static/app.css]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
data_resolucao: 2026-10-02
resumo: "Ao mesclar/fundir categorias, a IA agora sugere automaticamente o nome da nova categoria (como placeholder no input, assumido se o usuário confirmar sem digitar), além de definição sintetizada e palavras-chave combinadas editáveis. Simultaneamente, garante que qualquer separação/refino pela IA, renomeação ou redefinição de categoria marque todas as respostas afetadas com status 'alterada' para reconferência humana obrigatória."
---

# PEND-44: Fusão inteligente de categorias com sugestão de IA e status "alterada"

## Contexto & Dor:
1. **Separação pela IA:** Ao pedir à IA para separar categorias (ex.: *"separe metodologia e qualidade de ensino"*), a IA criava uma categoria nova e renomeava a categoria original mantendo seu código. As respostas que antes pertenciam à categoria mista não eram marcadas para reconferência, mantendo a codificação antiga sem alerta visual ao pesquisador.
2. **Mesclagem cega:** Ao juntar duas categorias, o sistema disparava apenas um `confirm()` nativo no navegador; a categoria de destino mantinha seu nome e definição antigos de forma engessada, sem permitir ao usuário definir um novo nome unificado, nova definição ou revisar palavras-chave.

## O que foi implementado:
1. **Gatilhos Abrangentes de Status "alterada" (`src/codeframe.py`):**
   - Em `refinar()`: qualquer categoria existente que tenha sofrido alteração de nome, de definição ou que tenha incorporado categorias fundidas passa a disparar `marcar_respostas_alteradas()` em todos os membros do quadro.
   - Em `renomear()`: ativada a marcação de `"alterada"` caso o nome da categoria mude (mesmo sem alteração de definição), alertando o pesquisador imediatamente na barra de revisão (`⚠️ N a reconferir`).
   - Em `fundir()`: além de remapear as origens (com `alterada_motivo` específico de mesclagem e `alterada_de`), as respostas já existentes na categoria destino também ganham status `"alterada"` com motivo explicativo caso o escopo do destino tenha sido redefinido.
   - `marcar_respostas_alteradas()` preserva motivos específicos prévios (como o remapeamento de origem) com o parâmetro `sobrescrever=False`.

2. **Sugestão Assistida por IA (`src/codeframe.py` e `app.py`):**
   - Novo schema e função `sugerir_fusao(qid, destino, *origens)`: aciona a IA (`llm.chamar_json`) com as categorias envolvidas e devolve `nome_sugerido`, `definicao_sugerida`, `keywords_sugeridas` e justificativa (com fallback determinístico se indisponível).
   - Nova rota `POST /api/pergunta/<qid>/frame/sugerir-fusao`.
   - Atualizada rota `POST /api/pergunta/<qid>/frame/fundir` para receber `novo_nome`, `nova_definicao`, `novas_keywords` e `por` (telemetria PEND-26).

3. **Novo Modal de Fusão no Frontend (`templates/index.html`, `static/app.js`, `static/app.css`):**
   - Diálogo dedicado `<dialog id="dlg-fusao">` disparado em todas as ações de mesclagem (cards de categorias, tabela do frame e janela de Saúde do Quadro).
   - O input de nome vem com a sugestão da IA no `placeholder`. Se o usuário apenas clicar em "Confirmar mesclagem" sem mexer no input, o valor sugerido é adotado por padrão.
   - Definição sintetizada e palavras-chave vêm pré-preenchidas e editáveis.

4. **Testes Unitários:**
   - Adicionados 5 testes em `tests/test_alterada.py` cobrindo renomeação de nome, fusão com metadados e status de destino, refino da IA gerando `alterada` e rotas HTTP da API.
   - Suíte de 185 testes aprovada com 100% de sucesso.
