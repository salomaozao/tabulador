# IP — Grupos de perguntas: quadro único, aprovação por pergunta, tabela única

Plano de implementação no formato MetaGPT (PM → Arquiteto → Gerente de Projeto → Engenheiro → QA).
Data: 2026-10-02 · Origem: conversa com o Gabriel · Memória: `tabulador-grupos-redesenho`.

**Status (2026-10-02): fases 1 a 4 implementadas e testadas** (commits `a9aa5ac`, `a8c4202`, `ceecabb` e o da fase 4; ponto de retorno: tag `pre-pivot-grupos`).
Desvio do plano: a página do grupo reaproveita `renderFrame`/`renderCodificacao` com uma "pergunta virtual" (rid composto + `_q` de origem) em vez de reescrever a tabela; a supervisão (auditar, aceite automático, revisão por categoria) continua na página de cada pergunta.

---

## 1. Requisitos originais (PM)

Gabriel gerou as categorias de uma pergunta de um grupo (Q32+Q33) e **não sabia se o quadro representava o grupo inteiro**. Pediu:

1. Informar **quantas respostas de cada pergunta** foram lidas para propor as categorias.
2. O botão de gerar categorias, o feedback ("Pedir ajuste à IA") e a saúde do quadro passam a ser **do grupo**.
3. **Uma categoria = um atributo** (nunca duas ideias), inclusive quando a IA ajusta o quadro.
4. **Aprovação continua por pergunta.** O grupo "fecha" quando todas as perguntas estão concluídas.
5. Dentro do grupo, **uma tabela só**, igual à das perguntas, com a coluna extra **"Questão de origem"** — as duas perguntas são categorizadas e revisadas ao mesmo tempo.
6. No Painel geral, as perguntas ficam **agrupadas por grupo**.

## 2. PRD

### 2.1 Metas
- O pesquisador sabe, ao ver o quadro, **de onde vieram as categorias** (cobertura por pergunta).
- Um único caminho de trabalho por grupo: gerar → ajustar → classificar → conferir → aprovar cada pergunta.

### 2.2 Histórias de usuário
- **H1.** Como pesquisador, ao gerar categorias do grupo vejo "Q32: 380 de 380 · Q33: 135 de 135" (ou "amostra de 900 de 3.000") para saber se o quadro é representativo.
- **H2.** Como pesquisador, peço ajuste à IA uma vez e ele vale para o grupo; a IA recusa fundir duas ideias numa categoria e me diz por quê.
- **H3.** Como pesquisador, confiro Q32 e Q33 na mesma tabela, filtro por "Questão de origem" quando quiser, e aprovo cada pergunta separadamente.
- **H4.** Como pesquisador, antes de mudar um quadro já aprovado vejo o impacto ("reabre Q32 — 380 classificadas").
- **H5.** Como pesquisador, no Painel geral vejo o grupo como um cartão (andamento por pergunta, "fechado" quando todas concluídas).

### 2.3 Pool de requisitos
| Pri. | Requisito |
|---|---|
| P0 | Amostra de indução do grupo com repetidas + cota mínima por pergunta; cobertura gravada e exibida |
| P0 | Edição do quadro do grupo (renomear, mesclar, adicionar, remover, palavras-chave, ajuste com IA) |
| P0 | Regra "um atributo por categoria" nos prompts e aviso na tela |
| P0 | Aprovação do quadro por pergunta (sem quebrar as travas de `coding.py`) |
| P1 | Página do grupo com tabela única + coluna "Questão de origem" + filtro |
| P1 | Aviso de impacto antes de alterar quadro já aprovado |
| P1 | Saúde do grupo (diagnóstico por categoria, com divisão por pergunta) |
| P2 | Painel geral: cartão do grupo e perguntas aninhadas na barra lateral |

### 2.4 Fora de escopo
- Quadro próprio por pergunta dentro do grupo (quem precisar sai do grupo na aba Grupos, como hoje).
- Mexer em perguntas sem grupo (continuam como estão).
- Mudar o formato de `codificacao.json` por pergunta.

---

## 3. Desenho do sistema (Arquiteto)

### 3.1 Estado atual relevante (verificado no código)
- `codeframe.frame(qid)` já devolve o quadro do grupo quando a pergunta pertence a um (`grupos_frame.grupo_efetivo`).
- `coding.py` (linhas ~227, 286) só classifica se `frame["status"] == "aprovado"`.
- Em `codeframe.py`, `renomear`, `fundir`, `adicionar`, `remover`, `editar_keywords` e `refinar` **lançam "em breve"** para pergunta em grupo. Esse é o maior buraco.
- `grupos_frame.induzir` faz **sorteio simples** sobre a lista misturada (não prioriza repetidas, sem cota por pergunta) e não grava cobertura.
- `grupos_frame.aprovar(nome)` aprova **uma vez para o grupo todo**.
- A classificação é gravada **por pergunta** (`perguntas/<QID>/codificacao.json`) — fica assim.

