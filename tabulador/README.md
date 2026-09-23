# Tabulador de respostas abertas — categorização, codebook e cruzamentos

Programa único para vários projetos de pesquisa (hoje: **SESI Minas** e **Assertiva**). A IA propõe
as categorias e classifica as respostas; o pesquisador valida tudo pela interface até ficar bom.

## Para quem vai usar (sem programação)

1. Dê dois cliques em **`iniciar.bat`** (ou, no SESI, em `SESI_cat\Abrir Tabulador.bat`, que já
   abre no projeto certo).
   - Na primeira vez ele prepara o ambiente e baixa os pacotes (1 a 3 minutos). Se o Python não
     estiver instalado, ele oferece instalar.
   - O navegador abre sozinho em `http://127.0.0.1:5000`. Deixe a janela preta aberta enquanto usa;
     para encerrar, feche-a. Dar dois cliques de novo só reabre o navegador.
2. Na primeira vez, clique em **⚙ Configurar IA** e cole a chave da OpenAI (fica gravada só neste
   computador, em `.env`).
3. No **Painel geral**, clique em "Ler a planilha agora" (se pedir) e escolha uma pergunta.

### O loop de validação (por pergunta)

```
 instruções p/ IA ─► ✨ Gerar categorias ─► ajustar (editar / mesclar / "Pedir ajuste à IA") ─► ✓ Aprovar categorias
                                                                                                │
   ┌────────────────────────────────────────────────────────────────────────────────────────────┘
   ▼
 ✨ Classificar AMOSTRA (30–200) ─► conferir: ✓ confirmar · corrigir no menu · comentar p/ IA
   ▲                                     │
   │   taxa "a IA acertou X%" baixa? ────┤ ajuste instruções/categorias ─► ↻ Reclassificar tudo
   │                                     │ comentários ─► ✨ Reclassificar comentadas
   └── + Classificar mais ◄──────────────┘
                                         │ acerto bom
                                         ▼
                      Classificar as restantes ─► ✓ Aprovar ─► Painel: ⬇ planilha final / codebook / cruzamentos
```

- **✓ (confirmar)**: a IA acertou. Confirmadas e corrigidas ficam protegidas: a IA não mexe mais nelas.
- **Acerto da IA** = confirmadas ÷ (confirmadas + corrigidas depois da IA). Serve para decidir quando
  parar de testar e classificar o restante.
- **Mudar as categorias depois de classificar**: aprovar as categorias é uma etapa só, antes da primeira
  classificação. Depois disso, renomear, mesclar, excluir ou pedir ajuste à IA vale na hora e não trava
  a classificação. Mesclar e excluir movem as respostas (as excluídas vão para Outros). Uma definição
  nova vale para as próximas classificações; *Reclassificar tudo* refaz as que ainda não foram conferidas.
- **Pedir ajuste à IA** (categorias): escreva "junte X e Y", "crie categoria para Z"… A IA devolve a
  lista revisada mantendo os códigos do que não mudou; há botão para desfazer.
- **Comentário para a IA** (resposta): vira instrução obrigatória ao clicar em *Reclassificar comentadas*.
- O Excel de revisão e o relatório HTML continuam disponíveis em cada pergunta.

### 📦 Resultados (aba própria na barra lateral)

Números gerais (perguntas aprovadas, respostas classificadas, conferidas por pessoas, acerto da IA), os
arquivos para baixar (*↻ Atualizar todos*, *⬇ Baixar*, *📂 Abrir pasta*) e, para cada pergunta, o gráfico
de categorias (% de quem respondeu que citou cada uma). Só entram nos arquivos as perguntas **aprovadas**.

| Resultado | Arquivo (em `<pasta do projeto>/output/`) |
|---|---|
| Planilha final (SESI) | `base_processamento_categorizada.xlsx` — cópia da planilha-fonte com `Q*_CAT` = categoria principal, `Q*_CAT2` = secundária (no fim da aba) e aba `Categorias` |
| Codebook | `codebook/codebook.xlsx` (+ `.html`) |
| Cruzamentos | `cruzamentos/cruzamentos.xlsx` (uma aba por pergunta, % por banner) |
| Base processada | `base/base.xlsx` (códigos `<QID>_COD1/_COD2` e nomes) |

