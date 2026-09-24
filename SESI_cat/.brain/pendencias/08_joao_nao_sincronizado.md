---
id: PEND-08
titulo: João baixou o Tabulador do GitHub e não vê a revisão sincronizada (falta .env/credenciais da nuvem)
modulo_afetado: [tabulador, config.py, nuvem.py]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-24
resumo: "João clonou o tabulador direto do GitHub, que só traz código (não traz .env nem SESI_cat/data, gitignorados de propósito). Sem as credenciais TABULADOR_TURSO_URL/TOKEN da equipe (ou o atalho OneDrive do SharePoint que o config.py acha sozinho), o app dele grava local e vazio: as respostas antigas da revisão ainda não sincronizaram com o banco da equipe."
---

# PEND-08: João sem sincronizar (clone via GitHub, sem nuvem configurada)

## Contexto
`.env`, `SESI_cat/data/` e `output*` são propositalmente gitignorados (`AGENTS.md`: nunca versionar,
contêm dados de cliente). O João baixou o `tabulador` pelo GitHub, então recebeu só o código
(`tabulador/` e `SESI_cat/projeto.py`), sem:
- a planilha-fonte (`SESI_cat/data/base_processamento.xlsx`), que nunca vem do git;
- o `.env` (chave de IA + `TABULADOR_TURSO_URL`/`TABULADOR_TURSO_TOKEN`), achado automaticamente só
  quando o `config.py` encontra uma pasta `Shortcuts` subindo os pais de onde está o `tabulador`
  (atalho do SharePoint "IA - Jumppi/Categorização de Respostas Abertas" adicionado ao OneDrive).

Sem essas credenciais, o Tabulador dele volta a gravar em arquivo local (comportamento padrão sem
nuvem) e por isso as respostas já revisadas por outras pessoas não aparecem pra ele — "não sincronizado".

## O que fazer
1. Conseguir a planilha-fonte (`SESI_cat/data/base_processamento.xlsx`) por fora do GitHub (OneDrive/SharePoint).
2. Ver os mesmos dados de revisão: criar `tabulador/.env` (a partir de `.env.example`) com as **mesmas**
   `TABULADOR_TURSO_URL`/`TABULADOR_TURSO_TOKEN` do banco da equipe (pegar com o Gabriel por canal seguro,
   nunca em chat/planilha) — o `.env` local sempre vence o da equipe, então isso já resolve sozinho.
3. Alternativa mais definitiva (evita repetir a cada pessoa nova): pedir acesso à pasta do SharePoint e
   clicar em "Add shortcut to OneDrive"; só funciona se o clone do GitHub estiver dentro da árvore do
   OneDrive dele, senão a busca do `config.py` não encontra o atalho.
4. Depois de configurar, fechar e abrir de novo (`Abrir Tabulador.bat`).

## Pendente / atenção
Ainda não confirmado se o João já conseguiu sincronizar. Relacionado a [[PEND-07]] (guardar a base
inteira na nuvem eliminaria parte desse atrito para a próxima pessoa nova).