### 3.2 Decisões de arquitetura
1. **Sem duplicar código.** As funções de edição de `codeframe.py` passam a operar sobre o "dono" do quadro: `dono = nome do grupo` se a pergunta tem grupo, senão `qid`. Leitura/gravação do quadro por duas funções (`_ler_frame(qid)`, `_gravar_frame(qid, f)`) que roteiam para `grupos_frame` ou para a pasta da pergunta. As mensagens "em breve" e o código fantasma saem.
2. **Remapeamento em todas as perguntas do grupo.** Mesclar/excluir categoria chama `_remapear_codificacao` para **cada** pergunta membro.
3. **Aprovação por pergunta sem mexer em `coding.py`:** o `frame.json` do grupo ganha `"aprovacoes": {"Q32": {"em": "...", "por": "..."}}`. `CF.frame(qid)` de pergunta em grupo devolve o quadro com `status` **calculado para aquela pergunta** (`"aprovado"` se `qid in aprovacoes`, senão `"rascunho"`). As travas existentes continuam valendo.
4. **Fechamento do grupo** = todas as perguntas membro com `codificacao.status == "aprovado"` (campo derivado, não gravado).
5. **Alteração de quadro após aprovação:** o servidor calcula o impacto (por pergunta: nº classificadas/conferidas) e exige `confirmado: true`. Com confirmação, as aprovações **de quadro** continuam, as respostas afetadas são remapeadas, e as conferidas por pessoa que mudarem de categoria ficam sinalizadas (`marcar_respostas_alteradas`, já existente). Gerar do zero **remove** as aprovações.
6. **Um atributo por categoria:** (a) reforço no prompt de indução e de refino; (b) o schema de refino ganha `avisos: string[]` para a IA explicar o que recusou; (c) validação local barata no servidor — nome/definição com " e ", " / ", " ou " ligando temas gera aviso (heurística, nunca bloqueia).
7. **Tabela única:** no front, `state.G` guarda o grupo e as linhas são a concatenação dos payloads de cada pergunta, cada linha com `qid`. Todas as ações da linha (confirmar, corrigir, comentar) continuam indo para `/api/pergunta/<qid>/...` — o back-end da revisão **não muda**.

### 3.3 Amostra de indução do grupo
```
limite = MAX_RESPOSTAS_INDUCAO (1500) ; k = nº de perguntas
se total_único <= limite -> lê tudo (cobertura 100%)
senão:
  1) todas as respostas repetidas (n>1), em ordem de n desc, até limite/2
  2) cota mínima por pergunta: min(n_q, limite // (2*k)) de respostas únicas (Random(0))
  3) completar até o limite com sorteio fixo (Random(0)) do que sobrou
```
Cobertura gravada em `frame.json`:
```json
"cobertura": {"amostra": false, "limite": 1500,
  "perguntas": {"Q32": {"unicas": 380, "lidas": 380}, "Q33": {"unicas": 135, "lidas": 135}}}
```
Função única `_linhas_inducao(dados)` em `codeframe.py` passa a servir pergunta e grupo (o `random.sample` ad hoc de `grupos_frame.induzir` é apagado).

### 3.4 Arquivos
| Arquivo | Mudança |
|---|---|
| `src/codeframe.py` | `_ler_frame/_gravar_frame`; edições roteadas por dono; remapeamento multi-pergunta; `_linhas_inducao` com cota; prompt de refino com regra de atributo e `avisos` |
| `src/grupos_frame.py` | `induzir` usa a amostra nova e grava `cobertura`; `aprovar_pergunta(nome, qid)`; `frame_para(qid)` (status calculado); `fechado(nome)`; `impacto_edicao(nome)` |
| `src/coding.py` | sem mudança prevista (travas leem `CF.frame(qid)`); só teste de regressão |
| `src/report.py` | `status_pergunta` mostra aprovação por pergunta |
| `app.py` | rotas `/api/grupo/<nome>` (payload, induzir, refinar, aprovar/<qid>) e impacto; rotas `/api/pergunta/<qid>/frame/*` seguem funcionando e delegam |
| `static/app.js` / `app.css` / `templates/index.html` | página do grupo (`#grupo/<nome>`), tabela única, cobertura, saúde do grupo, cartão no painel, barra lateral aninhada |
| `tests/test_grupos_frame.py` (+ novos) | ver §5 |
| `docs/AGENTS.md`, `COMO USAR.txt` | descrever o fluxo do grupo |

### 3.5 Fluxo de chamadas (gerar categorias do grupo)
```
UI (#grupo/motivo_troca) → POST /api/grupo/motivo_troca/frame/induzir
  → grupos_frame.induzir → preparar (junta Q32+Q33, origem_qid)
  → CF._linhas_inducao (todas repetidas + cota por pergunta)
  → llm.chamar_json(SCHEMA_FRAME) → frame.json {cobertura, aprovacoes:{}}
  ← payload do grupo + cobertura → UI mostra "Q32: x de y · Q33: x de y"
```