### Andamento das operações da IA

Gerar/ajustar categorias, classificar, aprovar e gerar resultados abrem uma janela de andamento com as
**etapas** (✓ feita, em andamento, a fazer), **barra de progresso**, tempo decorrido, **tempo restante**
estimado, velocidade (respostas/min), lote atual, chamadas à IA em andamento, tokens e um registro ao vivo
(ex.: "Lote 3 de 7 concluído"). Na classificação o progresso é real (respostas prontas); nas chamadas únicas
(gerar categorias) a estimativa vem da média das últimas chamadas do mesmo tipo (`progresso.py`).

### 🛠 Gerenciar projeto (zona de perigo)

Mostra as pastas do projeto, de resultados e a lixeira. Zona de perigo: apagar a classificação de uma
pergunta, apagar categorias + classificação de uma pergunta, recomeçar todas, e excluir o projeto da lista.
Cada ação pede para **digitar** uma palavra de confirmação. Nada é apagado de verdade: os arquivos vão para
`<saída>/_lixeira/<data>_<o quê>/`; excluir o projeto nunca apaga a pasta do projeto nem a planilha (os
resultados, se marcado, viram `<saída>_excluido_<data>`). No modo teste, só os dados de teste são afetados.

### Revisão pelo teclado

Clique numa linha da tabela de classificação e use: <kbd>↑</kbd>/<kbd>↓</kbd> navegar · <kbd>Enter</kbd>
confirmar ✓ e ir para a próxima · <kbd>C</kbd> escrever comentário (<kbd>Esc</kbd> volta para a tabela) ·
<kbd>1</kbd>–<kbd>9</kbd> trocar a categoria principal pelo código. As conferidas ficam sempre no fim da
tabela: ao confirmar ✓, a linha vai para o fim e a seguinte sobe para o lugar dela, então dá para
confirmar em sequência sem mexer o mouse. Corrigir não tira a linha do lugar (para ainda dar para
ajustar a secundária). Respostas longas mostram 5 linhas (clique para ver tudo).

### 🧪 Modo teste (sem IA)

Botão **🧪 Modo teste** no topo: a IA é trocada por valores **simulados** (`simulador.py`), sem internet,
chave ou custo — para validar telas e fluxo. Os resultados vão para `<pasta de saída>_teste`
(ex.: `SESI_cat/output_teste`), nunca misturados com os reais; na primeira vez a base já lida é copiada.
Faixa amarela no topo com **Apagar dados de teste** e **Sair do modo teste** (volta ao provedor anterior).

### Sempre a versão atual

Dar dois cliques com o Tabulador já aberto reaproveita a janela se for a mesma versão; se for uma
versão **antiga** (ex.: o programa foi atualizado), ela é fechada e a atual é aberta. Com a página aberta
durante uma atualização, aparece o aviso "O programa foi atualizado — Recarregar a página".

### Versionamento

Repositório privado: https://github.com/salomaozao/tabulador (raiz = pasta `jumppi`, com
`.gitignore` que versiona só `tabulador/` e `SESI_cat/`). **Nunca** vão para o git: `.env`
(chaves), `SESI_cat/data/` (dados do cliente) e pastas `output*` (respostas e resultados). A tag
`v0-base-antes-melhorias` marca a versão anterior às melhorias de usabilidade.

### IA: provedores e consumo

- **⚙ Configurar IA** → *Provedor*: OpenAI, **Google Gemini** (AI Studio, plano gratuito), **Groq**
  (Llama 3.3, gratuito), OpenRouter (modelos `:free` e pagos), DeepSeek ou *Personalizado* (qualquer
  API compatível com a OpenAI). O modal preenche endereço e modelo, mostra o link para obter a chave e
  tem **Testar conexão**. Cada provedor guarda a sua chave; trocar de provedor reaproveita a última.
