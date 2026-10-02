---
id: PEND-42
titulo: Congelar uma resposta (nem a conferir, nem confirmada, categoria travada)
objetivo_relacionado: OBJ-01
modulo_afetado: [tabulador, src/coding.py, src/supervisao.py, app.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-02
resumo: "Redesenhada em 02/10 após a validação do Gabriel: a trava NÃO é por pergunta, é por RESPOSTA. Ele vê uma resposta que não quer confirmar nem mexer agora, para voltar a ela mais tarde: ela não fica a conferir nem confirmada, e a categoria fica congelada. Implementado na branch feat/congelar-resposta (worktrees/tabulador-congelar), aguardando validação e merge. Substitui a trava por pergunta que havia entrado na main (merge c00fcdd)."
---

# PEND-42: Congelar uma resposta

- **Decisão do Gabriel (02/10):** a primeira versão (trava por pergunta, `confirmacao_travada`) estava errada. Ele quer **congelar uma resposta individual**: "não fica nem pendente nem confirmada; a categoria individual fica bloqueada, congelada", para mexer nela mais para a frente.
- **Estado novo:** `item.congelada = {por, em}` em `codificacao.json`; `situacao_revisao` devolve `"congelada"`. Fica fora de a conferir, de confirmadas e de corrigidas; continua contando como classificada. `resumo_revisao` expõe `n_congeladas`.
- **Só congela o que ainda não foi decidido:** pendente ou a reconferir. Confirmada ou corrigida: recusa ("desfaça a confirmação antes"). Descongelar devolve a resposta a pendente (ou a reconferir, se era 'alterada').
- **Fica de fora de tudo:** `atualizar_item` (categoria, secundária, comentário, ✓) recusa com `RespostaCongelada`; `validar` em bloco, `auto_aceitar`, `auditar`, `codificar`/`recodificar` (inclusive "Reclassificar tudo") e `importar_revisao` pulam a congelada. Uma mudança estrutural no quadro (fundir/excluir categoria) ainda remapeia o código dela, para não ficar uma categoria que não existe mais.
- **Aprovar a pergunta continua permitido** com congeladas, com aviso no diálogo ("saem com a categoria da IA, sem conferência"); o manifesto da entrega registra `n_congeladas`.
- **Tela:** botão ❄ ao lado do ✓ em cada resposta (tecla **F** com a linha focada); linha com faixa azul e "❄ congelada"; menus e comentário desabilitados; vai para o fim da tabela; pílula "❄ N congeladas" na barra fixa (clicável, filtra); opção "❄ congeladas" no filtro de situação; "a conferir" e "Confirmar as N mostradas" não contam as congeladas.
- **Removido (sem código fantasma):** `definir_trava`, `ConfirmacaoTravada`, `POST /trava`, a caixa "Travar confirmações", `auto_bloqueado` e `tests/test_trava.py`.
- **Log:** eventos `congelar` e `descongelar` (quem, quando, qual resposta).
- **Testes:** `tests/test_congelar.py` (7). Suíte na worktree: 191 passam.
- **Verificado em navegador (instância isolada, sem nuvem):** botão ❄ por linha, congelar pela tela, faixa e situação, menus desabilitados, pílula e contagem "5 a conferir", filtro, "Confirmar as N mostradas" pulando a congelada (5 confirmadas, 1 congelada), recusa da API ao mudar categoria. **Não verificado no navegador:** descongelar pelo botão/tecla F (a extensão do navegador perdeu a aba nessa hora); o descongelar foi conferido pela API.
