---
id: PEND-41
titulo: Feedback claro e desambiguação visual ao parar classificação (barra, etapas e cancelamento imediato)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, src/progresso.py, src/coding.py, src/supervisao.py, static/app.js, static/app.css]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Ao clicar em '⏹ Parar', os lotes futuros são cancelados, mas a interface induz à falsa impressão de que 'classificou tudo mas não carregou': a barra salta para 100% com checkmarks verdes ao entrar na etapa de gravação, o tempo restante continua estimando a base total e workers paralelos em andamento emitem logs ambíguos. Correção de UX no modal de progresso e travas de interrupção."
linear: JUM-27
---

# PEND-41: Desambiguação visual e feedback correto ao parar classificação/auditoria

## Contexto & Diagnóstico da Falha de UX
No uso real (ex.: classificação da Q29 em 02/10), ao acionar o botão **"⏹ Parar"**, o usuário relatou a percepção de que *"o botão não está parando, parece que classifica tudo mas não carrega, e as mensagens no log estão ambíguas"*.

A auditoria dos logs e do código revelou que **o backend realmente parou** (apenas 3 de 32 lotes foram executados e gravados, cancelando os demais 29 lotes). Contudo, a interface gráfica produziu uma ilusão de ótica enganosa devido a 4 fatores:

1. **Salto da barra para 100% e checkmark verde falso:**
   - A etapa de IA possui peso 12 e a etapa de gravação peso 1 (total 14).
   - Ao interromper os lotes e avançar para `progresso.etapa("gravar")`, a função `etapa()` marca automaticamente a etapa anterior ("ia") como `estado = "feito"`.
   - Isso faz com que a etapa da IA ganhe um **`✓` verde**, e a barra salte bruscamente de ~9% para 93% e, ao concluir a gravação, para **100%**.
   - Para o usuário, ver a barra em 100% com checks verdes dá a certeza de que a IA processou tudo. Ao retornar à tela da pergunta e ver apenas 90 respostas classificadas (e 860 pendentes), surge a impressão de que "o app classificou tudo mas não carregou".

2. **Estimativa de tempo e contadores não recalculados:**
   - Durante o estado `parando = True`, o modal continuava exibindo `faltam ~X min` (calculado sobre o total original de 32 lotes) e `lote K/32`, competindo contraditoriamente com o aviso `parando a pedido…`.

3. **Workers paralelos em voo emitem logs posteriores ao clique:**
   - As threads já despachadas para o executor (`ThreadPoolExecutor`) levam 10–20 segundos para finalizar o lote atual.
   - Enquanto finalizavam, emitiam mensagens no log como `Lote 2 de 32 concluído · 60 de 950 prontas`, dando a entender que o pedido de parada foi ignorado.

4. **Falta de guarda na função interna do lote (`_um`):**
   - Se uma thread no pool foi alocada mas a chamada de rede ainda não ocorreu, ela não checava `progresso.parada_pedida()` antes de chamar o modelo.

---

## Requisitos de Implementação

### 1. Interrupção Rápida no Backend (`src/coding.py`, `src/supervisao.py`)
- Em `_chamar_lote` (e equivalente na supervisão), a função executada pela thread (`_um`) deve checar `if progresso.parada_pedida(): return None` logo no início, evitando abrir requisições à IA se a parada já foi solicitada.
- No loop de coleta de futures, ao detectar `progresso.parada_pedida()`, chamar cancelamento e interromper a espera de novos lotes de forma limpa.

### 2. Estado "interrompido" no Gerenciador de Progresso (`src/progresso.py`)
- Quando a operação estiver com `parando = True` ou `parado_usuario = True`, a etapa de IA que foi interrompida **não deve** ser promovida a `estado = "feito"`.
- Adicionar estado visual ou flag `interrompida = True` (ex.: classe CSS `.interrompida` ou badge `⏹ Interrompida (3 de 32 lotes)` em tom amarelo/âmbar).
- A barra de progresso (`pct`) deve refletir a proporção real de respostas concluídas no momento da parada, sem saltar artificialmente para 100%.

### 3. Ajuste de Mensagens e UX no Modal (`static/app.js`, `static/app.css`)
- Ao entrar em `parando`:
  - Ocultar imediatamente a estimativa de tempo restante (`faltam ~X min`).
  - Atualizar o subtítulo para: `⏹ Cancelando lotes pendentes e gravando os concluídos…`.
  - No log de eventos, exibir mensagem explícita e inequívoca: `⏹ Operação interrompida: 90 respostas salvas; 860 continuam pendentes.`.
- Ao fechar o modal, manter o toast informativo claro: *"Classificação interrompida a seu pedido. 90 respostas foram salvas e 860 permanecem pendentes."*.

---

## Critérios de Aceite
1. Clicar em "⏹ Parar" interrompe as chamadas imediatamente sem submeter novos lotes.
2. A barra de progresso não salta para 100% nem exibe check verde `✓` na etapa de IA quando a operação for interrompida antes do término.
3. O modal de progresso não exibe estimativas de tempo contraditórias enquanto está em processo de parada.
4. O usuário tem clareza visual instantânea de quantas respostas foram efetivamente salvas e quantas continuam pendentes.
