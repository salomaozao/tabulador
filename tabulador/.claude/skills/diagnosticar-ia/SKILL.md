---
name: diagnosticar-ia
description: Descobre por que a IA do Tabulador não responde (chave inválida, cota esgotada, provedor sem crédito, variável de ambiente trocada) e escolhe um provedor que aguente o volume da categorização. Use quando aparecer "Please pass a valid API key", "quota", "no credits", 429/403/400, "Failed to fetch" ou quando for rodar milhares de respostas e precisar estimar se o provedor aguenta.
---

# Diagnosticar a IA do Tabulador

Rode tudo na pasta `tabulador`. **Nunca imprima o valor de uma chave**: compare chaves entre si
(`a == b`) ou mostre só se existem (`bool(chave)`).

## 1. De onde vem a chave

- `tabulador/.env` guarda uma chave por provedor (`TABULADOR_CHAVE_<PROVEDOR>`) e a ativa em
  `OPENAI_API_KEY` + `OPENAI_PROVEDOR` + `OPENAI_MODEL`.
- Desde 23/09/2026 o `config.py` usa `load_dotenv(ENV_FILE, override=True)`: o `.env` do Tabulador
  **vence** as variáveis do Windows. Antes disso, um `OPENAI_API_KEY` definido no sistema (de outro
  provedor) era mandado para o Gemini e dava `400 Please pass a valid API key`.
- Consequência: para trocar de provedor **só numa execução**, não use variável de ambiente; use as
  opções do supervisor (`--provedor`, `--modelo`), que mudam `config` em memória sem gravar o `.env`.

## 2. Teste rápido de cada provedor (sem mostrar chaves)

```python
from dotenv import dotenv_values; from openai import OpenAI
e = dotenv_values('.env')
testes = [('gemini', e.get('TABULADOR_CHAVE_GEMINI'), 'https://generativelanguage.googleapis.com/v1beta/openai/', 'gemini-2.5-flash'),
          ('openai', e.get('TABULADOR_CHAVE_OPENAI'), None, 'gpt-4.1-mini'),
          ('groq',   e.get('TABULADOR_CHAVE_GROQ'), 'https://api.groq.com/openai/v1', 'openai/gpt-oss-120b')]
for nome, k, url, m in testes:
    try:
        OpenAI(api_key=k, base_url=url).chat.completions.create(model=m, messages=[{'role': 'user', 'content': 'ok'}], max_tokens=5)
        print(nome, 'OK')
    except Exception as ex:
        print(nome, 'FALHA', str(ex)[:120])
```

Provedores CLI (usam o login do programa, sem chave): `python supervisor.py -p <projeto> --provedor cli_claude --modelo sonnet preparar <QID>`
serve de teste real.

## 3. O provedor aguenta o volume?

Conta: chamadas = respostas únicas ÷ lote (padrão 30; com CLI use `--lote 40`). O SESI tinha cerca de 7 mil
respostas únicas, ou seja, cerca de 200 chamadas.

| Provedor | O que aconteceu no SESI (23/09/2026) |
|---|---|
| Gemini, plano gratuito | **20 chamadas por dia** por modelo (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`). Acabou no meio da Q4 e deixou 360 respostas com erro. Serve só para teste. |
| OpenAI | `429 You have no credits remaining`: a conta ficou sem crédito. |
| Groq, gratuito | Responde, mas tem limite diário de tokens, é lento (até 87 s por lote) e às vezes cai para `json_object`. Serve para amostras. |
| **Claude Code CLI (`cli_claude`, sonnet)** | **Usado na produção.** Sem chave. Lote de 40 leva de 30 a 70 s. No máximo 2 chamadas simultâneas por processo; dá para rodar 2 ou 3 processos em perguntas diferentes. |

## 4. Erros e o que fazer

| Mensagem | Causa | Ação |
|---|---|---|
| `400 Please pass a valid API key` (Gemini) | chave de outro provedor indo para o Gemini | conferir o `override=True`; testar com a chave do `.env` |
| `403 ... reported as leaked` | chave vazada e bloqueada | gerar nova no AI Studio, trocar em ⚙ Configurar IA (ver PEND-04 do SESI) |
| `429 ... free_tier_requests, limit: 20` | cota diária gratuita | trocar de provedor; não adianta insistir |
| `429 no credits remaining` | conta sem saldo | trocar de provedor ou pedir recarga |
| respostas com `origem: "erro"` | lote falhou | `supervisor.py rodar` tira essas respostas e refaz (até `--tentativas`) |

## 5. Regra de ouro

Mudou o provedor? Registre no `dialogo_ias.md` do projeto qual modelo classificou cada pergunta, porque o
`codificacao.json` guarda o `modelo` da última rodada e isso entra na documentação da entrega.
