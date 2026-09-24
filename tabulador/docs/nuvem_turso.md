# Guardar a revisão na nuvem (Turso)

Por padrão o Tabulador grava a revisão de cada pergunta (respostas, categorias, codificação) em
arquivos dentro de `output/perguntas/<pergunta>/`, no computador de quem está rodando o app. Se você
preencher as duas variáveis abaixo no `.env`, esses arquivos passam a ser lidos e gravados num banco
na nuvem (Turso) — assim todo mundo que abrir o Tabulador, em qualquer computador, vê a mesma revisão
sem precisar copiar pasta nenhuma.

O que **não** muda: a planilha-fonte (`data/*.xlsx`), o codebook, os cruzamentos e a planilha final
categorizada continuam sendo gerados como arquivo local — só a parte que é editada por pessoas (o
"loop de validação") vai para a nuvem.

## 1. Criar a conta e o banco

1. Entre em **https://turso.tech** e crie uma conta (dá para usar login do GitHub ou do Google).
2. No painel (**app.turso.tech**), clique em **Create Database**.
3. Dê um nome ao banco — sugestão: `tabulador-jumppi` (um banco só, compartilhado por todos os
   projetos; cada projeto do Tabulador já se separa sozinho dentro dele, veja "Como funciona" abaixo).
4. Escolha a região mais próxima do Brasil disponível (ex.: `gru`/São Paulo, ou a mais próxima disso).
5. Confirme a criação. Você cai na página do banco.

## 2. Pegar as duas credenciais

Na página do banco, você precisa de duas coisas:

- **Database URL**: algo como `libsql://tabulador-jumppi-<sua-org>.turso.io`. Normalmente aparece
  direto na página do banco (aba "Overview" ou botão "Connect").
- **Auth Token**: na mesma página, procure **Create Token** (ou "Generate Token"). Gere um token e
  **copie na hora** — ele só é mostrado uma vez.

Se preferir usar o terminal em vez do site (opcional, precisa instalar o `turso` CLI):

```
turso auth login
turso db create tabulador-jumppi
turso db show tabulador-jumppi --url
turso db tokens create tabulador-jumppi
```

## 3. Colocar no lugar certo (uma vez só, para todo mundo)

O Tabulador já sabe achar sozinho a chave da IA da equipe: existe um `.env` compartilhado na pasta
do SharePoint **"IA - Jumppi/Categorização de Respostas Abertas" → `Projeto IA/V3/.env`**, sincronizada
como atalho no OneDrive de todo mundo (pasta `Shortcuts`). Quem abre o Tabulador nem sabe que esse
arquivo existe — ele só funciona.

Colar as duas variáveis **nesse mesmo arquivo** (em vez de no `tabulador/.env` de cada pessoa) faz a
nuvem funcionar do mesmo jeito plug-and-play: quem já tem o atalho do OneDrive passa a usar o banco
compartilhado sem tocar em nada, e continua só configurando a chave da IA (se quiser trocar de
provedor) pela tela "Configurar IA" do próprio app.

```
TABULADOR_TURSO_URL=libsql://tabulador-jumppi-<sua-org>.turso.io
TABULADOR_TURSO_TOKEN=<o token que você copiou>
```

Depois de salvar esse arquivo, cada pessoa só precisa fechar e abrir o Tabulador de novo
(`Abrir Tabulador.bat`) — não precisa reinstalar nem configurar nada localmente.

**Alternativa (banco separado, só para uma máquina/teste):** colar as mesmas duas variáveis no
`tabulador/.env` local (criado a partir de `.env.example`) sobrepõe o valor da equipe só naquela
máquina — útil para testar sem afetar o banco de todo mundo.

Nunca cole essas credenciais em conversa, planilha ou commit — elas dão acesso de leitura/escrita ao
banco inteiro. Tanto o `.env` local quanto o da pasta compartilhada já ficam fora do Git.

## Como funciona por baixo (se quiser entender ou depurar)

Todo arquivo que antes ia para `output/perguntas/<pergunta>/*.json` vira uma linha da tabela `blobs`
do banco (`projeto`, `pergunta`, `arquivo`, `dados`, `atualizado_em`) — um banco só serve todos os
projetos do Tabulador (SESI, Assertiva, futuros), diferenciados pelo campo `projeto`. Código em
`nuvem.py`; o gatilho fica em `codeframe.py` (`_ler`/`_gravar`), então qualquer parte do app que já
usava essas duas funções passou a usar a nuvem automaticamente, sem precisar mexer em mais nada.

Isso exige internet: se a conexão cair no meio de uma revisão, a tela de revisão vai dar erro ao
salvar (em vez de gravar silenciosamente só localmente) — é proposital, para nunca haver duas
versões divergentes da mesma pergunta em máquinas diferentes.

## Quanto cabe no plano grátis

O plano free do Turso dá 5 GB e até 500 bancos. Um projeto do tamanho do SESI (respostas + frame +
codificação de todas as perguntas abertas) usa uns 15–20 MB — ou seja, o plano grátis aguenta bem
mais de 100 projetos desse tamanho antes de precisar de um plano pago.
