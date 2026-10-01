---
id: OBJ-02
titulo: Quadro de categorias aprende com a revisão humana (IA erra menos e categoria ruim aparece sozinha)
area: tabulador
status: ativo
prioridade: alta
data_criacao: 2026-09-30
---

# OBJ-02: Quadro de categorias aprende com a revisão humana

### 1. Contexto e Dor Atual (JTBD - Problem Space)
- **Cenário / Gatilho:** Sara, Gabriel e João corrigem e confirmam milhares de respostas por pergunta (Q35 tem ~4,5 mil). A base segue crescendo: o campo reabriu e chegam mais respostas na segunda.
- **A Dor Real:** Cada correção arruma só aquela resposta. O quadro (nome + definição + exemplos da indução) nunca aprende com ela. A IA repete o mesmo erro no próximo lote, e ninguém é avisado quando uma categoria está ampla demais, confusa com outra ou quando Outros esconde uma categoria que falta. A Sara pediu para "separar Qualidade do Ensino" e nada visível aconteceu.
- **Impacto:** Retrabalho de revisão, taxa de auto-aceite baixa e categorias ruins descobertas só no fim, perto da entrega.

### 2. Ganhos Esperados (JTBD - Value & Relief)
- **Alívio operacional:** menos correções repetidas; a próxima leva sai mais certa.
- **Confiança e previsibilidade:** alertas objetivos (confusão X↔Y, ampla demais, rara, Outros saturado, auditor discordando) no lugar de intuição.
- **Rastreabilidade:** toda mudança no quadro tem versão, autor e antes/depois, e cada resposta sabe com qual versão foi classificada.

### 3. Critérios de Vitória (DoD de Alto Nível)
- [ ] `acerto_ia` sobe entre versões do quadro numa pergunta real (ex.: Q35).
- [ ] O % de auto-aceite com auditor concordando aumenta depois do aprendizado.
- [ ] Split/merge/nova categoria sugeridos com evidência e aplicados só com clique humano, com prévia do que muda.

### 4. Anti-Escopo / No-Gos (Shape Up - Limites Rígidos)
- ❌ **Não** mudar nome, código ou quantidade de categorias sem decisão humana. Automático só vale para descrição, keywords e exemplos.
- ❌ **Não** usar resposta aceita automaticamente como exemplo ou keyword (autorreforço).
- ❌ **Não** reclassificar resposta conferida por humano.
- ❌ **Não** usar embeddings ou clustering na v1.
- ❌ **Não** alterar o formato de `base_processamento_categorizada.xlsx`.
- ❌ **Não** fixar limiares do SESI no núcleo: eles ficam em `config.py` ou `projeto.py`.

### 5. Rabbit Holes (Shape Up - Armadilhas Técnicas Conhecidas)
- ⚠️ **Deriva da descrição:** reescritas automáticas sucessivas "engordam" a definição. Pôr teto de tamanho e comparar sempre com a versão aprovada original.
- ⚠️ **Quadro compartilhado** (Q32/Q33): o aprendizado precisa somar os sinais das perguntas irmãs.
- ⚠️ **Custo da reauditoria** em perguntas grandes: filtrar só as categorias afetadas.
- ⚠️ **Tamanho do prompt:** âncoras e casos-limite custam tokens por lote. Os tetos estão em `FEWSHOT_*` no config.

### 6. Validação dos Ganhos (Auditoria de Resultados)
- **Ganhos Obtidos vs Esperados:** [Preencher na conclusão].
- **Data de Validação:** Pendente

Plano completo: `C:\Users\GabrielNascimento\.claude\plans\enumerated-crafting-goblet.md`.