- Se o provedor não aceitar JSON Schema estrito, o `llm.py` tenta `json_object` e depois texto livre,
  extraindo o JSON (inclusive de blocos ```json```). Erros comuns (sem créditos, chave inválida,
  limite por minuto, modelo inexistente) aparecem em português.
- **📈 Consumo da IA** (barra lateral): chamadas e taxa de sucesso, tokens de entrada/saída, tempo e
  custo **estimado** em US$ e R$, por modelo, por pergunta/operação e as últimas chamadas. Lê
  `output/llm_log/` do projeto ativo. Preços de referência em `usage.py` (`PRECOS`); câmbio em
  `TABULADOR_USD_BRL` (padrão 5,40).
- Planos gratuitos têm limite de chamadas por minuto: se aparecer erro de limite, reduza
  `TABULADOR_PARALELO` (ex.: 1 ou 2) no `.env`.
- **💻 Programa instalado no computador** (`llm_cli.py`): em ⚙ Configurar IA, os provedores *Claude Code*,
  *Codex* e *Gemini CLI* usam o programa já instalado e logado no computador, sem chave de API. Cada chamada
  abre o programa sem ferramentas (não lê nem grava arquivos), numa pasta temporária, com saída JSON.
  É mais lento que a API (cerca de 5 a 10 s por chamada) e roda no máximo 2 chamadas ao mesmo tempo. O
  Claude Code está testado; o Codex e o Gemini CLI seguem a documentação desses programas e ainda não
  foram testados. Os que não estão instalados aparecem desabilitados.

### Novo projeto

Botão **+ Novo projeto** no topo. O assistente tem 5 passos:

1. Escolher a planilha, que é copiada para a pasta do projeto.
2. Conferir as colunas. O rascunho é montado **sem IA**, a partir dos dados: tipos, opções copiadas
   literalmente, dados pessoais, quem recebeu cada aberta e o que categorizar pela cor do `_CAT`.
3. Escrever o contexto para a IA. O botão ✨ sugere o contexto, os rótulos e as instruções.
4. Conferir o pedido: quem confirmou e quais abertas foram pedidas.
5. **Validar** (roda a leitura real da planilha) e **Criar**.

O projeto fica num `projeto.json`, descrito em [novo_projeto/FORMATO.md](novo_projeto/FORMATO.md). Os
mesmos passos funcionam pelo terminal (`python -m novo_projeto.cli ...`) e pela skill de IA
[.claude/skills/novo-projeto](.claude/skills/novo-projeto/SKILL.md), que o `AGENTS.md` indica para Codex
e Antigravity.

## Projetos

Cada projeto é uma pasta com um `projeto.py` ou um `projeto.json` (criado pelo assistente); a lista fica em `projetos.json` (caminhos relativos a
esta pasta). O projeto ativo é escolhido no topo da interface (ou `TABULADOR_PROJETO=sesi`, ou
`python run.py --projeto sesi ...`).

| Projeto | Definição | Planilha-fonte | Saídas |
|---|---|---|---|
| `sesi` | `../SESI_cat/projeto.py` | `SESI_cat/data/base_processamento.xlsx` (formato "plano": 1 cabeçalho, 1 coluna por pergunta) | `SESI_cat/output/` |
| `assertiva` | `projetos/assertiva/projeto.py` | SurveyMonkey de cabeçalho duplo (2 abas), via `Shortcuts/...` | `output/` (desta pasta, como antes) |

