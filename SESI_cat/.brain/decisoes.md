# Sumário Executivo de Decisões e Regras Vigentes

Este arquivo é o sumário central de decisões metodológicas e regras de negócio do projeto **SESI Minas — Categorização (Satisfação das Escolas)**. 

Para aprofundamento técnico, consulte os arquivos pontuados no diretório [`decisoes/`](decisoes).

---

## Tabela Resumo de Decisões

| ID | Título / Assunto | Módulo Afetado | Resumo Executivo | Detalhe |
| :--- | :--- | :--- | :--- | :---: |
| **[DEC-01](decisoes/01_categorizador_multiprojeto.md)** | **SESI roda no Categorizador multi-projeto (código em _laterais/categorizador)** | `projeto.py`, `categorizador` | SESI_cat guarda só a definição do projeto (projeto.py, formato plano) e o lançador; todo o código do app fica em _laterais/categorizador, compartilhado com a Assertiva. | [Abrir](decisoes/01_categorizador_multiprojeto.md) |
| **[DEC-02](decisoes/02_versionamento_e_dados.md)** | **Versionamento restrito e dados de cliente fora do git** | `git`, `data`, `output` | Git na raiz jumppi/ com .gitignore de lista de permissão (só _laterais/categorizador e SESI_cat). Nunca versionar .env, credenciais, SESI_cat/data nem output*; buscar chaves antes de cada commit. | [Abrir](decisoes/02_versionamento_e_dados.md) |
| **[DEC-03](decisoes/03_rid_estavel_e_nuvem.md)** | **Respostas identificadas pelo texto (rid estável) e revisão compartilhada na nuvem** | `tabulador`, `codeframe`, `coding`, `nuvem`, `supervisao` | O rid de cada resposta segue a chave do texto normalizado. Uma base nova preserva classificações e conferências, e as respostas novas ficam para classificar. A revisão (arquivos por pergunta) fica no Turso, compartilhada por todos; testes e modo teste nunca tocam no banco. Aceite automático só com confiança >= 0,85 (ajustável) e auditor (outra IA) concordando. | [Abrir](decisoes/03_rid_estavel_e_nuvem.md) |

---

## Como Adicionar ou Modificar Decisões
1. Crie ou edite o arquivo pontuado em `.brain/decisoes/XX_nome_descritivo.md` contendo o cabeçalho YAML frontmatter.
2. Registre a síntese na tabela acima ou execute:
   ```bash
   python .brain/scripts/manage_brain.py sync
   ```
