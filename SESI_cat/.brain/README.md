# .brain — Memória compartilhada do projeto SESI (categorização)

Esta pasta guarda as regras, o histórico e as pendências do projeto **SESI Minas — Satisfação das Escolas** (categorização das perguntas abertas). Ela serve para pessoas e assistentes de IA (Claude Code, Antigravity/Gemini, Cursor) trabalharem sem perder contexto.

O código do app fica em `_laterais/categorizador`; aqui fica só o que é específico do SESI.

```text
.brain/
├── README.md          # este guia
├── dialogo_ias.md     # log cronológico, só acrescentar no fim
├── decisoes.md        # sumário gerado pelo sync
├── decisoes/          # DEC-XX, um arquivo por decisão (YAML frontmatter)
├── pendencias.md      # sumário gerado pelo sync
├── pendencias/        # PEND-XX, um arquivo por pendência (YAML frontmatter)
└── scripts/manage_brain.py
```

## Como usar
1. **Ao começar:** leia `decisoes.md`, `pendencias.md` e a última entrada de `dialogo_ias.md` (bloco "Próxima IA / Handoff").
2. **Ao terminar um bloco de trabalho:** acrescente uma entrada no fim de `dialogo_ias.md`.
3. **Depois de criar ou alterar uma decisão ou pendência:**
   ```bash
   python .brain/scripts/manage_brain.py sync
   python ../_general/scripts/coletar_eventos.py
   python ../_general/scripts/gerar_ics.py
   ```
4. **Para verificar a integridade:** `python .brain/scripts/manage_brain.py audit`.

Não coloque respostas de respondentes nem chaves de API nesta pasta: ela é versionada no git (veja DEC-02).
