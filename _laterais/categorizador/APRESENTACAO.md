# Categorizador de respostas abertas — roteiro da apresentação

## Em uma frase
Um programa interno que transforma as respostas abertas de uma pesquisa em **categorias prontas para análise**
(planilha final, codebook e cruzamentos). A IA faz o trabalho pesado e o pesquisador **confere e decide**.

## O problema (30 s)
- Categorizar respostas abertas à mão é lento, caro e varia de pessoa para pessoa.
- Exemplo real: SESI Minas, com **3.743 respondentes** e **8 perguntas abertas**. Só a pergunta "O que precisa
  melhorar" tem **661 respostas diferentes**.
- Usar a IA "solta" não resolve: ninguém consegue auditar o que ela fez.

## A solução: a IA propõe, a pessoa valida (1 min)
1. **Categorias**: a IA lê as respostas e propõe uma lista fechada, com definição e exemplos reais. O
   pesquisador renomeia, junta, exclui ou pede ajustes em português ("junte X e Y") e **aprova**.
2. **Amostra primeiro**: a IA classifica 30 a 200 respostas. O pesquisador confirma ✓ ou corrige. O programa
   calcula a **taxa de acerto da IA** a partir dessas conferências.
3. **Loop de correção**: comentários viram instruções para a IA reclassificar. O que uma pessoa conferiu
   **nunca é sobrescrito**.
4. Com um acerto bom, a IA classifica o restante, o pesquisador **aprova** e os resultados saem prontos.

## O que sai no fim (30 s), na aba 📦 Resultados
- **Planilha final**: a planilha original com as colunas de categoria preenchidas, no formato que o cliente já usa.
- **Codebook** e **cruzamentos**: o % de cada categoria por perfil.
- Um gráfico por pergunta com o que as respostas dizem, e o indicador de quanto foi conferido por pessoas.

## Confiança e controle (30 s)
- **Transparência**: a janela de andamento mostra cada etapa, o lote atual, a velocidade, o tempo restante e
  as chamadas à IA. A aba **📈 Consumo** mostra os tokens, o tempo e o custo estimado de cada operação.
- **Rastreabilidade**: toda chamada à IA fica registrada. Só as perguntas **aprovadas** entram nos resultados.
- **Segurança**: a **🛠 Zona de perigo** pede confirmação digitada, e nada é apagado de verdade (vai para a
  lixeira). O **🧪 Modo teste** simula a IA sem custo, para treinar e fazer demonstrações.
- **Dados do cliente**: ficam na máquina. Só os textos das respostas vão para a IA, e colunas com dados
  pessoais são excluídas.
- **Sem dependência de fornecedor**: funciona com OpenAI, Gemini, Groq ou com o Claude Code instalado no
  computador. A troca é feita na tela.

## Escala: vários projetos (20 s)
- O programa já roda o **SESI** e a **Assertiva**. O botão **+ Novo projeto** lê uma planilha nova e monta a
  configuração **sem IA**, depois de conferir as perguntas pedidas pelo cliente. Um validador roda o processo
  real antes de liberar.

## Roteiro da demonstração (5 min, em 🧪 modo teste para não gastar)
1. **Painel geral**: o andamento das 8 perguntas.
2. Abrir uma pergunta, clicar em **Gerar categorias com IA** e mostrar a janela de andamento (etapas, barra, tempo).
3. Editar uma categoria, **pedir um ajuste à IA** e aprovar.
4. **Classificar amostra**: mostrar os lotes, a velocidade e o tempo restante. Depois conferir pelo teclado
   (Enter = ✓, 1–9 troca a categoria) e mostrar a **taxa de acerto** subindo.
5. Aprovar, abrir **📦 Resultados**, clicar em **Atualizar todos** e baixar a planilha final.
6. Terminar em **📈 Consumo** (custo) e **🛠 Gerenciar projeto** (controle).

## Próximos passos (se perguntarem)
- Rodar as 8 perguntas do SESI com a IA real e comparar com uma amostra categorizada à mão.
- Refazer a interface em React quando o uso crescer (hoje é HTML + JavaScript simples, sem instalação).
- Usar o assistente de novo projeto nas próximas pesquisas.

> Frase de fechamento: **"A IA faz o volume; o pesquisador mantém a decisão, e cada número sai auditável."**
