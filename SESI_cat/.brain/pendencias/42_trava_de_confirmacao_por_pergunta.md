---
id: PEND-42
titulo: Trava por pergunta que impede confirmar respostas e aprovar a pergunta até alguém desmarcar
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, src/coding.py, src/supervisao.py, app.py, static/app.js]
criticidade: media
status: resolvido
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
data_resolucao: 2026-10-02
resumo: "Pedido do Gabriel (02/10): poder bloquear uma pergunta de ser confirmada, com uma flag, e ela só ser confirmada se a flag for desmarcada manualmente. Feito na branch feat/trava-confirmacao-e-ordem-categorias (worktree worktrees/tabulador-trava-ordem), aguardando merge na main."
---

# PEND-42: Trava de confirmações

- **Decisões do Gabriel (02/10):** a trava impede (a) confirmar respostas (✓ individual, 'Confirmar as N mostradas', confirmar categoria em bloco, 'Aceitar alta confiança') e (b) aprovar a pergunta. **Corrigir categoria e desfazer confirmação continuam livres.** Qualquer pessoa pode desmarcar.
- **Onde fica:** `codificacao.json` → `confirmacao_travada: {por, em}`. Reclassificar não destrava; apagar a classificação apaga a trava.
- **Backend:** `coding.definir_trava`, `ConfirmacaoTravada` (recusa em `atualizar_item(validado=True)`, `validar(valor=True)`, `aprovar` e `supervisao.auto_aceitar`); `POST /api/pergunta/<qid>/trava {travada}`; o auditar com 'aceitar sozinhas' faz a auditoria e devolve `auto_bloqueado` em vez de aceitar. `resumo_revisao` expõe `confirmacao_travada`.
- **Tela:** caixa '🔒 Travar confirmações' ao lado de 'Aprovar e gravar' na barra fixa; pílula '🔒 confirmações travadas' na barra; ✓ vira 🔒 desabilitado nas pendentes; Enter avisa; 'Aceitar alta confiança' e 'Aprovar' desabilitados com o motivo. Na tela do grupo só o servidor recusa (mensagem de quem travou).
- **Log:** eventos `travar_confirmacoes` e `destravar_confirmacoes` (quem e quando).
- **Testes:** `tests/test_trava.py` (4). Suíte na worktree: 183 passam.
- **Não validado em navegador** (só pela API com o cliente de teste do Flask).
- **Limite conhecido:** restaurar uma versão antiga (🕘 Versões) devolve também o estado de trava daquela versão.
