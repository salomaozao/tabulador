# SESI Minas — categorização das perguntas abertas

**Para usar:** dê dois cliques em `Abrir Tabulador.bat`. Ele abre o Tabulador no projeto SESI.
Na primeira vez, o programa instala o que precisa (1–3 min) e pede a chave da OpenAI (botão **⚙ Configurar IA**).

Esta pasta guarda **só o material do projeto**: base, gravações, conversas, documentos e a memória
das IAs (`.brain/`). Não existe cópia do programa aqui. O código do Tabulador fica num lugar só,
`projetos/_laterais/tabulador/`, e o projeto SESI que ele usa (configuração, base e resultados) fica em
`projetos/_laterais/tabulador/projetos/sesi_cat/`:

- `src/projeto.py`: perguntas abertas (Q2, Q4, Q5, Q29, Q30, Q32, Q33, Q35), instruções fixas
  para a IA, filtros e banners dos cruzamentos
- `data/`: a planilha-fonte, que o programa não altera
- `output/`: tudo o que o programa gera. A entrega principal é
  `output/base_processamento_categorizada.xlsx`

Em 13/10/2026 a cópia antiga do programa que ficava nesta pasta foi para
`_general/quarentena_2026-10-13/` (com manifesto SHA-256). As pastas `data/` e `output/` daqui
foram mantidas como estavam.

## Pasta da Equipe (SharePoint)
- `_sharepoint/`: junção NTFS apontando diretamente para a pasta corporativa da empresa no SharePoint
  (`Shortcuts/Projetos - Tabulador`). Permite leitura e escrita instantânea pela IA no Orca sem duplicar espaço em disco.

