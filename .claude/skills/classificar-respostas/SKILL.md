---
name: classificar-respostas
description: Regras para classificar respostas abertas contra um quadro de categorias FECHADO e aprovado, iguais às que o Tabulador manda para a IA (coding._prompt), com as convenções do SESI. Use quando uma IA precisar classificar respostas diretamente (sem chamar a API do programa), escrever ou revisar o prompt de classificação, ou entender por que a IA pôs uma resposta numa categoria.
---

# Classificar respostas

Estas regras são as de `coding._prompt`. Se mudar alguma aqui, mude lá também, e vice-versa.

## Entrada

- Contexto do projeto (`CONTEXTO_PROJETO` do `projeto.py`/`projeto.json`).
- Enunciado da pergunta.
- Quadro aprovado: `código: nome - definição (ex.: até 3 exemplos)`, mais 97 Outros e 98 NS/NR.
- Instruções da pergunta (`instrucoes_frame` + campo da interface) e, por resposta, a **observação do
  pesquisador**, que é obrigatória quando existe.
- Respostas únicas `rid: "texto"`. Textos iguais depois de normalizados já vêm agrupados (campo `n`).

## Regras

1. `primaria` = a categoria da **primeira ideia ou da ideia principal**. É obrigatória.
2. `secundaria` = uma segunda ideia **claramente distinta**; se não houver, `null`. Nunca é igual à primária.
3. 97 Outros: só para resposta válida que não cabe em nenhuma categoria.
4. 98 NS/NR: "não sei", vazia, sem sentido, **só o nome** de escola, cidade ou pessoa, "respondido acima"
   (a menos que o quadro tenha "Remete a resposta anterior").
5. `confianca` de 0 a 1: 1,0 = literal ou inequívoca; < 0,6 = ambígua, precisa de revisão humana.
6. `justificativa` curta (até 15 palavras).
7. Exatamente um item por `rid`, na mesma ordem. Nunca invente código fora do quadro: o programa troca
   por Outros com confiança 0.

Saída: `{"codificacoes": [{"rid", "primaria", "secundaria", "confianca", "justificativa"}]}`.

## Convenções que evitam retrabalho (SESI, 23/09/2026)

- Resposta que só expressa sentimento geral ("insatisfeito", "excelente em tudo") vai para a categoria
  genérica do quadro, se existir, e **não** para "Qualidade do ensino".
- Numa pergunta de ponto forte, uma reclamação ("o app é difícil de entrar") é Outros (97), não NS/NR.
- Na pergunta "em que é melhor", "em nada" ou "não é melhor" também é Outros (97): é uma resposta válida.
- Idiomas ou "bilíngue" → ensino. Respeito ou tratamento humano → acolhimento. Furto ou sumiço de material → segurança.
- Listas de temas ("Estrutura, ensino e tecnologia"): primária = o primeiro tema; secundária = o segundo.
  Nesse caso a confiança pode ser alta, porque a ordem é explícita.
- Nomes próprios de funcionários na resposta não mudam a categoria. **Não repita** nomes na justificativa.

## Lotes

O programa manda de 30 a 40 respostas por chamada. Mais que isso aumenta a chance de a IA pular `rid`s
(o programa marca "LLM não devolveu esta resposta" como erro, e o `supervisor.py rodar` refaz).
