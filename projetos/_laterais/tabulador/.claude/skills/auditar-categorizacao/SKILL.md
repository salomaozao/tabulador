---
name: auditar-categorizacao
description: Protocolo para uma IA (Claude, Codex, Gemini...) atuar como SEGUNDO CODIFICADOR das respostas já classificadas pelo Tabulador. Lê o TSV de auditoria, registra só as discordâncias num JSON e aplica com --resto-ok. A concordância da auditoria é o que libera a confirmação automática. Use quando pedirem para "auditar", "conferir", "revisar a classificação", "dar segunda opinião" ou antes de rodar `supervisor.py auto-aceitar`.
---

# Auditar a categorização (segundo codificador)

A confiança que a IA declara não basta: abaixo de 0,50 ela erra metade das vezes, mas entre 0,50 e 0,70
ainda acerta mais de 96%. O que separa acerto de erro é **um segundo codificador independente concordar**.
Esse é o seu papel. Você não reclassifica do zero: julga se a categoria dada está certa.

Rode os comandos na pasta `tabulador`, sempre com `PYTHONIOENCODING=utf-8` no Windows.

## 1. Gerar a lista

```
python supervisor.py -p <projeto> auditar <QID>
```

O comando gera `<saída>/auditoria/<QID>_para_auditar.tsv` com rid, n, confiança, primária, secundária e texto.
Ficam de fora as respostas já conferidas por uma pessoa ou já auditadas (use `--todas` para refazer).
Imprima o quadro (`python run.py frame <QID> mostrar`) e leia as respostas em blocos de 300 a 400 linhas,
com o texto cortado em cerca de 200 caracteres. Para listas grandes, grave um arquivo compacto e leia por partes.

## 2. Critérios de julgamento

- **Primária = a PRIMEIRA ideia ou a ideia principal.** Resposta com vários temas não está errada só porque você
  destacaria outro tema. Discorde apenas quando a primária **não aparece** na resposta ou quando existe uma
  categoria claramente mais específica para ela.
- Secundária ausente ou discutível **não** é motivo para discordar.
- Confira a **coerência entre respostas parecidas** ("não se adaptou" numa ficou em Mudança e noutra em Outros?).
  Escolha uma regra e aplique a todas.
- Nomes de escola, cidade ou pessoa sozinhos → NS/NR (98). Frases vagas mas válidas → Outros (97).
- Muitas discordâncias do mesmo tipo mostram um **buraco no quadro**, não erro da IA. Pare, corrija o quadro
  (skill `desenhar-quadro-categorias`) e só então registre a sugestão com a categoria nova.
- Não corrija ortografia nem julgue o mérito da opinião do respondente.

## 3. Registrar só as discordâncias

`<saída>/auditoria/<QID>_veredito.json`:

```json
{"51":  {"primaria": 1, "secundaria": 2, "nota": "conclui o EM; lacunas = ensino"},
 "259": {"primaria": 7, "secundaria": null, "nota": "livros sumidos = furto/segurança (como rid 92)"}}
```

A `nota` é curta, diz o porquê e, quando for o caso, cita a resposta parecida que serviu de referência. Depois:

```
python supervisor.py -p <projeto> aplicar-auditoria <QID> <arquivo> --resto-ok   # o que não está no JSON = concorda
python supervisor.py -p <projeto> adotar-sugestoes <QID>   # a sua sugestão passa a aparecer; continua pendente
```

`adotar-sugestoes` guarda a classificação da IA em `ia_original` e escreve na justificativa
`[revisor <por>: nota] IA tinha: X`, para o pesquisador ver as duas opiniões.

## 4. Taxas de referência (SESI, 23/09/2026)

| Pergunta | Auditadas | Discordâncias | Principal causa |
|---|---:|---:|---|
| Q4 (melhorar para nota 10) | 610 | 7 (1,1%) | respeito/acolhimento; transparência |
| Q30 (pior que outras escolas) | 284 | 3 (1,1%) | idiomas; entretenimento |
| Q32 (provavelmente vai trocar) | 246 | 21 (8,5%) | faltava "Insatisfação geral" |
| Q33 (certamente vai trocar) | 83 | 10 (12%) | faltava "Insatisfação geral" |

Taxa acima de 5% quase sempre indica um buraco no quadro, não uma IA fraca.

## 5. O que não fazer

- Não marque `validado` à mão nem edite o `codificacao.json` direto. Use o supervisor, que preserva o
  que o pesquisador conferiu e registra `validado_por`.
- Não audite respostas que uma pessoa já conferiu ou corrigiu (o TSV já deixa essas de fora).
- Não trate "concordo" como "conferido por humano": a taxa de acerto da IA na interface conta só as conferências humanas.
