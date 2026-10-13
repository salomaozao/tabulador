---
id: PEND-21
titulo: Aprendizado do quadro, etapa 3 (propostas de separar/mesclar/criar com evidência e prévia; resolve o "separe Qualidade do Ensino" da Sara)
objetivo_relacionado: OBJ-02
modulo_afetado: [tabulador, src/codeframe.py, src/aprendizado.py, static/app.js]
criticidade: media
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-09-30
resumo: "Transformar os alertas da caixa 'Saúde do quadro' (PEND-18) em cards com proposta concreta: separar X em Y+Z (com quantas e quais respostas iriam para cada lado), mesclar (via fundir, inclusive em 97/98), criar a partir de Outros e renomear. Tudo com clique humano. O 'Pedir ajuste à IA' livre passa a mostrar a prévia (diff + respostas afetadas) antes de aplicar. Causa do 'não aconteceu nada' da Sara: refinar() mantém o código antigo na categoria dividida, então nenhuma resposta muda de lugar e nada é reclassificado."
---

# PEND-21: Propostas estruturais com prévia

- **Split aceito:**
  - cria as categorias novas;
  - reclassifica **só** as respostas não conferidas da categoria dividida;
  - as conferidas por humano voltam para "a conferir" com a marca "categoria dividida".
- **Nova a partir de Outros:** a IA agrupa os textos de Outros sob demanda e reclassifica só Outros.
- **Recusar proposta:** grava o motivo e silencia o alerta até o sinal crescer.
- **Já existe (PEND-18):**
  - os alertas `ampla`, `rara`, `outros`, `confusao` e `keyword_compartilhada` em `aprendizado.saude_de`;
  - o endpoint `GET /api/pergunta/<qid>/aprendizado`, que traz o dossiê completo.