### 3.6 Pontos em aberto (UNCLEAR)
- **Classificar por grupo ou por pergunta?** Proposta: botões "Classificar amostra / restantes" ficam no grupo e rodam as perguntas em sequência; a amostra de classificação inclui as duas. Confirmar com o Gabriel na fase 3.
- **Back-coding** em perguntas de grupo: hoje `frame_fixo` é por pergunta; assumir que pergunta com back-coding não entra em grupo (validar na aba Grupos).

---

## 4. Lista de tarefas (Gerente de Projeto)

Cada fase: implementar → testes → commit cirúrgico (`git add` por arquivo) → só então a seguinte.

### Fase 1 — Motor do grupo
1. `_ler_frame/_gravar_frame` e roteamento por dono em `codeframe.py`; apagar os `raise "em breve"`.
2. Remapeamento de `codificacao.json` em todas as perguntas membro (mesclar/excluir).
3. `_linhas_inducao` com repetidas + cota por pergunta; `grupos_frame.induzir` passa a usá-la; gravar `cobertura`.
4. Prompt de indução/refino com a regra "um atributo"; `avisos` no refino; heurística local de aviso.
5. Rota `/api/grupo/<nome>/frame/...` (induzir, refinar, categoria, fundir, keywords) delegando ao motor.
**Pronto quando:** edições funcionam em Q32/Q33 e a cobertura aparece no JSON.

### Fase 2 — Aprovação por pergunta e fechamento
1. `aprovacoes` no `frame.json`; `grupos_frame.frame_para(qid)` com status calculado; `CF.frame(qid)` usa.
2. `aprovar_pergunta` + rota; `fechado(nome)`; `report.status_pergunta` atualizado.
3. `impacto_edicao` + confirmação nas rotas de edição; "gerar do zero" zera aprovações.
**Pronto quando:** aprovar Q32 libera classificar Q32 e não Q33; editar o quadro mostra impacto.

### Fase 3 — Página do grupo (tabela única)
1. Rota `#grupo/<nome>` e `renderGrupo()`: cabeçalho, cobertura, instruções do grupo, quadro, refino, saúde.
2. Tabela única reaproveitando `renderCodificacao`, com coluna "Questão de origem" e filtro por origem; ações da linha vão para a pergunta dona.
3. Botões "Aprovar categorias" e "Aprovar classificação" **por pergunta**; selo "Grupo fechado".
4. Na página da pergunta de um grupo: tirar os botões de quadro e deixar um link para o grupo.
5. Saúde do grupo (`dossie_consolidado` + `assimetrias`).

### Fase 4 — Painel geral
1. Cartão do grupo (perguntas dentro, andamento somado, "Q32 ✓ · Q33 em revisão").
2. Barra lateral com as perguntas aninhadas sob o grupo; perguntas sem grupo ficam como estão.

---

## 5. QA — critérios de aceite e testes

- **Cobertura:** grupo com 515 únicas lê 100%; grupo sintético com 3.000 únicas respeita o limite, inclui todas as repetidas e dá a cada pergunta ao menos `limite // (2k)` linhas.
- **Edição:** renomear/mesclar/excluir/adicionar/keywords agem no quadro do grupo; mesclar remapeia `codificacao.json` de **todas** as perguntas.
- **Aprovação:** aprovar Q32 não aprova Q33; classificar Q33 sem aprová-la continua bloqueado; `fechado()` só é verdadeiro com as duas classificações aprovadas.
- **Impacto:** editar quadro com classificações pede `confirmado`; gerar do zero limpa `aprovacoes`.
- **Um atributo:** pedido "junte A e B" (atributos distintos) volta com `avisos` e quadro inalterado (teste com LLM simulado).
- **Regressão:** perguntas sem grupo se comportam como antes; `python -m unittest discover -s tests` passa em cada fase.
- **Manual (por fase):** abrir o app no SESI (cópia de teste), gerar categorias do grupo, conferir cobertura, aprovar uma pergunta, ver o cartão no painel.

## 6. Riscos
| Risco | Mitigação |
|---|---|
| `app.js` grande e acoplado à pergunta única (`state.P.qid`) | Tabela do grupo monta linhas com `qid` próprio; fases pequenas; teste manual a cada fase |
| Remapeamento corrompe classificação | `snapshot_antes` + `protecao.verificar` em cada pergunta; teste de conservação (skill `data-conservation-auditor`) |
| Aprovação por pergunta confunde quem já usa o grupo atual | `aprovacoes` ausente em quadro antigo → migrar: se o grupo já está `aprovado`, todas as perguntas membro entram como aprovadas |
| Heurística de "um atributo" gera falso alarme | Só avisa, nunca bloqueia |

## 7. Ordem de entrega e rastreabilidade
Fase 1 → 2 → 3 → 4, uma branch por fase em worktree dedicada (regra do AGENTS.md), um commit por fase, `.brain` e handoff atualizados no fim de cada bloco.
