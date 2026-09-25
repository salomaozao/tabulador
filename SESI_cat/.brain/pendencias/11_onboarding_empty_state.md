---
id: PEND-11
titulo: Empty state de onboarding para gente nova sem nenhum projeto (avaliado e descartado por ora)
modulo_afetado: [tabulador, src/projetos.py, static/app.js]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-25
data_resolucao: 2026-09-25
resumo: "Perguntei ao conselho de IAs qual a maior fricção pra gente nova abrindo o Tabulador pela primeira vez sem nuvem configurada. Convergiram numa proposta boa (empty state com 2 caminhos: criar projeto local ou conectar nuvem, condicionado ao estado 'seletor de projeto vazio' que a aplicação já calcula). Ao investigar o código antes de implementar, achei um problema na premissa: registro de projetos vazio hoje derruba o app inteiro (StopIteration em projetos.padrao(), chamado na importação de config.py) — não é uma tela vazia alcançável hoje. Além disso, o caso real documentado (PEND-08, João) já tinha projeto registrado; o atrito dele era só de nuvem, já resolvido. Descartei implementar o empty state agora."
---

# PEND-11: Empty state de onboarding (avaliado e descartado)

## Contexto
Rodei o conselho de IAs (transcrição em
`jumppi/_general/conselho/rodadas/20260925_162704_no-tabulador-quando-uma-pessoa-nova-da-equipe-abre-o-app-pel.md`)
perguntando sobre onboarding de gente nova (pesquisadores, não-programadores) numa máquina que nunca
rodou o Tabulador. Convergência em 2 rodadas, boa qualidade de debate:
- Arquiteto propôs um checklist de 3 itens (nuvem, criar projeto, chave de IA); Crítico achou um furo
  real (o checklist some ao criar projeto local, escondendo a etapa de nuvem pra quem devia conectar
  primeiro); Pragmático cortou pra 2 caminhos simples (criar local vs. conectar nuvem), sem chave de IA
  no momento inicial (só cobrar quando for usar IA de verdade); Rubber Duck perguntou sobre o
  "beco sem saída" pós-configuração (volta pro app e nada muda?). Segunda rodada fechou: condicionar ao
  estado "seletor vazio" que já existe (não "sem projeto local"), reaproveitar o booleano de conexão que
  já alimenta o indicador de nuvem pra não mostrar o caminho de nuvem se já está conectado, e um botão
  "Recarregar" pra resolver o beco sem saída.

## Por que não implementei
Investigando `tabulador/src/projetos.py` antes de codar: `padrao()` faz
`os.getenv("TABULADOR_PROJETO") or reg.get("ativo") or next(iter(reg["projetos"]))` — se
`reg["projetos"]` estiver vazio, `next(iter(...))` levanta `StopIteration`. Isso é chamado dentro de
`ativar()`, que `config.py` executa **na importação do módulo** (bottom de `config.py`). Ou seja: hoje,
um `projetos.json` com `"projetos": {}` não mostra tela vazia nenhuma — derruba o processo Flask inteiro
antes mesmo de servir a primeira página. O cenário que o conselho desenhou o empty state para resolver
não é alcançável sem antes tornar `projetos.py`/`config.py` resilientes a registro vazio — uma mudança
bem mais arriscada (toca o bootstrap usado em toda requisição) do que "implementável numa tarde", e que
não tem nenhum caso real reportado pedindo por ela: o único atrito de "gente nova" documentado (PEND-08,
João) já tinha um projeto registrado (veio no clone do GitHub) — o problema dele era só a nuvem não
configurada, e isso já foi resolvido (tooltip acionável, commit `50eec1d`).

## Se isso vier a importar de verdade
Antes de reabrir: (1) confirmar que existe um caso real de time expandindo pra projetos totalmente
novos sem nenhum projeto pré-registrado no `projetos.json` do clone; (2) blindar `projetos.padrao()`/
`ativar()` pra não derrubar o processo com registro vazio (retornar `None` e a UI decidir o que
mostrar) antes de desenhar a tela em si. Aí sim a proposta do conselho (2 caminhos, condicionado ao
booleano de nuvem, botão recarregar) é um bom ponto de partida.
