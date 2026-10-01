---
id: QA_{SLUG}
ciclo: {SLUG}
data_auditoria: {DATA}
auditor: {AUTOR}
commit_hash: {COMMIT_HASH}
veredito: REPROVADO
---

# Laudo de QA & Auditoria de Entrega: {TITULO}

## 1. Ambiente & Escopo do Teste
- **Branch / Worktree:** `{WORKTREE_OU_BRANCH}`
- **Commit Avaliado:** `{COMMIT_HASH}`
- **Auditor / Modelo:** `{AUTOR}`
- **Data da Execução:** `{DATA}`

## 2. Comandos de Validação Executados
```bash
# Testes Unitários e Integração
python -m unittest discover -s tests -v

# Validação Sintática de Frontend
node --check static/app.js
```

## 3. Matriz de Resultados
| Suíte de Teste / Verificação | Quantidade | Sucesso | Falhas | Status |
| :--- | :---: | :---: | :---: | :---: |
| Testes Unitários Backend | X | X | 0 | ✅ PASSOU |
| Sintaxe Frontend | X | X | 0 | ✅ PASSOU |
| Regressão de Endpoints | X | X | 0 | ✅ PASSOU |

## 4. Auditoria de Conservação & Regra Zero do Git
- [ ] **Conservação de Dados:** Bases de dados em `data/` permaneceram intactas.
- [ ] **Zero Código Fantasma:** Nenhuma função depreciada ou duplicada solta no arquivo.
- [ ] **Commits Cirúrgicos:** Nenhum `git add .` realizado; apenas arquivos de escopo foram alterados.
- [ ] **Anti-Escopo Respeitado:** Nenhum No-Go definido no PRD foi violado.

## 5. Veredito Final
> **Status:** `[ APROVADO PARA MERGE / REPROVADO ]`
- **Justificativa:** Explicação do resultado.
- **Próximo Passo:** Se aprovado, pode ser integrado à branch principal e implantado. Se reprovado, reabrir a tarefa com o diff de erro.
