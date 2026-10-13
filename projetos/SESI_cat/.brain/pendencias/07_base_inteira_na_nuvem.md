---
id: PEND-07
titulo: Avaliar guardar a base inteira (não só a revisão) na nuvem, para rodar só o Tabulador sem pasta de projeto local
modulo_afetado: [tabulador, nuvem.py, projeto.py, load.py]
criticidade: baixa
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-09-24
data_resolucao: 2026-09-25
resumo: "Ideia do Gabriel: subir também a base (planilha-fonte/base processada), não só o loop de revisão, para o Turso — assim bastaria rodar o `tabulador` (a pasta `SESI_cat` poderia até ficar dentro dele) sem precisar sincronizar outra pasta de projeto. Avaliada pelo conselho de IAs em 25/09: descartada (over-engineering, risco de dado defasado silencioso e gargalo de upload); o problema real que motivou a ideia (PEND-08) já foi endereçado tornando o aviso de nuvem não configurada acionável."
---

# PEND-07: Base inteira na nuvem (não só a revisão)

## Contexto
Hoje (ver `tabulador/docs/nuvem_turso.md`) o Turso guarda só o que é editado por pessoas: os JSON de
`output/perguntas/<pergunta>/` (respostas, frame, codificação, instruções). O que fica de fora, sempre
local, é: a planilha-fonte (`SESI_cat/data/*.xlsx`), `output/base/` e os resultados (planilha final,
codebook, cruzamentos). O `projeto.py` (definição do projeto: `FONTE_XLSX`, filtros de base, rótulos,
`CONTEXTO_PROJETO`, instruções fixas para a IA) também é código local, versionado no git junto do
`SESI_cat/`, mas fora do `tabulador/`.

Em 2026-09-24 (sessão sobre o João não estar sincronizado — ver PEND-08) o Gabriel propôs: e se a base
inteira também fosse pra nuvem? Assim uma pessoa nova só precisaria rodar o `tabulador`, sem precisar de
outra pasta de projeto (`SESI_cat`) sincronizada à parte — ela poderia até morar dentro do `tabulador`.

## Tradeoffs a avaliar antes de decidir
- **`projeto.py` da SESI usa filtros em lambda Python** (`FILTROS = {"todos": lambda df: ...}`), não dá
  para virar JSON puro sem antes desenhar uma DSL de filtro (o `projeto.json` do assistente `novo-projeto`
  já é declarativo, mas cobre um caso mais simples). Sem isso, "só a pasta" não é suficiente: ainda sobra
  código Python específico do projeto rodando fora do banco.
- Tamanho: hoje cada projeto usa ~15–20 MB na nuvem só com a revisão; a base bruta (milhares de
  respondentes x dezenas de perguntas) pode multiplicar esse tamanho, mas ainda deve caber tranquilo no
  plano grátis do Turso (5 GB).
- **Uma pessoa por vez** já é a regra da revisão (nuvem_turso.md: "a última gravação vence"); gravar a
  base também exigiria pensar em quem "recarrega a planilha" e o que acontece se a fonte mudar no meio
  do campo (ver PEND-01, base parcial).
- Dado de cliente: já é aceito guardar respostas de pesquisa no Turso (é o que a revisão já faz); subir a
  base não muda esse risco, mas amplia o volume de dado sensível fora do disco de cada máquina.
- Não decidido se a base "read-only" sobe uma vez (como o `nuvem.py subir` já faz para a revisão) ou se
  passa a ser recarregada direto do banco a cada "Recarregar planilha".

## Próximo passo
Quando for retomar: desenhar como um `projeto.json`/DSL substituiria os filtros em lambda antes de
decidir se vale a pena subir a base pro Turso, e se compensa mover `SESI_cat` para dentro de `tabulador`
ou manter pastas separadas (uma por cliente) mesmo com tudo na nuvem.

## Resolução (2026-09-25) — descartada
Rodei o conselho de IAs (`jumppi/_general/conselho`, personas Arquiteto/Crítico/Pragmático, 2 rodadas
— transcrição completa em
`jumppi/_general/conselho/rodadas/20260925_154316_pend-07-vale-a-pena-guardar-a-base-inteira-planilha-fonte-ba.md`).
Conclusão do Crítico e do Pragmático, que o Arquiteto não conseguiu rebater: subir a planilha-fonte
inteira (~3.700 linhas) pro Turso tem dois furos reais —
1. **Dado defasado silencioso:** a regra "usa o xlsx local se existir, senão baixa da nuvem" faz
   alguém com um `base_processamento.xlsx` velho esquecido na máquina gerar cruzamentos com demografia
   desatualizada sem erro nenhum.
2. **Gargalo de rede:** se o upload da fonte for atrelado ao mesmo fluxo que já sobe
   respostas/frame/codificação por pergunta, cada salvamento reenviaria um arquivo de megabytes,
   travando a experiência e estourando limite do Turso à toa.

Turso continua guardando só o que já guarda (o trabalho da equipe pergunta a pergunta). O menor passo
real para o problema que motivou a ideia (alguém numa máquina nova sem a pasta do projeto) é: (1)
copiar a `data/base_processamento.xlsx` uma vez via Drive/OneDrive quando precisar rodar em máquina
nova — 30 segundos, sem dívida técnica; (2) o aviso de nuvem não configurada ser claro e acionável,
que é exatamente o que resolve o caso do João (PEND-08) — já implementado no mesmo commit que fechou
esta pendência (`static/app.js`, tooltip do indicador de nuvem).
