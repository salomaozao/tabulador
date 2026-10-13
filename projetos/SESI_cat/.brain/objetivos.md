# Bússola Estratégica: Objetivos e Dores do Projeto

Este arquivo é a bússola de valor do projeto **Sesi Cat**.
Ele define as dores reais a serem sanadas, os ganhos esperados, critérios de vitória e os limites rígidos de escopo (No-Gos / Rabbit Holes).

> **Atenção para as IAs:** Nenhuma tarefa ou código deve ser produzido sem estar a serviço de um dos objetivos ativos abaixo. Consulte sempre os Anti-Escopos e Rabbit Holes no arquivo detalhado antes de propor alterações.

---

## 🎯 Objetivos Ativos (Dores Prioritárias)

| ID | Objetivo / Dor | Área | Prioridade | Vitória Esperada / Ganhos | Detalhes |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **[OBJ-01](objetivos/01_classificacao_multiprojeto_e_resiliencia_rid.md)** | **Classificação automatizada multi-projeto e resiliência de RID em nuvem** | `engenharia_dados` | **Alta** | Módulo tabulador executando sem erros em todos os projetos mapeados.  RIDs estáveis persistidos corretamente na nuvem. | [Abrir](objetivos/01_classificacao_multiprojeto_e_resiliencia_rid.md) |
| **[OBJ-02](objetivos/02_quadro_aprende_com_a_revisao.md)** | **Quadro de categorias aprende com a revisão humana (IA erra menos e categoria ruim aparece sozinha)** | `tabulador` | **Alta** | acerto_ia sobe entre versões do quadro numa pergunta real (ex.: Q35).  O % de autoaceite com auditor concordando aumenta depois... | [Abrir](objetivos/02_quadro_aprende_com_a_revisao.md) |
| **[OBJ-03](objetivos/03_protecao_e_rastreabilidade_da_base.md)** | **Base classificada protegida contra perda e rastreável (quem/qual modelo fez o quê, e quando)** | `tabulador` | **Alta** | Dá para restaurar a codificação de uma pergunta para qualquer ponto das últimas 72 h, com a nuvem ativa.  Um teste que simula u... | [Abrir](objetivos/03_protecao_e_rastreabilidade_da_base.md) |
| **[OBJ-04](objetivos/04_tabulador_como_site.md)** | **Transformar o Tabulador (e as ferramentas da Jumppi) num site único, acabando com a sincronização entre máquinas** | `tabulador` | **Alta** | O Tabulador roda num endereço web com login, e o projeto SESI funciona ponta a ponta (carregar base, classificar, revisar, expo... | [Abrir](objetivos/04_tabulador_como_site.md) |

---

## 🏁 Objetivos Alcançados (Problemas Resolvidos)

| ID | Objetivo | Área | Conclusão | Ganhos Obtidos vs Esperados | Registro |
| :--- | :--- | :---: | :---: | :--- | :---: |
| *Nenhum objetivo arquivado ainda* | - | - | - | - | - |

---

## Como Operar a Bússola
1. **Adicionar Objetivo:** Crie `.brain/objetivos/XX_nome.md` com YAML frontmatter e seções padronizadas.
2. **Encerrar Objetivo:** Altere `status: alcancado` e informe `data_conclusao: AAAA-MM-DD`.
3. Sincronize com:
   ```bash
   python .brain/scripts/manage_brain.py sync
   ```
