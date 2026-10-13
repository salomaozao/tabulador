---
id: PRD_2026-10-01_amostra_controle
ciclo: 2026-10-01_amostra_controle
data_criacao: 2026-10-01
data_revisao: 2026-10-01
autor: Product Manager (Claude Opus 5.5)
objetivo_relacionado: OBJ-02
pendencia: PEND-32
status: draft
---

# PRD: Controle de qualidade contínuo (erro real do que vai ao cliente sem conferência humana)

> **Revisão 01/10, a pedido do Gabriel:** "não queremos parar o processo de categorização para estimar o erro; precisamos de um lugar para isso que o usuário faça esporadicamente". A versão anterior previa uma amostra fixa de 40 por pergunta, conferida de uma vez, e foi substituída por **pacotes pequenos, opcionais e sorteados na hora**. O erro estimado vai se acumulando com o tempo.

## 1. Contexto & Dor de Negócio (Problem Statement)
- **Problema:**
  - O único número de qualidade da tela, "a IA acertou X%" (`coding.resumo_revisao → acerto_ia`), é calculado sobre o que humanos conferiram, e eles conferem de preferência as respostas duvidosas. É uma **amostra viciada**.
  - Ao aprovar, tudo o que não foi conferido vai ao cliente como a IA classificou: as aceitas automaticamente ("passaram pelo auditor") e as "a conferir" que ninguém abriu. Essa parte **não tem medida de erro**.
- **Restrição de operação:** a medição **não pode interromper** a categorização. Ela precisa caber em momentos soltos do dia (2 min) e nunca ser obrigatória.
- **Impacto se nada for feito:**
  - não sabemos se entregamos 2% ou 15% de erro;
  - o limiar de auto-aceite é escolhido no escuro;
  - não há número defensável para a nota metodológica ao cliente.
- **Ganhos Esperados:**
  - erro estimado, com intervalo, por pergunta e no projeto, que vai ficando mais preciso sozinho;
  - custo diluído (≈ 5 respostas por pessoa por dia);
  - a calibração do limiar passa a ter evidência.

## 2. Personas
- **Sara / João (revisores):** conferem quando têm uma brecha. Precisam de algo curto, de teclado, que não os influencie e que possa ser largado no meio.
- **Gabriel (coordenador):** decide quando aprovar, qual limiar usar e o que dizer ao cliente.
- **Cliente (Jucimara / SESI):** recebe a base e a nota metodológica.

## 3. User Stories & Requisitos Funcionais
- **US-01 (pacote esporádico):** Como revisora, quero um atalho sempre visível, `🎯 Controle · 5 respostas (~2 min)`, que abra um **pacote de 5 respostas sorteadas do projeto inteiro**, para contribuir com o controle quando eu tiver uma brecha, sem sair do que estou fazendo.
  - **Lugar:** pílula fixa no topo do app, ao lado do status da IA. Ela aparece só quando há projeto com classificação.
  - **Sorteio:** feito **na hora do clique**, uniforme entre todas as respostas do projeto que iriam ao cliente sem olho humano. Entram as aceitas automaticamente e as "a conferir" classificadas pela IA. Ficam fora as decisões humanas, NS/NR por regra e as respostas com erro de IA.
  - **Nunca obrigatório:** fechar a janela no meio não perde nada, porque cada conferência é gravada na hora. A pílula não pisca, não insiste e não bloqueia nada.
- **US-02 (conferir às cegas):** Como revisora, quero ver **só o texto** e escolher a categoria antes de ver a da IA, para não ser influenciada.
  - Atalhos: 1-9 e letras para categoria, `S` para secundária, `P` para pular, `Enter` para confirmar.
  - Depois da escolha: "A IA disse X". Se for diferente: `Manter a minha (Y)` / `A IA está certa`.
  - Como o pacote mistura perguntas, cada cartão mostra o enunciado e a lista de categorias daquela pergunta.
- **US-03 (nada se perde):** Cada conferência confirma ou corrige a resposta **na base**, pelo mesmo caminho da tabela. Assim, o controle também é revisão de verdade.
- **US-04 (ver o resultado sem procurar):** Como coordenador, quero ver no **painel geral do projeto** um bloco "Controle de qualidade" com:
  - erro estimado do projeto e de cada pergunta, sempre como ponto + intervalo;
  - quantas conferências cada pergunta tem;
  - a quebra automáticas × a conferir.
  - Uma pergunta com menos conferências que o mínimo para destaque (padrão 30) aparece como "ainda pouco medido (8 de ~30)", **sem** número em destaque.
  - O antigo "a IA acertou X%" passa a se chamar "**acerto nas que vocês conferiram**", com o aviso de que não representa a base.
