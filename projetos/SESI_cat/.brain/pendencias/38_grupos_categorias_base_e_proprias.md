---
id: PEND-38
titulo: Grupos de perguntas - categorias base do grupo + categorias próprias de cada pergunta (rever a lógica do quadro único e da aprovação por pergunta)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, grupos_frame, codeframe, app.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Depois de usar a primeira versão dos grupos (quadro único + aprovação por pergunta), o Gabriel não gostou da lógica. Ideia a amadurecer: o grupo define categorias BASE (compartilhadas) que aparecem na página de cada pergunta, e cada pergunta pode ter categorias PRÓPRIAS (que só existem em Q4 ou só em Q5). Isso também esclarece o que significa 'aprovar' em cada pergunta. Sem pressa: já existe uma base implementada; evoluir mais para frente."
linear: JUM-24
---

# PEND-38: Grupos - categorias base do grupo + categorias próprias da pergunta

**Status:** guardado como pendência por decisão do Gabriel (02/10). **Não mexer agora.** Já existe uma base implementada (commits `a9aa5ac`..`4ee87fd`, plano em `tabulador/docs/IP_grupos_de_perguntas.md`, ponto de retorno: tag `pre-pivot-grupos`).

## O que o Gabriel observou ao usar
1. **Fluxo confuso:** entra-se no grupo, mas a geração das categorias acabou acontecendo "para a pergunta" e não de forma clara para o grupo.
2. **Categoria com dois assuntos:** a IA gerou categorias juntando dois temas. Isso tem que ser barrado **no prompt do categorizador** (um valor/atributo por categoria). A fase 1 reforçou o prompt e adicionou um aviso local por nome ("Preço e atendimento"), mas o caso real mostra que **precisa ser validado e endurecido** (ver tarefas).
3. **Aprovar categorias para Q4 e para Q5:** não ficou claro **o que difere** entre aprovar numa e na outra, já que o quadro é um só.
4. **Categorias que só aparecem numa pergunta:** haverá categorias que existem apenas em Q4 ou apenas em Q5 (ex.: motivo específico de nota baixa vs. de nota alta). O quadro 100% único não cobre isso.

## Ideia proposta (a desenvolver)
- **Categorias base do grupo:** o conjunto compartilhado, representativo do grupo inteiro.
- Essas categorias **aparecem dentro da página de cada pergunta**, junto das **categorias próprias** daquela pergunta (acréscimos que só valem nela).
- A aprovação passa a ter sentido claro: base aprovada **uma vez no grupo**; cada pergunta aprova **o que é só dela** (e a classificação).

## Perguntas em aberto (decidir antes de implementar)
- Categoria própria de Q5 entra no quadro que a IA usa para classificar Q4? (provável que não: só na própria pergunta.)
- Códigos: faixa reservada por pergunta (ex.: base 1-49, próprias 50-89) ou código global único? Impacto nos cruzamentos e no codebook exportado.
- Como o relatório/cruzamentos tratam categoria base (comparável entre perguntas) vs. própria (não comparável)?
- Quando uma categoria própria aparece nas duas perguntas, "promover" para a base (e remapear)?
- A página do grupo continua com a tabela única e coluna "Questão"? (a tabela única foi decisão anterior; manter ou voltar a uma visão por pergunta com a base vinculada.)
- Migração: o quadro único de hoje vira a "base" e as aprovações por pergunta viram o quê?

## Tarefas quando for retomado
- [ ] Validar com uso real o caso "categoria com dois assuntos": reproduzir, ver se o prompt de indução do grupo (`grupos_frame.induzir`) e o aviso `avisos_atributo` pegam; se não, endurecer (checagem pós-geração pedindo à IA que separe, ou rejeitar nomes com dois atributos).
- [ ] Desenhar o modelo base + próprias (arquivos, códigos, aprovação) e passar pelo conselho de IAs antes de implementar.
- [ ] Rever os rótulos da tela ("Aprovar categorias para Q4") até ficar óbvio o que cada aprovação significa.
- [ ] Relacionadas: PEND-35 (assistente de IA na criação do grupo), PEND-33 (auto-agrupamento de categorias humanas).
