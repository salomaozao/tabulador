# IP — Criação e Configuração de Grupos com Assistência de IA

Plano de implementação no formato MetaGPT (PM → Arquiteto → Gerente de Projeto → Engenheiro → QA).  
Data: 2026-10-02 · Origem: alinhamento com o Gabriel · Status: **Planejado (Pronto para Execução)**.

---

## 1. Requisitos Originais (PM)

Gabriel definiu a evolução na criação de grupos de perguntas no Tabulador:
1. **A decisão de agrupamento é humana:** Não queremos que a IA fique sugerindo pares de perguntas às cegas com base puramente em cruzamento de bases estatísticas (`grupos_frame.sugerir`).
2. **Aumentar o input cognitivo da IA na configuração do grupo:** Quando o pesquisador decide criar um grupo e marca 2 ou mais perguntas, a IA deve entrar com força analítica para preencher e estruturar os detalhes do grupo:
   - **Nome / Rótulo do grupo**: conciso, substantivo e representativo do tema compartilhado (sem junções mecânicas como "Q32 / Q33").
   - **Descrição e contexto**: explicar o que unifica as perguntas e onde as bases dos respondentes diferem (ex.: motivos de cancelamento vs. motivos de não adesão).
   - **Instruções robustas para a IA (`instrucoes_frame`)**: diretrizes metodológicas para a indução do codeframe compartilhado (escopo temático, neutralidade, regra de 1 atributo por código, desambiguação).
   - **Análise semântica de compatibilidade**: apontar se há divergências de polaridade, granularidade ou escopo entre as perguntas que exijam atenção humana.

---

## 2. PRD (Product Requirements Document)

### 2.1 Metas
- **Zero esforço braçal de redação:** O pesquisador só escolhe as perguntas; a IA propõe os metadados e as instruções do quadro com qualidade executiva.
- **Quadros compartilhados mais consistentes:** Instruções de indução (`instrucoes_frame`) geradas com conhecimento das respostas reais de ambas as perguntas, prevenindo quadros assimétricos ou enviesados para uma só base.
- **Eliminação de ruído:** Remoção do card de "Sugestões de grupos" baseado em sobreposição estatística disjunta.

### 2.2 Histórias de Usuário
- **H1.** Como pesquisador, ao selecionar Q32 e Q33 na tela de novo grupo e clicar em *"✨ Analisar e preencher com IA"*, recebo em segundos um nome profissional (ex.: *"Motivos de evasão e cancelamento"*), uma descrição do escopo e instruções detalhadas para a montagem das categorias.
- **H2.** Como pesquisador, caso eu tente agrupar perguntas com polaridades opostas (ex.: *"O que você mais gostou"* + *"O que você menos gostou"*), a IA me alerta sobre o risco semântico e sugere como modular as instruções para o quadro não misturar atributos positivos e negativos no mesmo código.
- **H3.** Como pesquisador, posso editar livremente qualquer sugestão preenchida pela IA antes de salvar o grupo.
- **H4.** Como pesquisador em um grupo já existente, posso clicar em *"✨ Reavaliar detalhes com IA"* para atualizar o nome ou as instruções com base nas perguntas atualmente associadas.

### 2.3 Pool de Requisitos
| Pri. | Requisito | Detalhe |
|---|---|---|
| **P0** | Endpoint `POST /api/grupos/analisar-ia` | Recebe lista de QIDs, lê enunciados e micro-amostra de respostas, chama LLM com schema estrito. |
| **P0** | Remoção da sugestão cega | Retirar o bloco `sugestoes` da interface e aposentar `grupos_frame.sugerir()` na UI. |
| **P0** | Ação na tela (UX) | Botão `✨ Analisar com IA` no card de Novo Grupo e Grupo Existente com loading state e preenchimento nos inputs. |
| **P0** | Prompt estruturado de taxonomia | Instruir a IA a respeitar a regra "uma categoria = um atributo" e foco em rótulos neutros. |
| **P1** | Card de Compatibilidade Semântica | Aviso visual no card com observações e grau de coerência semântica das perguntas agrupadas. |
| **P1** | Campo `descricao` no grupo | Persistir `descricao` em `grupos` (`projeto.json`/`grupos.json`) para enriquecer codebook e documentação. |

### 2.4 Fora de Escopo
- Alterar o motor de indução do quadro (isso pertence ao `IP_grupos_de_perguntas.md`).
- Forçar o usuário a aceitar as sugestões da IA (todos os campos continuam 100% editáveis).

---

## 3. Desenho do Sistema (Arquiteto)

### 3.1 Coleta de Insumos para a IA
Para a IA gerar boas instruções e rótulos, ela precisa de dados reais, não apenas do código da pergunta:
1. **Metadados:**
   - Rótulo e enunciado de cada pergunta (`V.por_id(qid)["rotulo"]`).
   - Universo/filtro e contexto geral do projeto (`V.contexto()`).
2. **Micro-amostra representativa:**
   - 10 a 15 respostas únicas mais frequentes de cada pergunta (lidas via `CF.preparar(qid)["respostas"]`).
   - Isso permite que a IA "veja" o vocabulário real que os respondentes usaram em cada perna do grupo.

### 3.2 Novo Endpoint: `POST /api/grupos/analisar-ia`

