---
name: desenhar-quadro-categorias
description: Propõe, revisa ou unifica o quadro de categorias (code frame) de uma pergunta aberta no Tabulador, com as mesmas regras que o programa manda para a IA e as lições do SESI (categoria de insatisfação genérica, "remete a resposta anterior", quadro único para perguntas irmãs, nomes de escola/cidade como NS/NR). Use antes de aprovar um frame, quando a auditoria achar muitas respostas forçadas em Outros ou numa categoria errada, ou quando pedirem para "criar/ajustar/revisar as categorias" de uma pergunta.
---

# Desenhar o quadro de categorias

O quadro é a decisão mais cara da categorização: um quadro ruim faz a IA errar com **confiança alta**, e
a auditoria só descobre depois. Esta skill vale para a IA do programa (é o mesmo conteúdo de
`codeframe._prompt_inducao` e `codeframe.refinar`) e para quem estiver revisando.

## Regras do programa (não mude sem mudar o código)

1. Quadro **fechado**, de 6 a 15 categorias, mutuamente exclusivas.
2. Nome curto (de 1 a 4 palavras) e definição objetiva de 1 frase.
3. **Uma ideia por categoria.** "Preço e Atendimento" é proibido.
4. Priorize o que o cliente consegue usar. Agrupe ideias raras em categorias mais amplas, a menos que sejam estratégicas.
5. **Não crie** "Outros" (97) nem "NS/NR" (98): elas são fixas e entram sozinhas.
6. De 2 a 4 exemplos **literais**, copiados das respostas.
7. Ordene da mais frequente para a menos frequente.
8. As instruções da pergunta (`instrucoes_frame` no projeto e o campo "Instruções para a IA") são obrigatórias.

## Lições do SESI (23/09/2026)

Saíram da auditoria de 1.223 respostas das perguntas Q4, Q30, Q32 e Q33.

- **Perguntas de "por quê" precisam de "Insatisfação geral (sem motivo específico)".** Respostas como "Estou
  insatisfeito", "Esperava mais", "Experiência horrível", "Piorou muito" e "Não está gostando" foram forçadas em
  "Qualidade do ensino" ou em Outros com confiança entre 0,30 e 0,45. Foi o erro mais comum:
  26 das 31 correções na Q32 e na Q33.
- **"Remete a resposta anterior"** ("pelos motivos já citados") vira categoria própria quando o projeto pede
  isso (Q32/Q33). Sem esse pedido, fica em NS/NR (Q30: "Já dito anteriormente"). Decida uma regra por projeto e
  escreva-a nas instruções.
- **Perguntas irmãs usam o mesmo quadro.** A Q32 ("provavelmente vai trocar") e a Q33 ("certamente vai trocar")
  ganharam um quadro único para poderem ser somadas no relatório. Os códigos precisam ser idênticos nas duas.
- **Separe "conclusão do ciclo" de "motivos externos"** em perguntas de retenção. Formatura não é
  insatisfação e costuma ser a maior categoria (na Q33, cerca de 45%).
- **Nome de escola, cidade ou pessoa sozinho** ("Alvimar", "Ubá", "Sesi Comar") vai para NS/NR, não para Outros.
- **Frases vagas mas válidas** ("Voltar às origens", "Ser mais imparcial") vão para Outros (97). Mantenha a
  mesma decisão em todas as perguntas do projeto; a Q4 e a Q30 tinham decidido diferente.
- **Idiomas e "ser bilíngue"** entram em Qualidade do ensino/metodologia, a menos que exista categoria própria.
- **Respeito ou tratamento humano com o aluno** entra em Acolhimento, não em Professores nem em Disciplina.
- **Categoria "Organização interna"** tende a virar depósito: a IA pôs exemplos de *comunicação* nela (Q4).
  Confira se os exemplos de cada categoria batem com a definição dela.

## Como revisar um quadro proposto

1. Leia as 40 respostas mais frequentes e 40 sorteadas (`supervisor.py auditar <QID>` gera o TSV).
2. Para cada categoria, pergunte: a definição separa claramente esta categoria da vizinha? Os exemplos batem com a definição?
3. Procure padrões **sem casa**: insatisfação genérica, remissão a respostas anteriores, elogio numa pergunta de
   crítica ("nada a melhorar"), motivos externos.
4. Faça uma classificação de amostra (30 a 60 respostas) antes de rodar tudo. Se mais de 5% for para Outros
   ou ficar com confiança abaixo de 0,5, o quadro ainda tem buraco.
5. Para mudar um quadro já aprovado **sem perder o que foi classificado**, use `python run.py frame <QID> adicionar|renomear|fundir|remover`.
   Fundir e remover remapeiam a classificação existente.
6. Quadro aprovado por IA sem o pesquisador: registre `aprovado_por` no `frame.json` e abra uma pendência
   pedindo a conferência humana (como a PEND-06 do SESI).
