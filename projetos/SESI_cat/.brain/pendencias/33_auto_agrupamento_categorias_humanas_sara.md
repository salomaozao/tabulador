---
id: PEND-33
titulo: (Ideia futura) Auto-agrupamento inteligente de categorias criadas por humano (metodologia Sara)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/aprendizado.py, src/codeframe.py, static/app.js]
criticidade: baixa
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Ideia guardada para amadurecimento (pensamento registrado): a metodologia de codificação humana (ex.: Sara na Q29) cria micro-categorias granulares de altíssima riqueza semântica, mas com volumetria baixa (< 1%). A auto-melhora do tabulador deve usar essa riqueza para propor fusões e agrupamentos inteligentes sem perda semântica (sintetizando definições e unindo keywords/exemplos), apresentando propostas no modal de Saúde com prévia e aprovação em 1 clique."
linear: JUM-20
---

# PEND-33: Auto-Agrupamento Inteligente de Categorias Humanas (Metodologia Sara)

## 1. Motivação e Racional (Pensamento Guardado)
- **O Fenômeno Humano:** Quando a Sara (ou qualquer pesquisador sênior) categoriza ou revisa perguntas abertas densas (como a `Q29`), ela cria novas categorias específicas para capturar nuances reais do campo (ex.: "Ensino Técnico", "Alunos atípicos e inclusão", "Aulas de reforço").
- **A Riqueza Semântica:** Essas categorias não são ruído — são ouro analítico. Trazem vocabulário autêntico e distinções reais que a indução genérica da IA não percebeu.
- **O Desafio Estatístico:** O excesso de granularidade gera muitas categorias com frequência minúscula ($< 1\%$ ou $< 0.5\%$), sobrecarregando relatórios executivos.
- **A Solução Futura (Auto-Melhora do Tabulador):** A IA lê as respostas e as categorias manuais, identifica clusters de afinidade semântica e propõe a fusão inteligente.
  - **Fusão sem Perda (Lossless Merge):** A definição consolidada sintetiza os subtemas; keywords de lift e exemplos literais de cada micro-categoria são herdados e integrados.
  - **Decisão Humana:** Conforme a Regra de Ouro do OBJ-02, a IA nunca altera a taxonomia sozinha. Ela gera um card de proposta no modal de *Saúde do Quadro* com prévia do antes/depois, e o pesquisador aprova com 1 clique.

## 2. Esboço Técnico para Futura Implementação
1. **Detecção:** `aprendizado.propostas_agrupamento_de(frame, dossie)` cruza categorias com $N < 2\%$ e termos compartilhados de alto lift.
2. **Síntese LLM:** Prompt estruturado que gera nome de macro-tema e definição sintetizada a partir das micro-categorias candidatas.
3. **Card na Saúde do Quadro:** Exibe o grupo sugerido, novo volume somado ($N$ e $\%$), nova definição e botão `[✓ Aprovar Agrupamento]`.
4. **Execução:** Aciona `CF.fundir(qid, destino, *origens)` com snapshot de proteção prévio e remapeamento transparente das respostas em `codificacao.json`.

## 3. Diretriz Operacional
- **Status:** Pensamento guardado para evolução futura da arquitetura. Não implementar agora.
