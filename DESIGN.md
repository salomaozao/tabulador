# DESIGN.md — Tabulador

> Documenta o sistema que já está em `static/app.css` (fonte da verdade dos valores). Atualizar aqui ao mudar um token.

## Cores (tokens em `:root`, com tema escuro por `prefers-color-scheme` e `data-theme`)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--surface` / `-2` / `-3` | #fcfcfb / #f1f0ee / #e6e4df | #1a1a19 / #242423 / #2f2f2d | fundo, painéis, hover |
| `--border` | #dedcd7 | #3a3937 | divisórias |
| `--text` / `-2` / `-3` | #0b0b0b / #52514e / #66645f | #fff / #c3c2b7 / #a09f98 | texto, secundário, terciário |
| `--accent` (fundo, texto branco por cima) | #1d62b8 | #2f6fca | botão primário, item ativo |
| `--accent-text` (cor de texto/link) | #1d62b8 | #79b0f2 | links e destaques; separado do `--accent` porque no escuro o fundo precisa ser escuro e o texto claro |
| `--ok` / `--warn` / `--danger` | #17693f / #8a5300 / #b00020 | #5fcf8f / #f2c46d / #ff7b8a | estados |
| `--human` | #4a3aa7 | #b3a9f5 | decisão humana (confirmado/corrigido) |
| `--cat-1..3` | #2a78d6 #eb6834 #1baf7a | variações | séries de gráfico |

## Tipografia
`14px/1.45`, token `--fonte`: `"Segoe UI Variable Text", "Segoe UI", "SF Pro Text", ui-sans-serif, sans-serif`. **Decisão (2026-10-06):** fonte do sistema escolhida de propósito, porque o app é local, a equipe usa Windows e não deve depender de rede/CDN; sem `system-ui`/Arial/Inter/Roboto genéricos. Títulos 15–22px, peso 600–700; texto auxiliar 12px.

## Espaçamento e forma
Base 4px (gaps 4/6/8/10/12/16); raios 4–8px; sidebar fixa de 280px; topo sticky.

## Componentes
`.btn` (+ `primary`, `ghost`, `sm`, `perigo`), `.pill` (estado), `.sq-stat` (indicador), `.u-barra` (gráfico em barras, focável), diálogos `<dialog>`, `.side li` (navegação), `.prog` (progresso).

## Regras
- Estado por **cor + texto/ícone**, nunca só cor.
- Destaque de status em cartão: borda completa tingida (não borda lateral grossa — anti-pattern); ponto/ícone para reforço.
- Foco: nunca `outline:none` sem substituto; usar `outline:2px solid var(--accent)` ou transparente (visível em alto contraste).
- Novos valores de cor só como token; ações perigosas em `--danger` e fora do fluxo principal.
- Ícones de navegação: SVG de traço 1,5px (`.nav-ic`, `currentColor`), não emoji.
- Caminhos técnicos (planilha-fonte) mostram só o nome do arquivo; o caminho completo fica no `title`.
- Gates (ambos devem sair com 0): `python <skills>/frontend-ai-stack/scripts/check_ui.py static --baseline .ui_baseline.json` e `python tools/check_contraste.py` (WCAG AA 4,5:1, claro e escuro).
