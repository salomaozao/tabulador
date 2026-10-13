---
id: OBJ-04
titulo: Transformar o Tabulador (e as ferramentas da Jumppi) num site único, acabando com a sincronização entre máquinas
area: tabulador
status: ativo
prioridade: alta
data_criacao: 2026-10-13
---

# OBJ-04: Tudo num site

### 1. Contexto e Dor Atual (JTBD - Problem Space)
- **Cenário / Gatilho:** hoje cada pessoa roda o Tabulador na própria máquina (`iniciar.bat` + venv local). Código, base e resultados chegam a cada um por OneDrive/SharePoint e Syncthing, e só a revisão vai para o Turso.
- **A Dor Real (palavras do Gabriel, 13/10/2026):** "a maior parte dos problemas vem vindo da sincronização entre todo mundo, problema com versionamento etc." Exemplos já vividos:
  - cópias do app espalhadas e divergentes: o SESI_cat tinha uma cópia inteira do programa, o `tabulador_equipe` era uma versão antiga e o `tabulador_design` era um repositório separado;
  - o mesmo projeto em 3 pastas com dados diferentes;
  - "última gravação vence" no Turso (DEC-03);
  - processo velho rodando código novo pela metade;
  - cada pessoa precisa da planilha, do `.env` e do Python instalados.
- **Impacto:** tempo perdido conciliando versões, risco de perder revisão humana e dificuldade de dizer qual versão produziu qual entrega.

### 2. Ganhos Esperados (JTBD - Value & Relief)
- **Uma versão só:** todo mundo abre um endereço e usa o mesmo código e os mesmos dados. Atualizar vira "publicar", sem copiar pasta.
- **Sem instalação:** usuário não programador não precisa de Python, venv, `.bat` nem chave no `.env`.
- **Concorrência de verdade:** o servidor arbitra as edições simultâneas, sem a regra "última gravação vence" por arquivo.
- **Rastreabilidade:** a versão em produção é sempre um commit conhecido (liga com o OBJ-03).

### 3. Critérios de Vitória (DoD de Alto Nível)
- [ ] O Tabulador roda num endereço web com login, e o projeto SESI funciona ponta a ponta (carregar base, classificar, revisar, exportar) sem nada instalado na máquina do usuário.
- [ ] Nenhuma pasta sincronizada é necessária para trabalhar: planilha-fonte por upload e resultados por download.
- [ ] Publicar uma versão nova é um passo só, e a tela mostra qual commit está no ar.
- [ ] Os outros projetos e ferramentas da Jumppi (ex.: dashboard do pesquisador) seguem o mesmo modelo.

### 4. Anti-Escopo / No-Gos (Shape Up - Limites Rígidos)
- ❌ **Não** reescrever a interface em React só por isso: o site pode começar com o Flask atual servido num servidor.
- ❌ **Não** subir dado de cliente para serviço sem decidir antes onde ficam os dados e quem acessa (LGPD e contrato).
- ❌ **Não** desligar o modo local antes de o site estar validado numa entrega real.

### 5. Rabbit Holes (Shape Up - Armadilhas Técnicas Conhecidas)
- ⚠️ **Estado em arquivos:** o app grava JSON em `output/perguntas/...`. No servidor, isso precisa virar banco (o Turso já cobre parte) ou um disco persistente único.
- ⚠️ **Chamadas longas de IA:** a classificação em lote leva minutos. O site precisa de fila ou de tarefa em segundo plano, e não pode depender de requisição aberta.
- ⚠️ **Provedor de IA por CLI local** (`llm_cli.py`) não existe no servidor. No site, só API.
- ⚠️ **Login:** hoje a identificação é o nome autodeclarado (PEND-09). Isso muda o anti-escopo do OBJ-03.

### 6. Validação dos Ganhos (Auditoria de Resultados)
- **Ganhos Obtidos vs Esperados:** [Preencher na conclusão].

> **Revisa o OBJ-03:** os itens "não criar servidor central" e "não criar login com senha" do anti-escopo do OBJ-03 deixam de valer como direção de longo prazo. Continuam valendo só até este objetivo ser planejado.
