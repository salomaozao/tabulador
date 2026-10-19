---
name: supervisionar-categorizacao
description: Conduz a categorização de todas as perguntas abertas de um projeto do Tabulador sem o pesquisador presente, deixando para ele só o que precisa de olho humano. Fluxo: preparar → quadro → classificar → auditar → aceitar sozinho o que tem alta confiança → fila de revisão. Use quando pedirem para "categorizar tudo", "rodar a categorização", "matar o máximo com alta confiança", "supervisionar a IA" ou "adiantar a categorização enquanto eu não estou".
---

# Supervisionar a categorização

**Meta:** o pesquisador volta e encontra cada pergunta classificada. Tudo o que tem alta confiança está
confirmado automaticamente, e o resto está numa fila curta, com a sugestão do auditor à vista. Nada de
decisão irreversível: tudo pode ser desfeito e o que o pesquisador já conferiu nunca é tocado.

Ferramenta: `tabulador/supervisor.py` (CLI). Rode na pasta `tabulador` com `PYTHONIOENCODING=utf-8`.
As opções globais valem só para a execução e não gravam no `.env`: `--provedor cli_claude --modelo sonnet --lote 40 --paralelo 2`.

## 0. Antes de começar

1. Leia o `.brain/decisoes.md` e o `.brain/pendencias.md` do projeto (skill `manage-brain`).
2. **Backup:** `cp -r <saída>/perguntas <saída>/_backup/perguntas_<data>_antes_supervisao`.
3. Confirme que o app (porta 5000) **não** está aberto mexendo nas mesmas perguntas. Os dois gravam o mesmo `codificacao.json`.
4. `python supervisor.py -p <projeto> status` mostra o painel de todas as perguntas.
5. Escolha o provedor pela conta de volume (skill `diagnosticar-ia`). Plano gratuito não aguenta milhares de respostas.

## 1. Quadro de categorias

- Pergunta sem `respostas.json` ou sem frame: `python supervisor.py -p <projeto> --provedor cli_claude preparar <QID>`.
  O comando lê as respostas e induz o quadro **em rascunho**.
- Revise com a skill `desenhar-quadro-categorias`, principalmente as categorias genéricas: "Insatisfação geral"
  em perguntas de motivo e "Elogio geral" em perguntas de ponto forte.
- Perguntas irmãs (ex.: "provavelmente" e "certamente vai trocar") → um quadro só, com os mesmos códigos.
- Se aprovar sem o pesquisador: `python run.py frame <QID> aprovar`, grave `aprovado_por` no `frame.json`
  e **abra uma pendência** pedindo a conferência.

## 2. Classificar

```
python supervisor.py -p <projeto> --provedor cli_claude --modelo sonnet --lote 40 rodar <QID> [<QID>...]
```

- Usa `somente_faltantes`: não refaz o que já está classificado nem o que foi conferido.
- Lotes com erro são retirados e refeitos (até `--tentativas`, padrão 3).
- Rode em segundo plano, com um processo por grupo de perguntas (de 2 a 3 processos, **nunca** dois na mesma pergunta).
  Acompanhe pelos arquivos `<saída>/llm_log/*code_<QID>_*.json`.
- No SESI, com o Claude Code CLI e lote de 40: de 30 a 70 s por lote; a Q29 (1.297 respostas) levou 11 min.

## 3. Auditar (segundo codificador)

Siga a skill `auditar-categorizacao`: `auditar` → ler → `<QID>_veredito.json` só com as discordâncias
→ `aplicar-auditoria --resto-ok` → `adotar-sugestoes`.

Se a auditoria achar um **buraco no quadro**, corrija o quadro (`run.py frame <QID> adicionar ...`) e rode
`python supervisor.py -p <projeto> reclassificar <QID> --categorias 97`, que manda de novo só as não conferidas
em Outros. Depois audite essas de novo.

## 4. Aceitar o que tem alta confiança

```
python supervisor.py -p <projeto> auto-aceitar <QID> --limiar 0.70
```

A resposta é confirmada (`validado_por: "auto"`) só se **todas** as condições valem: confiança >= limiar,
auditoria concorda, não é Outros e não teve erro. As respostas NS/NR marcadas por regra também entram.
Essas confirmações ficam **fora** da taxa "acerto da IA" da interface.

Calibração do SESI (1.223 respostas): a discordância do auditor foi de 0,7% em >= 0,95, 0% entre 0,85 e 0,95,
0,8% entre 0,70 e 0,85, 3,6% entre 0,50 e 0,70 e 49% abaixo de 0,50. Daí o limiar de 0,70. Recalibre a cada
projeto com os dados da auditoria antes de mudar o limiar.

Para desfazer: `python supervisor.py -p <projeto> desfazer-auto <QID>`.

## 5. Entregar a fila ao pesquisador

- `python supervisor.py -p <projeto> fila <QID> -n 60` lista as pendentes, das mais frequentes para as menos, com a sugestão do auditor.
- Na interface, as confirmadas vão para o fim da tabela e as pendentes ficam no topo. Com o teclado, Enter confirma e os números trocam a categoria.
- **Não aprove a codificação** (`run.py code <QID> aprovar`) sem o pesquisador: é isso que alimenta a planilha final.

## 6. Registrar

- `dialogo_ias.md` do projeto: o que foi feito, qual modelo classificou cada pergunta, os números
  (aceitas, pendentes, discordâncias) e as decisões de quadro.
- Pendências para tudo o que o pesquisador precisa decidir.
- As lições novas entram nas skills (este arquivo, `desenhar-quadro-categorias`, `auditar-categorizacao`).
