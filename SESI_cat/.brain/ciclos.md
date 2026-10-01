# Linha de Montagem de Software (MetaGPT / SOPs)

Este documento centraliza todos os ciclos de engenharia do projeto **Sesi Cat**, operados através de artefatos estruturados e papéis tipados.

---

## 🚦 Estado da Linha de Montagem em Tempo Real
- **Ciclo Ativo:** `2026-10-01_amostra_controle`
- **Fase Vigente:** `PRD`
- **Role da Vez:** `Product Manager`
- **Próxima Ação:** Role: Product Manager. Preencha e aprove o arquivo .brain/ciclos/2026-10-01_amostra_controle/01_PRD.md com requisitos e anti-escopos.

---

## 📦 Inventário de Ciclos de Desenvolvimento

| Ciclo / Identificador | Título / Objetivo de Negócio | Objetivo | Status | Tarefas | Veredito QA | Artefatos |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **[2026-10-01_amostra_controle](ciclos/2026-10-01_amostra_controle)** | 2026-10-01 Amostra Controle | `OBJ-02` | `DRAFT` | `0/9` | `REPROVADO` | [PRD](ciclos/2026-10-01_amostra_controle/01_PRD.md) · [ARCH](ciclos/2026-10-01_amostra_controle/02_ARCH.md) · [TASKS](ciclos/2026-10-01_amostra_controle/03_TASKS.json) · [QA](ciclos/2026-10-01_amostra_controle/04_QA_REPORT.md) |
| **[2026-09-30_feedbacks_sara](ciclos/2026-09-30_feedbacks_sara)** | 2026-09-30 Feedbacks Sara | `OBJ-01` | `DRAFT` | `0/2` | `PENDENTE` | [PRD](ciclos/2026-09-30_feedbacks_sara/01_PRD.md) · [ARCH](ciclos/2026-09-30_feedbacks_sara/02_ARCH.md) · [TASKS](ciclos/2026-09-30_feedbacks_sara/03_TASKS.json) · [QA](ciclos/2026-09-30_feedbacks_sara/04_QA_REPORT.md) |
| **[2026-09-29_timeout_progresso](ciclos/2026-09-29_timeout_progresso)** | 2026-09-29 Timeout Progresso | `OBJ-01` | `CONCLUIDO` | `3/3` | `APROVADO` | [PRD](ciclos/2026-09-29_timeout_progresso/01_PRD.md) · [ARCH](ciclos/2026-09-29_timeout_progresso/02_ARCH.md) · [TASKS](ciclos/2026-09-29_timeout_progresso/03_TASKS.json) · [QA](ciclos/2026-09-29_timeout_progresso/04_QA_REPORT.md) |

---

## 🛠️ Comandos da Linha de Montagem (CLI)
```bash
# Ver status detalhado da esteira
python .brain/scripts/manage_brain.py sop status

# Iniciar novo ciclo a partir do template
python .brain/scripts/manage_brain.py sop novo <slug-da-feature> --titulo "Nome da Demanda" --obj OBJ-01

# Avançar para a próxima fase (PRD -> ARCH -> TASKS -> DEV -> QA -> MERGED)
python .brain/scripts/manage_brain.py sop avancar --nota "Artefato validado"

# Recuar em caso de rejeição em teste ou arquitetura
python .brain/scripts/manage_brain.py sop recuar --motivo "Falha nos testes de regressão"

# Atualizar status de uma tarefa no WBS
python .brain/scripts/manage_brain.py sop task TASK-01 DONE
```
