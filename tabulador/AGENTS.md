# Instruções para agentes de IA (Codex, Antigravity, Gemini, Claude Code)

Este é o Tabulador de respostas abertas: uma aplicação Flask com JS puro que atende vários projetos. A visão geral está em `README.md`.

## Criar um projeto novo

Siga **exatamente** o processo de `.claude/skills/novo-projeto/SKILL.md`. É o mesmo arquivo que o Claude Code usa como skill. Resumo das etapas:

1. rodar o perfil;
2. fazer as perguntas obrigatórias à pessoa;
3. gerar o rascunho sem IA;
4. completar apenas os campos permitidos;
5. validar até não haver erro;
6. registrar.

Não escreva um `projeto.json` ou `projeto.py` do zero e não pule o validador (`python -m novo_projeto.cli validar <pasta>`).

## Biblioteca de skills (`.claude/skills/`)

Cada pasta tem um `SKILL.md`: o Claude Code carrega sozinho; Codex, Antigravity e Gemini devem **ler o
arquivo inteiro antes** de fazer a tarefa correspondente. O índice fica em `.claude/skills/README.md`.

| Tarefa | Skill |
|---|---|
| Criar projeto novo | `novo-projeto` |
| Categorizar tudo / supervisionar a IA / "matar o que tem alta confiança" | `supervisionar-categorizacao` |
| Criar ou revisar o quadro de categorias | `desenhar-quadro-categorias` |
| Classificar respostas (regras do prompt do programa) | `classificar-respostas` |
| Conferir ou auditar a classificação (segundo codificador) | `auditar-categorizacao` |
| A IA não responde, chave, cota, escolha de provedor | `diagnosticar-ia` |

## Regras gerais

- Nunca versione `.env`, `SESI_cat/data` ou pastas `output*`, porque contêm dados de clientes.
- As opções de resposta (`niveis`) são copiadas literalmente da planilha. Nunca as redigite.
- Testes: `python -m unittest discover -s tests -v`. Eles gravam em pastas temporárias.
