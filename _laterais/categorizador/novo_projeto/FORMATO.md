# Formato do `projeto.json`

O `projeto.json` define um projeto no formato "plano": uma linha de cabeçalho e uma coluna por pergunta. Ele tem o mesmo conteúdo de um `projeto.py`, mas sem código, e fica na pasta do projeto. Quando existe `projeto.py` na mesma pasta, o `projeto.py` tem prioridade.

Há três jeitos de criar o arquivo, e os três usam o mesmo rascunho e o mesmo validador:

- **pelo app:** botão **+ Novo projeto**, ao lado do seletor de projeto;
- **por um agente de IA:** a skill `.claude/skills/novo-projeto/SKILL.md`, que serve para Claude Code, Codex e Antigravity;
- **pelo terminal:**
  ```
  python -m novo_projeto.cli rascunho <planilha.xlsx> --pasta <pasta> --nome "Nome"
  python -m novo_projeto.cli validar <pasta>
  python -m novo_projeto.cli registrar <pasta>
  ```

Para escrever um projeto do zero, parta de [modelo/projeto.json](modelo/projeto.json).

## Campos

| Campo | O que é |
|---|---|
| `NOME`, `CLIENTE` | Nomes que aparecem na interface e nos relatórios. |
| `FORMATO` | Sempre `"plano"`. O formato SurveyMonkey continua sendo configurado em `projeto.py`. |
| `FONTE_XLSX` | Caminho da planilha, relativo à pasta do projeto (o padrão é `data/…`). O categorizador só lê esse arquivo e nunca o altera. |
| `PLANO` | Traz três chaves: `aba` (onde estão os dados), `aba_codebook` (aba com os enunciados, opcional) e `id` (coluna com o id numérico do respondente). |
| `PII_MATCH` | Trechos de nomes de coluna com dados pessoais. Essas colunas nunca entram na base, nos prompts nem nas saídas. |
| `CONTEXTO_PROJETO` | Um parágrafo para a IA: quem respondeu, os temas e como costumam ser as respostas. |
| `FILTROS` | Define quem recebeu cada pergunta (ver abaixo). O filtro `todos` já existe e não precisa ser declarado. |
| `PERGUNTAS` | Lista com uma entrada por coluna usada (ver abaixo). Colunas que não aparecem aqui ficam fora da base. |
| `DERIVADAS` | Banners dos cruzamentos. Usa `mapa` (valor original → grupo) ou `faixas` (`[mín, máx, rótulo]`), e `niveis` precisa listar exatamente esses grupos. |
| `BANNERS_PADRAO` | Quais derivadas (ou perguntas) entram nos cruzamentos automáticos. |
| `SAIDA_PLANILHA` | A planilha final, que é uma cópia da fonte com a categoria de cada pergunta numa coluna. Traz `colunas`, no formato `{pergunta: "Q4_CAT"}`. |
| `CONFERENCIA` | Registra quem confirmou o pedido (`responsavel`), quando (`data`), por qual canal (`origem_pedido`) e quais abertas o cliente pediu (`abertas_pedidas`). O projeto só é aceito quando essa lista é igual à das perguntas com `codificar: true`. |

### Perguntas

Cada pergunta tem os campos `id`, `tipo` e `rotulo`. Use `coluna` quando o nome da coluna na planilha for diferente do `id`. Os tipos possíveis são:

- **`meta`**: id, datas, coletor, escola. Não é pergunta.
- **`unica`**: escolha única. Leva `niveis`, com as opções **copiadas exatamente como estão na planilha**, inclusive com erros de digitação.
- **`numerica`**: número. Com `"nps": true`, os cruzamentos mostram promotores e detratores. As respostas NS/NR ficam vazias.
- **`aberta`**: texto livre. Com `"codificar": true`, a pergunta entra na categorização. O campo `instrucoes_frame` (opcional) guarda instruções fixas para a IA montar as categorias.

Todas as perguntas aceitam `base`, que é o nome do filtro de quem a recebeu. Sem `base`, vale `todos`.

### Filtros

```json
"base_Q4": {"descricao": "Deram nota 0 a 6 (Q3)", "pergunta": "Q3", "entre": [0, 6], "ou_respondeu": "Q4"}
"base_Q2": {"descricao": "Vínculo = Outro (Q1)", "pergunta": "Q1", "em": ["Outro. Qual?"], "ou_respondeu": "Q2"}
```

Cada filtro usa `entre` (faixa numérica, com as pontas incluídas) ou `em` (lista de valores exatos). O campo `ou_respondeu` mantém na base quem respondeu a pergunta mesmo estando fora da regra. **Use-o sempre nas abertas.** O categorizador apaga da base tudo o que fica fora do filtro, e o validador trata como erro qualquer resposta aberta que seria perdida assim.

## O que o validador confere

**Erros** (impedem o registro do projeto):

- ainda há algum `PREENCHER`;
- uma coluna declarada não existe;
- o id está vazio, repetido ou não é numérico;
- um valor da planilha não está nas opções declaradas;
- uma resposta aberta seria perdida;
- um número seria perdido na conversão;
- uma coluna com dado pessoal foi declarada como pergunta;
- uma derivada ou um banner está inconsistente;
- a conferência do pedido está ausente ou diferente das perguntas marcadas.

**Avisos** (pedem apenas ciência):

- uma resposta fechada fica fora do filtro;
- há colunas não declaradas que têm dados;
- uma coluna `_CAT` marcada para categorizar não tem o destaque de cor das outras, ou uma coluna destacada não está marcada;
- há e-mails ou telefones dentro de respostas abertas.
