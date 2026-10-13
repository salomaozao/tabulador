# Biblioteca de skills do Tabulador

Instruções para qualquer IA (Claude Code, Codex, Antigravity, Gemini) ajudar na categorização de respostas
abertas seguindo o mesmo processo. Cada skill nasceu de um prompt que o programa já usa ou de uma lição
de projeto real. As skills que citam números vêm do SESI Minas (23/09/2026).

| Skill | Para quê | Vem de |
|---|---|---|
| [`novo-projeto`](novo-projeto/SKILL.md) | criar o `projeto.json` de uma pesquisa nova | `novo_projeto/` |
| [`supervisionar-categorizacao`](supervisionar-categorizacao/SKILL.md) | rodar tudo, aceitar sozinho o que tem alta confiança e deixar a fila para o pesquisador | `supervisor.py` + sessão SESI |
| [`desenhar-quadro-categorias`](desenhar-quadro-categorias/SKILL.md) | propor e revisar o quadro de categorias | `codeframe._prompt_inducao` / `refinar` + auditoria SESI |
| [`classificar-respostas`](classificar-respostas/SKILL.md) | classificar contra o quadro fechado | `coding._prompt` |
| [`auditar-categorizacao`](auditar-categorizacao/SKILL.md) | segundo codificador: concordar ou sugerir | `supervisor.py auditar` + sessão SESI |
| [`diagnosticar-ia`](diagnosticar-ia/SKILL.md) | chaves, cotas e escolha de provedor | `config.py`, `llm.py`, `llm_cli.py` |

## Como manter

- Mudou um prompt no código (`coding._prompt`, `codeframe._prompt_inducao`, `codeframe.refinar`)? Atualize a skill correspondente no mesmo commit.
- Aprendeu algo num projeto (um erro recorrente da IA, um buraco no quadro, um limite de provedor)? Registre na
  skill certa com a data e o projeto, em uma ou duas linhas, sem dados pessoais de respondentes.
- As skills não levam respostas de respondentes além de exemplos curtos e anônimos.