O `projeto.py` define: `NOME`, `CLIENTE`, `CONTEXTO_PROJETO` (texto para a IA), `FONTE_XLSX`, `FORMATO`
(`"plano"` ou `"surveymonkey"`), `PERGUNTAS` (com `"codificar": True` e `"instrucoes_frame"` nas
abertas), `FILTROS`/`FILTROS_DESCRICAO` (quem recebeu cada pergunta), `DERIVADAS` e `BANNERS_PADRAO`
(cruzamentos) e, opcionalmente, `BACKCODING`, `PII_MATCH`, `PLANO`, `SAIDA_PLANILHA`. Para um projeto
novo no formato plano, use o assistente **+ Novo projeto** (ou a skill / `python -m novo_projeto.cli`), que gera
e valida um `projeto.json`. O formato SurveyMonkey continua sendo configurado à mão em `projeto.py`.

Dados pessoais (`PII_MATCH` / colunas não declaradas) nunca entram na base, nos prompts nem nas saídas
— exceto a *planilha final*, que é uma cópia da planilha-fonte do próprio cliente.

## Linha de comando (opcional)

```bash
python run.py --projeto sesi load                 # lê a planilha -> output/base/
python run.py --projeto sesi frame Q4 induzir     # IA propõe o frame
python run.py --projeto sesi frame Q4 aprovar
python run.py --projeto sesi code Q4              # classifica tudo + revisao.xlsx + relatorio.html
python run.py --projeto sesi code Q4 importar     # aplica correções do revisao.xlsx
python run.py --projeto sesi code Q4 aprovar      # trava e grava na base
python run.py --projeto sesi exportar             # planilha final categorizada
python run.py --projeto sesi codebook | crosstabs | status | report all
python run.py --projeto assertiva all [--auto]    # fluxo completo da Assertiva (para nos pontos de aprovação)
```

Demais comandos de frame (`mostrar`, `renomear`, `fundir`, `adicionar`, `remover`) no topo de `run.py`.

Testes (não chamam a OpenAI; escrevem em pasta temporária): `python -m unittest discover -s tests -v`
(os da Assertiva são pulados se a planilha-fonte não estiver acessível).

## Estrutura

| Arquivo | Papel |
|---|---|
| `projetos.py` / `projetos.json` | lista de projetos e ativação (aponta `config.*` e `variables.*` para o projeto) |
| `config.py` | caminhos do projeto ativo, chave/modelo da OpenAI (`.env`), lote e paralelismo da IA |
| `variables.py` | repassa o mapa de variáveis do projeto ativo + utilitários (`norm`, `por_id`...) |
| `load.py` | leitura da planilha (SurveyMonkey de cabeçalho duplo **ou** plana), expurgo de PII, bases, banners |
| `codeframe.py` | respostas únicas + NS/NR, indução do frame, edição, **refino pela IA com feedback**, aprovação |
| `coding.py` | classificação (amostra / restantes / tudo, em paralelo), confirmação, correções, taxa de acerto, aplicação na base |
| `exportar.py` | planilha final no formato da planilha-fonte |
| `report.py`, `codebook.py`, `crosstabs.py` | relatório de conferência, codebook, cruzamentos |
| `llm.py` | OpenAI com JSON Schema estrito; log de cada chamada em `output/llm_log/` |
| `llm_cli.py` | IA pelo programa instalado no computador (Claude Code, Codex, Gemini CLI) |
| `novo_projeto/` | criação de projetos: perfil da planilha, rascunho sem IA, validador, registro, assistente e CLI |
| `app.py` + `templates/` + `static/` | interface web (Flask + JS puro, sem build) |
| `iniciar.bat` | instalador/lançador (ambiente em `%LOCALAPPDATA%\Tabulador\venv`) |

Variáveis de ambiente úteis: `OPENAI_MODEL` (padrão `gpt-4.1`), `TABULADOR_PARALELO` (chamadas
simultâneas, padrão 4), `ASSERTIVA_LOTE` (respostas por chamada, padrão 30), `TABULADOR_MAX_INDUCAO`
(máx. de respostas únicas lidas ao propor categorias, padrão 1500 — acima disso usa amostra),
`TABULADOR_PORTA` (padrão 5000).

**Futuro:** front-end em React com build pronto embutido (o usuário final continuaria sem precisar de Node).
