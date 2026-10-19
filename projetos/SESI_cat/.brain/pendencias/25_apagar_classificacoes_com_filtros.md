---
id: PEND-25
titulo: Apagar classificações com filtros (popup com escopo, prévia e confirmação forte)
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, app.py, src/coding.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Botão 'Apagar classificações…' abre um popup com filtros combináveis: categoria(s), situação (só não conferidas / só automáticas / só com erro / inclui conferidas por humano), origem/modelo e frame_versao. A prévia mostra quantas e quais respostas saem. As apagadas voltam a 'não classificadas'. Snapshot automático antes (PEND-24). Incluir conferidas por humano exige marcar uma caixa a mais e digitar o número de respostas para confirmar."
linear: JUM-13
---

# PEND-25: Apagar classificações com filtros

- **Padrão:** "só não conferidas por humano" vem marcado. Conferidas por humano nunca entram por padrão.
- **Prévia:** contagem por categoria e 10 exemplos. O botão final diz "Apagar 312 classificações" com o número real.
- **Backend:**
  - `coding.apagar(qid, filtros, por)` devolve `{removidas, rids}`;
  - grava com `permitir_reducao=True` (PEND-24) e registra no histórico da pergunta (quem, filtros, n).
- **Desfazer:** "↶ Desfazer" logo depois, que devolve **só os itens apagados** (pelos rids). Restaurar o snapshot inteiro desfaria também o que outras pessoas conferiram nesse meio-tempo (ver PEND-31).
- **Depende de:** PEND-24 camadas 1-2.
- **Cuidado:** a lixeira local de `_apagar_pergunta` continua valendo para apagar a pergunta inteira. Esta é outra função, por item.
