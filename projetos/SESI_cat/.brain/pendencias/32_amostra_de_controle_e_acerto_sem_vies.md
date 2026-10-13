---
id: PEND-32
titulo: Amostra de controle aleatória - medir o erro real das automáticas e corrigir o viés do "a IA acertou X%"
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/supervisao.py, src/coding.py, static/app.js]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Lacuna metodológica achada na revisão do plano (01/10). (1) O 'a IA acertou X%' é calculado só sobre o que humanos conferiram, e humanos conferem de preferência o que a IA marcou como duvidoso (baixa confiança, auditor discordou): é uma amostra viciada, e o número não representa a base. (2) As que 'passaram pelo auditor' nunca são conferidas, então não há medida do erro delas; dois modelos podem errar juntos. Ação: sortear uma amostra de controle aleatória (ex.: 5%, mínimo 30 por pergunta, estratificada por categoria) dentro das automáticas, conferida às cegas, e reportar o erro estimado com intervalo de confiança por pergunta."
---

# PEND-32: Amostra de controle

- **Sorteio:**
  - por pergunta, entre as respostas aceitas automaticamente ou que passaram pelo auditor;
  - estratificado pelas categorias principais, com semente fixa registrada (reprodutível);
  - o tamanho é configurável no `config.py`, sem limiar do SESI no núcleo (anti-escopo do OBJ-02).
- **Conferência às cegas:**
  - a fila "Controle de qualidade" não mostra a categoria da IA antes de a pessoa escolher, ou mostra só depois, para evitar viés de ancoragem;
  - decidir com o Gabriel se o cego é viável no ritmo da equipe.
- **Métricas:**
  - erro das automáticas, com IC 95% (Wilson);
  - acerto da IA **na amostra aleatória**, que passa a ser o número exibido;
  - o atual vira "acerto nas conferidas", com a ressalva.
- **Bônus (confiabilidade entre codificadores):** uma parte da amostra conferida por duas pessoas (ex.: Sara e João) dá a concordância humano × humano (kappa). É o teto realista para a IA e um número defensável no relatório metodológico do cliente.
- **Alimenta:** a PEND-23 (mostrar a taxa de erro de quem passou pelo auditor), o OBJ-02 §3 e a PEND-30 (comparar modelos com um gabarito sem viés).
- **Plano de implementação (01/10, revisado):** ciclo `ciclos/2026-10-01_amostra_controle` (PRD, ARCH e TASKS v1.1), com a fase em PRD aguardando aprovação.
  - O Gabriel vetou a amostra fixa por pergunta: "não queremos parar o processo de categorização para estimar o erro".
  - Virou **controle contínuo e esporádico**:
    - pílula `🎯 Controle · 5 (~2 min)` no topo;
    - pacotes de 5 sorteados na hora, do projeto inteiro, conferidos às cegas;
    - o erro acumula por pergunta e no projeto (com cobertura);
    - aparece no painel geral e na revbar;
    - na aprovação, só informa, nunca bloqueia.
  - O kappa entre humanos ficou para a v2.
- **Substitui** a seção "Sorteio" acima: o sorteio estratificado e a semente por pergunta foram trocados pelo sorteio uniforme no projeto (ver ARCH §2).