- **US-05 (na hora de aprovar, sem bloquear):** Como coordenador, ao clicar "Aprovar e gravar nos resultados" numa pergunta, quero que a confirmação **mostre** o erro estimado dela. Se ela tiver poucas conferências, a confirmação oferece `Conferir 5 desta pergunta agora` ou `Aprovar assim mesmo`. Aprovar nunca é impedido.
- **US-06 (calibrar):** Quando o erro das **automáticas** passar de um teto configurável (padrão 5%) com intervalo que já exclui o teto, quero o aviso "o auto-aceite está deixando passar erro: considere subir o limiar ou trocar o auditor". É **só um aviso**: o limiar não muda sozinho.
- **US-07 (entrega):** O relatório da pergunta (`/relatorio/<qid>`) traz a linha metodológica com o erro estimado, o nº de conferências e o período.

## 4. Requisitos Não-Funcionais
- **Zero interrupção:** nenhuma tela, ação ou aprovação depende do controle. Nada aparece sozinho (sem pop-up, sem lembrete).
- **Reprodutibilidade:** cada pacote registra semente, horário, quem pediu, o tamanho da população no momento e os rids sorteados.
- **Persistência:** `controle.json` por pergunta, gravado por `CF._gravar` (local e nuvem), separado de `codificacao.json` (risco de gravação simultânea, PEND-31).
- **Desempenho:** sortear um pacote ou calcular as estimativas do projeto em menos de 300 ms, sem chamada à IA.
- **Estatística:** detalhada no `02_ARCH.md`.
  - por pergunta: Wilson 95% sobre todas as conferências acumuladas;
  - projeto: combinação ponderada pelo tamanho atual de cada pergunta;
  - a cobertura (quanto da população tem medida) aparece junto.

## 5. Anti-Escopo & No-Gos (Limites Rígidos)
- 🚫 **Não** interromper, lembrar, cobrar ou bloquear ninguém por causa do controle (nem na aprovação).
- 🚫 **Não** criar amostra fixa por pergunta nem meta obrigatória de conferências.
- 🚫 **Não** mudar o formato de `base_processamento_categorizada.xlsx` (OBJ-02).
- 🚫 **Não** mudar o limiar de auto-aceite automaticamente.
- 🚫 **Não** fixar números do SESI no núcleo: tamanho do pacote, mínimo para destaque e teto de erro ficam em `config.py`.
- 🚫 **Não** fazer dupla codificação / kappa entre humanos nesta versão (v2 da PEND-32).
- 🚫 **Não** chamar IA neste ciclo.

## 6. Rabbit Holes
- ⚠️ **População que muda com o tempo:** conferências antigas descrevem a base de quando foram feitas. Depois de uma reclassificação grande ou de uma troca de modelo, o número mistura épocas.
  - Mitigação v1: mostrar o período ("conferências de 01/10 a 09/10").
  - Mitigação v1: marcar "medida anterior à mudança do quadro" quando a maioria das conferências tiver `frame_versao` anterior à atual.
  - Não tentar corrigir isso estatisticamente na v1.
- ⚠️ **Duas pessoas sorteando ao mesmo tempo** podem pegar a mesma resposta. Na gravação, se a resposta já foi conferida por outra pessoa, o cartão é trocado por outro sorteio, sem erro na tela.
- ⚠️ **Pacote só de uma pergunta (US-05):** ele não segue a mesma regra de sorteio do projeto. Para a estimativa por pergunta, isso não importa. Para a do projeto, a combinação é feita por pergunta, ponderada (ver ARCH), justamente para que isso não distorça.
- ⚠️ **O que é erro:** v1 = **primária** diferente. Diferença só na secundária = "erro parcial", mostrado à parte (decisão do Gabriel pendente).
- ⚠️ **Poucas conferências:** o intervalo é largo, e a tela nunca mostra o ponto sozinho.

## 7. Critérios de Aceite
- [ ] Com a categorização em andamento numa aba, abrir e fechar um pacote em outra não altera filtros, rolagem nem a operação em curso.
- [ ] O sorteio nunca traz resposta conferida por humano, NS/NR por regra ou com erro de IA; a mesma semente dá os mesmos rids.
- [ ] Na janela, a categoria da IA **não está no DOM** antes da escolha.
- [ ] Concordar → item `validado_por=humano`; discordar → `origem=humano` com `corrigido_de`; `controle.json` guarda `{escolha_cega, final, ia, cego, pacote, por, em}`.
- [ ] Com 3 erros em 40 conferências numa pergunta: "7,5% (2,6-19,9%)".
- [ ] A confirmação de aprovação mostra o erro estimado, e aprovar funciona com zero conferências.
- [ ] Nenhum "a IA acertou" sobra na UI; a suíte de testes não tem falhas novas; `node --check static/app.js` passa.
