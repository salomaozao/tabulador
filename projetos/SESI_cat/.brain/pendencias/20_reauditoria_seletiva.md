---
id: PEND-20
titulo: Aprendizado do quadro, etapa 2C (reauditar só as não conferidas afetadas quando o quadro muda)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/supervisao.py, src/aprendizado.py]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
resumo: "Depois de uma atualização automática do quadro (PEND-19), rodar supervisao.auditar só nas respostas não conferidas por humano, cuja categoria (ou o par de confusão dela) mudou e cujo frame_versao é anterior ao atual. Se o auditor discordar de uma auto-aceita, ela volta para 'a conferir' com o motivo. A guarda volumétrica (PEND-14) vale acima de 100 respostas."
linear: JUM-9
---

# PEND-20: Reauditoria seletiva

- **Pré-requisito já pronto (PEND-18):** cada item novo grava `frame_versao`, e o histórico diz quais categorias mudaram em cada versão.
- **Itens antigos sem `frame_versao`:** tratar como versão 1.
- **Não fazer:** reclassificar (só auditar); tocar em item com `origem=humano` ou `validado_por=humano`.
