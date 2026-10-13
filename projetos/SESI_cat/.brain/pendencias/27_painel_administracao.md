---
id: PEND-27
titulo: Painel de administração (pessoas, modelos, quadros) sobre a telemetria
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, app.py, static/app.js, src/usage.py]
criticidade: baixa
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Depois do PEND-26: uma aba Administração com (1) pessoas: revisões por dia, % de correções e categorias mais revisadas; (2) modelos: acerto contra humano, concordância com o auditor, custo e tempo (reaproveita usage.py, que já agrega por modelo, pergunta e dia); (3) quadros: linha do tempo de cada categoria (criada por, definições, mesclas) e acerto por frame_versao; (4) segurança: snapshots e bloqueios do PEND-24."
---

# PEND-27: Painel de administração

- **Depende de:** PEND-26, com algumas semanas de dados.
- **Reaproveitar:**
  - a tela de uso (`src/usage.py` + aba de uso em `app.js`), que já faz "Por pergunta / Por modelo / Por dia";
  - o `historico.py` (curva diária).
- **Não fazer:** login ou permissões. A identificação continua sendo o nome da aba.
