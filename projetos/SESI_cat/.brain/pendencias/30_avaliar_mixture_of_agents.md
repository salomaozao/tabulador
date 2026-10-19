---
id: PEND-30
titulo: Avaliar mixture of agents (2-3 modelos classificando e agregando) no lugar de classificador + auditor
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/coding.py, src/supervisao.py]
criticidade: baixa
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Ideia do Gabriel (01/10). Hoje já existe uma forma simples de MoA: um modelo classifica e outro audita (supervisao.auditar), e o auto-aceite exige a concordância dos dois. Avaliar o voto de 3 modelos baratos, ou um proposer + aggregator, medindo acerto contra o humano e custo. Só faz sentido depois da telemetria por modelo (PEND-26), que permite comparar sem achismo."
linear: JUM-17
---

# PEND-30: Mixture of agents

- **Pergunta a responder:** com o mesmo custo, 3 modelos baratos votando acertam mais (contra o gabarito humano) do que 1 modelo bom + auditor?
- **Experimento mínimo:**
  - usar 300 respostas já conferidas por humano da Q35;
  - rodar `supervisor.py` com 3 provedores;
  - comparar o acerto, a concordância e a cobertura de auto-aceite.
- **Depende de:** PEND-26.
- **Anti-escopo:** não mudar o pipeline de produção antes do experimento.
