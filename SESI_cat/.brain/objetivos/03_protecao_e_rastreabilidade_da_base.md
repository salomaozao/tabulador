---
id: OBJ-03
titulo: Base classificada protegida contra perda e rastreável (quem/qual modelo fez o quê, e quando)
area: tabulador
status: ativo
prioridade: alta
data_criacao: 2026-10-01
---

# OBJ-03: Base classificada protegida e rastreável

### 1. Contexto e Dor Atual (JTBD - Problem Space)
- **Cenário / Gatilho:** Várias pessoas (Gabriel, Sara, João) e várias IAs (Claude, Antigravity, o próprio Tabulador) mexem ao mesmo tempo no código e na base de revisão. Com a nuvem ativa, cada gravação substitui a anterior no banco, e apagar na nuvem é definitivo, sem lixeira.
- **A Dor Real:** Um bug ou uma alteração descuidada no código pode apagar ou encolher milhares de respostas já conferidas por humano, e ninguém percebe na hora. Também não dá para responder "qual modelo criou esta categoria?", "quando a definição mudou?" ou "quem conferiu esta resposta?". Sem isso não existe painel de administração nem como comparar modelos.
- **Impacto:** Risco de perder dias de revisão humana perto da entrega e falta de base para decidir sobre modelos, pessoas e quadros.

### 2. Ganhos Esperados (JTBD - Value & Relief)
- **Alívio operacional:** Quando algo der errado, voltar a uma versão anterior leva minutos, sem precisar refazer a revisão.
- **Confiança e previsibilidade:** Gravações que encolhem a base sem motivo são barradas antes de chegar ao banco.
- **Rastreabilidade:** Cada resposta e cada categoria guarda quem fez, com qual modelo, quando e em qual versão do quadro.

### 3. Critérios de Vitória (DoD de Alto Nível)
- [ ] Dá para restaurar a codificação de uma pergunta para qualquer ponto das últimas 72 h, com a nuvem ativa.
- [ ] Um teste que simula uma gravação que zera a codificação é bloqueado e registrado.
- [ ] Para qualquer resposta, aparecem o modelo que classificou, quem conferiu e quando.
- [ ] Para qualquer categoria, aparecem quem criou, com qual modelo e quando a definição mudou.

### 4. Anti-Escopo / No-Gos (Shape Up - Limites Rígidos)
- ❌ **Não** montar o painel de administração antes de a telemetria existir e ter algumas semanas de dados.
- ❌ **Não** trocar o Turso por outro banco nem criar um servidor central.
- ❌ **Não** versionar dados de cliente no git (os snapshots ficam no Turso e em `output/_backup`, que é ignorado pelo git).
- ❌ **Não** criar login com senha. A identificação continua sendo o nome autodeclarado da aba (PEND-09).

### 5. Rabbit Holes (Shape Up - Armadilhas Técnicas Conhecidas)
- ⚠️ **Tamanho do histórico:** `codificacao.json` da Q35 tem milhares de itens. Guardar uma cópia inteira a cada clique de ✓ estoura o banco, então os snapshots precisam ser espaçados ou ter retenção limitada.
- ⚠️ **Backfill de telemetria:** os itens antigos não sabem o modelo. Dá para estimar pelo `llm_log`, mas o resultado precisa ser marcado como estimado, nunca como certo.
- ⚠️ **Escrita concorrente:** a guarda de "não encolher" não pode bloquear o fluxo legítimo de apagar ou reabrir. Para isso existe uma liberação explícita.

### 6. Validação dos Ganhos (Auditoria de Resultados)
- **Ganhos Obtidos vs Esperados:** [Preencher na conclusão].
- **Data de Validação:** Pendente