```
UI (#grupos) → POST /api/grupos/analisar-ia
  Body: { perguntas: ["Q32", "Q33"] }
  Backend:
    1. Valida se há ao menos 2 perguntas abertas válidas.
    2. Extrai rótulos e micro-amostras de respostas.
    3. Chama llm.chamar_json(system, user, SCHEMA_ANALISE_GRUPO, nome="analise_grupo")
    4. Retorna { ok: true, rotulo, descricao, instrucoes_frame, compatibilidade }
```

### 3.3 Schema JSON da LLM
```python
SCHEMA_ANALISE_GRUPO = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rotulo", "descricao", "instrucoes_frame", "compatibilidade"],
    "properties": {
        "rotulo": {
            "type": "string",
            "description": "Nome curto e profissional do grupo (máximo 60 caracteres). Substantivo, sem siglas ou códigos Q."
        },
        "descricao": {
            "type": "string",
            "description": "1 ou 2 frases resumindo o construto em comum e os públicos de cada pergunta."
        },
        "instrucoes_frame": {
            "type": "string",
            "description": "Diretrizes metodológicas estruturadas para a indução do codeframe compartilhado."
        },
        "compatibilidade": {
            "type": "object",
            "additionalProperties": False,
            "required": ["grau", "observacoes"],
            "properties": {
                "grau": {"type": "string", "enum": ["alto", "medio", "baixo"]},
                "observacoes": {"type": "string", "description": "Pontos de atenção semântica, polaridade ou escopo entre as perguntas."}
            }
        }
    }
}
```

### 3.4 Prompt de Metodologia e Taxonomia
- **System Prompt:**
  > "Você é um metodologista sênior de pesquisa de opinião e engenheiro de taxonomia. Seu papel é estruturar a unificação de perguntas abertas que compartilharão o mesmo quadro de categorias (codeframe).
  > Diretrizes essenciais:
  > 1. Regra de ouro: uma categoria deve representar exatamente UM atributo conceitual (nunca fundir temas distintos).
  > 2. Rótulo: crie um nome executivo claro, sem incluir 'Q32' ou pontuações mecânicas.
  > 3. Instruções: oriente objetivamente que tipo de categorias buscar, vocabulário a consolidar e como evitar categorias ambíguas.
  > 4. Compatibilidade: avalie se as perguntas têm a mesma polaridade e nível de detalhamento."

- **User Prompt:**
  Apresenta o contexto do projeto, os enunciados de cada pergunta participante e a micro-amostra de respostas reais tabuladas.

### 3.5 Mudanças na Interface (`static/app.js` e `templates/index.html`)
1. **Remoção da seção `sugestoes`:**
   - Apagar o bloco visual de pares de sugestões estatísticas no topo da aba Grupos.
2. **Card de Grupo (`cardGrupo`):**
   - Inclusão do botão `✨ Preencher detalhes com IA` ao lado do título ou logo acima dos campos de texto.
   - O botão fica desabilitado se menos de 2 checkboxes estiverem marcadas.
   - Ao clicar: feedback visual *"Analisando perguntas com IA..."*.
   - Ao receber a resposta: preenche os campos `gr-rotulo` e `gr-instr`, além de renderizar o box informativo de compatibilidade.

---

## 4. Plano de Tarefas (Gerente de Projeto)

> [!IMPORTANT]
> **Coordenação com a outra IA:**
> Atualmente a branch `feat/grupos-fase1` está sendo trabalhada por outro agente para o motor de indução e aprovações.
> Esta feature de IA para criação de grupos deve ser implementada em **worktree isolada** (`worktrees/tabulador-grupos-ia-input` na branch `feat/grupos-ia-input`) após ou em paralelo sem tocar nos mesmos arquivos de motor de classificação.

### Fase 1 — Back-end e Amostragem (`src/grupos_frame.py` & `app.py`)
1. Implementar função `grupos_frame.analisar_com_ia(qids: list[str]) -> dict`.
2. Extração de micro-amostra segura de respostas reais via `codeframe.preparar`.
3. Rota `POST /api/grupos/analisar-ia` em `app.py`.
4. Teste unitário com mock de LLM testando geração de rotulo, instrucoes e compatibilidade.

### Fase 2 — Front-end e UX (`static/app.js` e `static/app.css`)
1. Remover a renderização da seção `.gr-sugs` (sugestões estatísticas cegas).
2. Adicionar o botão `✨ Analisar com IA` no formulário de criação/edição.
3. Tratamento de loading, erro e preenchimento suave dos campos.
4. Adicionar display para o feedback de compatibilidade semântica.

### Fase 3 — Persistência e Documentação
1. Suportar campo opcional `descricao` no dicionário de grupos em `projeto.json`.
2. Atualizar documentação em `docs/AGENTS.md` e `docs/COMO USAR.txt`.

---

## 5. Critérios de Aceite (QA)

1. **Seleção mínima:** Clicar em *"Analisar com IA"* com menos de 2 perguntas marcadas exibe aviso amigável e não faz chamada de rede.
2. **Qualidade do Rótulo:** Para Q32 e Q33 do SESI (motivo de troca / cancelamento), a IA devolve um nome substantivo em português, sem termos técnicos internos.
3. **Qualidade das Instruções:** O campo `instrucoes_frame` gerado contém orientações claras sobre os atributos a serem codificados e alerta sobre unicidade de ideias.
4. **Sem sugestão cega:** A aba Grupos carrega direto os grupos do projeto e o formulário de novo grupo, sem sugestões não solicitadas.
5. **Liberdade total do usuário:** O usuário pode alterar qualquer caractere sugerido pela IA antes de salvar.
6. **Regressão:** A suíte de testes `python -m unittest discover -s tests -v` continua passando integralmente.
