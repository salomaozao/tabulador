# PRODUCT.md — Tabulador de respostas abertas

> Rascunho de 2026-10-06 derivado do README e do código. Itens marcados (?) precisam da confirmação do Gabriel.

- **Propósito:** categorizar respostas abertas de pesquisa, gerar codebook e cruzamentos. A IA propõe categorias e classifica; o pesquisador valida tudo pela interface até ficar bom.
- **Público:** equipe do Instituto Olhar / Jumppi (pesquisadores, sem programação). Uso diário, sessões longas, tabelas grandes. Projetos hoje: SESI Minas e Assertiva.
- **Contexto de uso:** app local Flask (`iniciar.bat`, `http://127.0.0.1:5000`), várias pessoas e IAs no mesmo projeto (lista de presença), modo teste sem custo.
- **Tarefa central:** revisar e corrigir classificações (✓ confirmar, corrigir, comentar) com rapidez e sem perder o lugar; ver andamento e taxa de acerto.
- **Restrições:** sem build (HTML + `static/app.css` + `static/app.js` puros); PT-BR; dados de cliente nunca vão ao repositório; nada de dependência externa de CDN (?).
- **Voz:** direta, técnica, sem jargão de TI; avisos de perigo explícitos (apagar categorias exige digitar confirmação).
- **Princípios:** (1) densidade informativa com hierarquia clara, não decoração; (2) o estado do trabalho (pendente, confirmado, corrigido, atenção) legível de relance; (3) ações destrutivas sempre separadas e confirmadas; (4) acessível por teclado (foco visível) e legível em claro e escuro.
- **Anti-metas:** parecer template SaaS; modais intrusivos para tarefas longas (preferir painel/lista-detalhe); cor como único sinal de status.
