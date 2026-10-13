---
id: PEND-23
titulo: Janela "Auditoria concluída" mostra o ganho de confiança que a auditoria trouxe
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/supervisao.py, static/app.js]
criticidade: media
status: resolvido
data_resolucao: 2026-10-02
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Hoje a janela só diz 'N concordam e M discordam'. O auditor não devolve confiança e a auditoria não altera a confiança dos itens, então não existe ainda um 'aumento de confiança' para mostrar. Decidido (01/10, opção A): 'Antes: K com confiança alta, sem segunda opinião → Depois: K' passaram pelo auditor (confiança alta e outra IA concordou) · +Δ', mais a confiança média da IA nas concordadas e nas discordadas (calibração). Sem mudar o schema do auditor."
---

# PEND-23: Ganho de confiança na auditoria

- **Estado atual:**
  - `supervisao.auditar()` grava `auditoria = {por, ok, em[, primaria, secundaria, nota]}` e devolve `{auditadas, concorda, discorda, lotes_com_erro, por}`.
  - O `SCHEMA_AUDITORIA` não tem campo de confiança.
- **Decisão do Gabriel (01/10): opção A, sem mudar o schema.** O nome "liberadas para aceitar sozinhas" foi recusado. O texto precisa dizer que o auditor passou por cima.
  - **Destaque:** "Antes da auditoria: **K** com confiança alta, ainda sem segunda opinião → Depois: **K'** **passaram pelo auditor** (confiança alta e outra IA concordou) · **+Δ**".
  - **Linha de apoio (calibração):** "Confiança média da IA: 0,91 onde o auditor concordou × 0,62 onde discordou". Se a diferença for pequena, mostrar "a confiança da IA não está separando acerto de erro", porque isso é um alerta.
  - **Na tabela e nos filtros:** usar o mesmo termo, "passou pelo auditor", para não ter dois nomes para a mesma coisa.
- **Descartada:** a opção B (o auditor devolve a própria confiança e entra uma "confiança combinada"). Ela custa tokens e cria uma fórmula que alguém precisa defender.
- **Ressalva metodológica:** "passou pelo auditor" ≠ "está certa". Dois modelos podem errar juntos. A taxa real de erro dessas respostas vem da amostra de controle humana (PEND-32), e a janela deve mostrar essa taxa quando ela existir.
- **Também:** guardar o resumo de cada rodada de auditoria no `historico` da pergunta (alimenta OBJ-03 / PEND-26).

## Resolvida (02/10)
- `supervisao.auditar(..., limiar)` devolve `ganho` (alta, passaram_antes, passaram_depois, confiança média onde concordou x discordou); a janela mostra o texto da opção A e o alerta de calibração quando a diferença é < 0,10. Teste em `tests/test_supervisao.py`.
- **Fica para a PEND-26:** guardar o resumo de cada rodada de auditoria no `historico` da pergunta, e mostrar a taxa de erro real quando a PEND-32 existir. A tabela e os filtros já usam o termo da janela? Não conferido: verificar na PEND-26.
