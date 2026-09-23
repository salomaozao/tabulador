---
name: novo-projeto
description: Cria um projeto novo no Categorizador de respostas abertas a partir de uma planilha de pesquisa (.xlsx no formato "plano", com um cabeçalho e uma coluna por pergunta), seguindo um processo em etapas com travas. O rascunho é gerado sem IA, a pessoa confirma o pedido e o validador roda o pipeline real. Use quando pedirem para "criar projeto", "cadastrar pesquisa nova no categorizador", "configurar projeto.json" ou "preparar categorização de uma base nova".
---

# Novo projeto no Categorizador

Esta skill cria o `projeto.json` de uma pesquisa nova. O processo é fixo e **nenhuma etapa pode ser pulada**. A maior parte do arquivo já vem pronta de um rascunho feito por código, que lê a planilha sem IA. O seu papel se resume a três coisas:

- **perguntar** à pessoa o que não está nos dados;
- **escrever** os textos (contexto, rótulos, instruções);
- **rodar o validador** até ele aceitar.

Formato completo do arquivo: `novo_projeto/FORMATO.md`.

## Por que o processo é travado

No SESI, a IA acertou tudo o que estava nos dados (tipos, opções, filtros, dados pessoais) e errou no que estava só no pedido: marcou a Q30 para categorizar, mas o cliente tinha destacado em amarelo apenas 7 colunas `_CAT`, e a Q30 não estava entre elas. Os erros que custam caro são silenciosos:

- uma opção redigitada faz as respostas sumirem;
- um filtro errado apaga respostas da base;
- um dado pessoal acaba indo para a IA.

Por isso vale a regra: **dados vêm do código; intenção vem da pessoa; você não inventa nenhum dos dois.**

## Como rodar os comandos

Rode sempre na pasta `_laterais/categorizador`, com o Python do ambiente do categorizador:

```
PY = %LOCALAPPDATA%\Categorizador\venv\Scripts\python.exe   (se não existir: python)
$PY -m novo_projeto.cli <comando> ...
```

## Etapa 1: Perfil da planilha

```
$PY -m novo_projeto.cli perfil <planilha.xlsx> [--aba <aba>]
```

- Leia o resumo que o comando imprime. **O perfil é a sua fonte de verdade.** Não abra a planilha por outro caminho nem "corrija" valores que aparecem nela.
- Se a planilha tiver mais de uma aba de dados, ou cabeçalho em duas linhas (SurveyMonkey), **pare**. Esse formato não é coberto pela skill: avise a pessoa de que ele é configurado à mão em `projeto.py`.

## Etapa 2: Perguntas obrigatórias à pessoa

Faça estas perguntas **antes** de gerar o rascunho. Se o seu ambiente tiver uma ferramenta de perguntas (AskUserQuestion ou similar), use-a. Se a pessoa não souber alguma resposta, registre "não informado". **Nunca invente uma resposta.**

1. **Nome do projeto e do cliente.** Pergunte também onde criar a pasta. O padrão é `jumppi/<Nome>_cat/`.
2. **Quem pediu a categorização e por qual canal** (e-mail, reunião, planilha marcada…). Isso vai para `CONFERENCIA.responsavel`, `CONFERENCIA.origem_pedido` e `CONFERENCIA.data`, que é a data de hoje.
3. **Quais perguntas abertas o cliente pediu para categorizar.** Mostre à pessoa:
   - as colunas `_CAT` com o cabeçalho destacado ("cabeçalho destacado" no perfil);
   - as `_CAT` sem destaque;
   - as abertas sem coluna `_CAT`.

   A lista confirmada vai para `CONFERENCIA.abertas_pedidas`.
4. **Contexto da pesquisa:** quem respondeu, o objetivo e os temas. É com isso que você escreve o `CONTEXTO_PROJETO`.
5. **Regras de pulo do questionário**, se a pessoa souber. Exemplo: "a Q4 só aparece para quem deu nota até 6". Servem para conferir os filtros que o rascunho deduziu.

## Etapa 3: Rascunho sem IA

```
$PY -m novo_projeto.cli rascunho <planilha.xlsx> --pasta <pasta> --nome "<Nome>" --cliente "<Cliente>"
```

O comando copia a planilha para `<pasta>/data/`, grava o perfil em `<pasta>/output/novo_projeto/perfil.json` e cria `<pasta>/projeto.json`. **Leia cada item da lista "Confira" que ele imprime**, porque são as deduções que precisam ser revistas.

## Etapa 4: Completar o projeto.json

Você **pode** editar:

- `CONTEXTO_PROJETO`, escrito a partir da resposta 4, sem acrescentar fatos que a pessoa não deu;
- `rotulo` de cada pergunta, deixando-o mais curto e legível;
- `instrucoes_frame` das abertas marcadas, que é opcional: diga que tipo de categoria faz sentido, como "PONTOS A MELHORAR", "MOTIVO DA TROCA" etc.;
- `CONFERENCIA`, com as respostas da etapa 2;
- `codificar` das abertas, **somente** para que fique igual a `CONFERENCIA.abertas_pedidas`. Quando uma aberta sai da lista, retire-a também de `SAIDA_PLANILHA.colunas`; quando entra, acrescente `"<id>": "<coluna>_CAT"`;
- `DERIVADAS` e `BANNERS_PADRAO`, apenas se a pessoa pedir cruzamentos. **As chaves de `mapa` precisam ser copiadas dos valores do perfil**, e `niveis` precisa listar exatamente os grupos usados.

Você **não pode**, a menos que a pessoa confirme de forma explícita e você registre isso em `_notas`:

- redigitar ou "corrigir" `niveis`, nem mesmo um erro de digitação da planilha;
- alterar `FILTROS`. Se o filtro deduzido contradisser a regra de pulo informada pela pessoa, mostre a diferença e pergunte qual vale. **Nunca remova `ou_respondeu`**;
- tirar uma coluna de `PII_MATCH` ou declarar como pergunta uma coluna com dado pessoal;
- mudar `tipo`, `PLANO` ou `FONTE_XLSX`.

## Etapa 5: Validar, até não haver erro

```
$PY -m novo_projeto.cli validar <pasta>
```

- **❌ Erro:** corrija dentro das regras da etapa 4 e rode de novo. Se a correção exigir algo proibido (mudar opções ou filtros, por exemplo), pergunte à pessoa.
- **⚠ Aviso:** mostre **todos** os avisos à pessoa e anote a decisão dela. Os avisos de cor em `_CAT` e de dado pessoal dentro do texto são importantes.
- Não passe para a etapa 6 enquanto o validador não disser "✅ Projeto válido".

## Etapa 6: Registrar e ler a base

```
$PY -m novo_projeto.cli registrar <pasta> [--slug <nome-curto>]
$PY run.py --projeto <slug> load
```

O comando `registrar` roda o validador de novo e só grava em `projetos.json` se não houver nenhum erro.

## Etapa 7: Relatório final à pessoa

Mostre à pessoa:

- as abertas que serão categorizadas e o número de respostas de cada uma;
- os filtros e as notas que ela precisa confirmar;
- os avisos que ela aceitou;
- como abrir o projeto: `iniciar.bat` e escolher o projeto no topo da página.

Se a pasta do projeto tiver `.brain/`, registre a criação do projeto em `.brain/dialogo_ias.md`.
