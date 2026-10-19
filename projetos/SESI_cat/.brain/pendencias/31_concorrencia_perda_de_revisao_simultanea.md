---
id: PEND-31
titulo: Duas pessoas revisando a mesma pergunta podem apagar o trabalho uma da outra (gravação sem checagem de versão)
objetivo_relacionado: OBJ-03
modulo_afetado: [tabulador, src/nuvem.py, src/codeframe.py, src/coding.py]
criticidade: alta
status: aberto
responsavel: Gabriel Nascimento
data_abertura: 2026-10-01
resumo: "Achado da revisão do plano (01/10), deduzido do código e ainda não reproduzido. codificacao.json é um blob único. Cada ✓/correção lê o arquivo inteiro, muda um item e regrava o arquivo inteiro (nuvem.gravar = upsert sem condição). O _lock de app.py só vale dentro de um processo, e cada máquina tem o seu. Com o cache de leitura de 5s, a leitura pode estar atrasada. Resultado: se Sara e João conferem a mesma pergunta ao mesmo tempo, o último a gravar apaga os ✓ do outro, sem erro e sem aviso. É o caminho de perda de dados mais provável hoje, mais do que um bug de código."
linear: JUM-18
---

# PEND-31: Perda por gravação simultânea

- **Mecanismo (lost update):**
  - A lê a v1 e B lê a v1;
  - A grava a v1+✓a, e B grava a v1+✓b;
  - o ✓a some.
  - O aviso de presença ("fulano também está nesta pergunta", PEND-09) avisa, mas não impede.
- **Reproduzir primeiro:** um teste com dois processos e Turso local (`file:`), ou dois `CD.validar` intercalados com leitura do cache, mostrando o item perdido.
- **Correção (concorrência otimista):**
  - `nuvem.gravar(..., se_versao=atualizado_em_lido)` vira `UPDATE ... WHERE atualizado_em = ?`; zero linhas afetadas = conflito;
  - no conflito: reler sem cache, **reaplicar só a mudança do item** (as operações de revisão são por rid, então o merge é trivial) e regravar, com até 3 tentativas;
  - operações em massa (classificar/auditar) já releem antes de gravar e passam a usar a mesma checagem;
  - no modo local, o mesmo vale pelo mtime do arquivo, se a pasta estiver compartilhada pelo OneDrive.
- **Relação com a PEND-24:** a guarda "não encolher conferidas por humano" pegaria parte disso como erro. Com esta correção, o conflito é resolvido em vez de bloqueado.
- **Até corrigir:** orientar a equipe a dividir as perguntas por pessoa (uma pessoa por pergunta).
