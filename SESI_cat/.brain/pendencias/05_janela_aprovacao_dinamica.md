---
id: PEND-05
titulo: Janela dinâmica para aprovar categorias (perfil informativo) + supervisor na interface
modulo_afetado: [tabulador, static/app.js, supervisor.py]
criticidade: media
status: resolvido
data_resolucao: 2026-09-24
responsavel: Gabriel Nascimento
data_abertura: 2026-09-23
resumo: "Levar o fluxo do supervisor.py (IA classifica, um segundo modelo audita, aceita sozinho o que tem confiança >= 0,70 com auditoria concordando) para a interface, com uma janela de aprovação que mostre por categoria o perfil de quem citou (NPS, satisfação, retenção, escola) e amostras, para aprovar em bloco. Fazer em commit separado."
---

# PEND-05: Janela dinâmica de aprovação de categorias

## Contexto
Em 23/09 a categorização do SESI foi supervisionada pela linha de comando (`tabulador/supervisor.py`):
a IA (Claude Code CLI, sonnet) classificou, o Claude auditou cada resposta como segundo codificador e
as respostas com confiança >= 0,70 **e** auditoria concordando foram confirmadas automaticamente
(`validado_por: "auto"`). O resto ficou pendente para o pesquisador, já com a sugestão do auditor.

Calibração (Q4, Q30, Q32, Q33, 1.223 respostas auditadas), discordância do auditor por faixa de confiança:
>= 0,95: 0,7% · 0,85–0,95: 0% · 0,70–0,85: 0,8% · 0,50–0,70: 3,6% · < 0,50: 49%.

## O que fazer
1. Botão "Aceitar alta confiança" na pergunta (usa `supervisor.cmd_auto_aceitar`) e mostrar
   `n_confirmadas_auto` separado das conferências humanas (o `resumo_revisao` já devolve).
   Confirmado com o Gabriel (24/09): é para manter exatamente como já aparece hoje no SESI —
   aprovações/confirmações automáticas e correções vindas da auditoria da IA revisora contam como
   uma forma de feedback também, não só as confirmações humanas manuais.
2. Janela de aprovação por categoria: nome, definição, n, % e **perfil de quem citou**
   (Grupo NPS, satisfação geral, intenção de manter, escola) contra o total, mais 5 exemplos.
   Aprovar/mesclar/renomear dali mesmo.
3. Mostrar a sugestão do auditor (`auditoria`, `ia_original`) na linha da resposta, com um atalho
   para "aceitar sugestão".
4. Auditoria por um segundo provedor (outro modelo) direto da interface.
5. **Novo (pedido do Gabriel, 24/09):** contabilizar na aba/API de uso (`usage.py`, `/api/usage`)
   as confirmações automáticas (`validado_por: "auto"`) e as chamadas do auditor/segundo codificador
   separadamente das confirmações humanas manuais — hoje `usage.py` não distingue `validado_por`,
   então esse consumo de chamadas de IA fica misturado com o resto. Verificado em 24/09: ainda não
   implementado.

## Resolução (24/09)
Os 5 itens estão feitos (ver DEC-03):
1. Na pergunta, o botão **⚡ Aceitar alta confiança** tem limiar ajustável (padrão 0,85) e o botão **↶ Desfazer as automáticas**. A pill "⚡ auto" e o filtro "confirmadas automaticamente" separam as automáticas; a barra de revisão também. O acerto da IA continua calculado como antes.
2. **🗂 Revisar por categoria** abre uma janela com um card por categoria:
   - definição e nome editáveis, e mesclar;
   - exemplos reais;
   - perfil de quem citou comparado com a base da pergunta: NPS, nota média, % de detratores, satisfação geral, % que pode trocar, escolas acima do esperado e os atributos Q6–Q26 que essas pessoas avaliam pior;
   - **✓ Confirmar N pendentes**, que deixa de fora as respostas em que o auditor discordou.
   Antes de classificar, a janela mostra só a definição e os exemplos. A configuração fica em `PERFIL`, no projeto.py.
3. A sugestão do auditor aparece na linha, com o botão "aceitar sugestão" e a tecla **S**, e há o filtro "auditor discordou". As sugestões adotadas pelo supervisor.py aparecem como "revisor".
4. **🔎 Auditar com outra IA** deixa escolher qualquer provedor ou modelo pronto, com `llm.usando` trocando o provedor só durante a chamada. Opcionalmente, já aceita as de alta confiança em seguida.
5. Na aba Consumo, os tokens de "auditoria" aparecem separados, e há o card "Supervisão por IA" (automáticas, auditadas e sugestões adotadas). "Conferência humana" passou a contar só as pessoas.

Módulos novos: `tabulador/supervisao.py` e `tabulador/perfil.py`. Testes: `tests/test_supervisao.py`.
