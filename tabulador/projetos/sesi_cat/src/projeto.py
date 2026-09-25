"""Projeto SESI — Pesquisa de satisfação das Escolas SESI Minas (pais e responsáveis).

Definição do projeto para o Tabulador (código em ../tabulador). Para abrir a
interface já neste projeto, dê dois cliques em "Abrir Tabulador.bat" nesta pasta.

Planilha-fonte: data/base_processamento.xlsx (somente leitura)
  aba "base"     - uma linha por respondente, uma coluna por pergunta (Q1..Q35); as colunas
                   Q*_CAT estão vazias e são preenchidas na planilha final gerada pelo app
  aba "Codebook" - enunciado de cada pergunta (usado como texto da pergunta para a IA)
Saídas: output/ (base, perguntas, codebook, cruzamentos, planilha final categorizada)

Para ajustar: rótulos, filtros de base, instruções fixas para a IA ("instrucoes_frame") e banners
dos cruzamentos estão abaixo. Instruções que mudam com frequência podem ser escritas direto na
interface (campo "Instruções para a IA" de cada pergunta).
"""
from __future__ import annotations

from pathlib import Path

NOME = "SESI Minas — Satisfação das Escolas"
CLIENTE = "SESI Minas"
FORMATO = "plano"  # uma linha de cabeçalho, uma coluna por pergunta

_MEU_DIR = Path(__file__).resolve().parent
_PASTA = _MEU_DIR.parent if _MEU_DIR.name in ("src", "codigo") else _MEU_DIR
FONTE_XLSX = _PASTA / "data" / "base_processamento.xlsx"
PLANO = {"aba": "base", "aba_codebook": "Codebook", "id": "respondent_id"}
# dados pessoais: nunca entram na base, nas saídas nem nos prompts da IA
PII_MATCH = ["ip_address", "email_address", "first_name", "last_name"]

CONTEXTO_PROJETO = (
    "Pesquisa de satisfação realizada pelo Instituto Olhar / Jumppi para o SESI Minas (Serviço Social da "
    "Indústria de Minas Gerais) com pais, mães e responsáveis de alunos das Escolas SESI em Minas Gerais "
    "(educação infantil, ensino fundamental e ensino médio, inclusive médio integrado ao técnico). "
    "Os temas avaliados são: estrutura física e tecnológica, atendimento da secretaria, proposta pedagógica "
    "e professores, bem-estar e acolhimento dos alunos, comunicação com as famílias, custo-benefício "
    "(mensalidade e materiais) e intenção de manter o aluno na escola. Respostas em português, de tamanho "
    "variado, muitas vezes com erros de digitação e com mais de um assunto na mesma resposta."
)

# --------------------------------------------------------------------------------------
# Filtros de base: quem recebeu a pergunta. As abertas incluem também quem respondeu fora do
# filtro (poucos casos de inconsistência no questionário), para nenhuma resposta ser descartada.
# --------------------------------------------------------------------------------------
SUPERIOR = ("Superiores", "Muito superiores.")
INFERIOR = ("Inferiores", "Muito inferiores")

FILTROS = {
    "todos": lambda df: df["respondent_id"].notna(),
    "vinculo_outro": lambda df: df["Q1"].eq("Outro vínculo. Qual?") | df["Q2"].notna(),
    "nps_0_7": lambda df: df["Q3"].le(7) | df["Q4"].notna(),
    "nps_8_10": lambda df: df["Q3"].ge(8) | df["Q5"].notna(),
    "superior": lambda df: df["Q28"].isin(SUPERIOR) | df["Q29"].notna(),
    "inferior": lambda df: df["Q28"].isin(INFERIOR) | df["Q30"].notna(),
    "prov_trocar": lambda df: df["Q31"].eq("Provavelmente vai trocar de escola") | df["Q32"].notna(),
    "cert_trocar": lambda df: df["Q31"].eq("Certamente vai trocar de escola") | df["Q33"].notna(),
}

FILTROS_DESCRICAO = {
    "todos": "Todos os respondentes",
    "vinculo_outro": "Vínculo com o aluno = 'Outro vínculo'",
    "nps_0_7": "Deram nota de 0 a 7 na recomendação (Q3)",
    "nps_8_10": "Deram nota de 8 a 10 na recomendação (Q3)",
    "superior": "Acham os diferenciais do SESI superiores aos de outras escolas (Q28)",
    "inferior": "Acham os diferenciais do SESI inferiores aos de outras escolas (Q28)",
    "prov_trocar": "Provavelmente vão trocar de escola (Q31)",
    "cert_trocar": "Certamente vão trocar de escola (Q31)",
}

# --------------------------------------------------------------------------------------
# Perguntas. "coluna" = nome da coluna na aba "base" (padrão: o próprio id).
# O enunciado completo vem da aba "Codebook".
# --------------------------------------------------------------------------------------
_SATISF = ["5Muito Satisfeito(a)", "4Satisfeito(a)", "3Neutro", "2Insatisfeito", "1Muito Insatisfeito(a", "Não sei avaliar"]

_INSTR_ESCOLA = (
    "Use categorias TEMÁTICAS sobre a escola, com nomes curtos e neutros (ex.: Professores/corpo docente, "
    "Qualidade do ensino/metodologia, Acompanhamento pedagógico, Comunicação com a família, Estrutura física, "
    "Tecnologia, Segurança, Alimentação/cantina, Esporte e atividades extracurriculares, Disciplina/bullying, "
    "Acolhimento/relacionamento, Atendimento da secretaria/gestão, Material didático/apostilas, "
    "Mensalidade/custo). Não crie categorias só com o nome da escola ou da cidade."
)

PERGUNTAS: list[dict] = [
    # ---- meta ----------------------------------------------------------------------
    {"id": "respondent_id", "tipo": "meta", "rotulo": "ID do respondente"},
    {"id": "collector_id", "tipo": "meta", "rotulo": "Coletor"},
    {"id": "date_created", "tipo": "meta", "rotulo": "Data de início"},
    {"id": "date_modified", "tipo": "meta", "rotulo": "Data de conclusão"},
    {"id": "ESCOLA", "coluna": "custom_1", "tipo": "meta", "rotulo": "Escola (unidade SESI)"},
    # ---- perfil / NPS ------------------------------------------------------------------
    {"id": "Q1", "tipo": "unica", "rotulo": "Relação com o(a) aluno(a)",
     "niveis": ["Mãe", "Pai", "Responsável legal", "Outro vínculo. Qual?"]},
    {"id": "Q2", "tipo": "aberta", "rotulo": "Outro vínculo com o aluno (qual?)", "base": "vinculo_outro", "codificar": True,
     "instrucoes_frame": "Categorias de PARENTESCO/VÍNCULO com o aluno (ex.: Avó/Avô, Tia/Tio, Irmã/Irmão, Padrasto/Madrasta). Respostas com nome próprio de pessoa vão para NS/NR."},
    {"id": "Q3", "tipo": "numerica", "rotulo": "NPS - probabilidade de indicar a Escola SESI (0-10)", "nps": True},
    {"id": "Q4", "tipo": "aberta", "rotulo": "O que precisa melhorar para nota 10", "base": "nps_0_7", "codificar": True,
     "instrucoes_frame": "Categorias de PONTOS A MELHORAR. " + _INSTR_ESCOLA},
    {"id": "Q5", "tipo": "aberta", "rotulo": "O que mais se destaca (motivo da nota alta)", "base": "nps_8_10", "codificar": True,
     "instrucoes_frame": "Categorias de PONTOS FORTES / motivos de satisfação. " + _INSTR_ESCOLA},
    # ---- satisfação (escala 1 a 5) -------------------------------------------------------
    {"id": "Q6", "tipo": "unica", "rotulo": "Estrutura - Limpeza e organização", "niveis": _SATISF},
    {"id": "Q7", "tipo": "unica", "rotulo": "Estrutura - Conservação das salas e espaços", "niveis": _SATISF},
    {"id": "Q8", "tipo": "unica", "rotulo": "Estrutura - Segurança da unidade", "niveis": _SATISF},
    {"id": "Q9", "tipo": "unica", "rotulo": "Estrutura - Estrutura tecnológica", "niveis": _SATISF},
    {"id": "Q10", "tipo": "unica", "rotulo": "Estrutura - Esporte e lazer", "niveis": _SATISF},
    {"id": "Q11", "tipo": "unica", "rotulo": "Estrutura - Alimentação (lanchonete/refeitório)", "niveis": _SATISF},
    {"id": "Q12", "tipo": "unica", "rotulo": "Secretaria - Cordialidade e respeito", "niveis": _SATISF},
    {"id": "Q13", "tipo": "unica", "rotulo": "Secretaria - Agilidade do atendimento", "niveis": _SATISF},
    {"id": "Q14", "tipo": "unica", "rotulo": "Secretaria - Capacidade de solucionar", "niveis": _SATISF},
    {"id": "Q15", "tipo": "unica", "rotulo": "Pedagógico - Metodologias de ensino", "niveis": _SATISF},
    {"id": "Q16", "tipo": "unica", "rotulo": "Pedagógico - Professores", "niveis": _SATISF},
    {"id": "Q17", "tipo": "unica", "rotulo": "Pedagógico - Acompanhamento acadêmico", "niveis": _SATISF},
    {"id": "Q18", "tipo": "unica", "rotulo": "Pedagógico - Aprendizagem e desenvolvimento", "niveis": _SATISF},
    {"id": "Q19", "tipo": "unica", "rotulo": "Pedagógico - Retorno à família", "niveis": _SATISF},
    {"id": "Q20", "tipo": "unica", "rotulo": "Bem-estar - Acolhimento", "niveis": _SATISF},
    {"id": "Q21", "tipo": "unica", "rotulo": "Bem-estar - Relações entre alunos e profissionais", "niveis": _SATISF},
    {"id": "Q22", "tipo": "unica", "rotulo": "Bem-estar - Inclusão e convivência", "niveis": _SATISF},
    {"id": "Q23", "tipo": "unica", "rotulo": "Bem-estar - Segurança emocional e pertencimento", "niveis": _SATISF},
    {"id": "Q24", "tipo": "unica", "rotulo": "Comunicação - Clareza e transparência", "niveis": _SATISF},
    {"id": "Q25", "tipo": "unica", "rotulo": "Comunicação - Frequência e antecedência", "niveis": _SATISF},
    {"id": "Q26", "tipo": "unica", "rotulo": "Comunicação - Canais de comunicação", "niveis": _SATISF},
    {"id": "Q27", "tipo": "unica", "rotulo": "Custo-benefício",
     "niveis": ["Muito bom", "Bom", "Regular", "Ruim", "Muito ruim", "Não sabe/Não se aplica"]},
    # ---- comparação com outras escolas ------------------------------------------------------
    {"id": "Q28", "tipo": "unica", "rotulo": "Diferenciais comparados a outras escolas",
     "niveis": ["Muito superiores.", "Superiores", "Semelhantes", "Inferiores", "Muito inferiores", "Não tenho base para comparar"]},
    {"id": "Q29", "tipo": "aberta", "rotulo": "Em que o SESI é melhor que outras escolas", "base": "superior", "codificar": True,
     "instrucoes_frame": "Categorias de VANTAGENS do SESI frente a outras escolas. " + _INSTR_ESCOLA},
    {"id": "Q30", "tipo": "aberta", "rotulo": "Em que o SESI pode melhorar frente a outras escolas", "base": "inferior", "codificar": True,
     "instrucoes_frame": "Categorias de DESVANTAGENS / pontos a melhorar frente a outras escolas. " + _INSTR_ESCOLA},
    # ---- retenção ----------------------------------------------------------------------------
    {"id": "Q31", "tipo": "unica", "rotulo": "Possibilidade de manter o aluno no próximo ano",
     "niveis": ["Certamente manterá", "Provavelmente manterá", "Provavelmente vai trocar de escola", "Certamente vai trocar de escola"]},
    {"id": "Q32", "tipo": "aberta", "rotulo": "Por que provavelmente vai trocar de escola", "base": "prov_trocar", "codificar": True,
     "instrucoes_frame": "Categorias de MOTIVO PARA TROCAR DE ESCOLA (insatisfações com a escola e também motivos externos, "
                         "ex.: mudança de cidade, conclusão do ciclo/formatura, custo/mensalidade, distância). "
                         "Respostas que só remetem a respostas anteriores ('pelos motivos já citados') formam categoria própria."},
    {"id": "Q33", "tipo": "aberta", "rotulo": "Por que certamente vai trocar de escola", "base": "cert_trocar", "codificar": True,
     "instrucoes_frame": "Categorias de MOTIVO PARA TROCAR DE ESCOLA (insatisfações com a escola e também motivos externos, "
                         "ex.: mudança de cidade, conclusão do ciclo/formatura ('último ano', 'vai se formar'), custo, distância). "
                         "Respostas que só remetem a respostas anteriores formam categoria própria."},
    {"id": "Q34", "tipo": "unica", "rotulo": "Satisfação geral com a Escola SESI",
     "niveis": ["Muito satisfeito(a)", "Satisfeito(a)", "Nem satisfeito(a), nem insatisfeito(a)", "Insatisfeito(a)", "Muito insatisfeito(a)"]},
    {"id": "Q35", "tipo": "aberta", "rotulo": "Principal melhoria para aumentar a satisfação", "codificar": True,
     "instrucoes_frame": "Categorias de SUGESTÃO DE MELHORIA. " + _INSTR_ESCOLA
                         + " Separe 'Nada a melhorar / está tudo bom' como categoria própria."},
]

# --------------------------------------------------------------------------------------
# Variáveis derivadas (banners dos cruzamentos)
# --------------------------------------------------------------------------------------
DERIVADAS = {
    "VINCULO": {
        "rotulo": "Vínculo com o aluno", "origem": "Q1",
        "mapa": {"Mãe": "Mãe", "Pai": "Pai", "Responsável legal": "Outro responsável", "Outro vínculo. Qual?": "Outro responsável"},
        "niveis": ["Mãe", "Pai", "Outro responsável"],
    },
    "NPS_GRUPO": {
        "rotulo": "Grupo NPS", "origem": "Q3",
        "faixas": [(0, 6, "Detratores (0-6)"), (7, 8, "Neutros (7-8)"), (9, 10, "Promotores (9-10)")],
        "niveis": ["Promotores (9-10)", "Neutros (7-8)", "Detratores (0-6)"],
    },
    "COMPARACAO3": {
        "rotulo": "Diferenciais vs. outras escolas", "origem": "Q28",
        "mapa": {"Muito superiores.": "Superiores", "Superiores": "Superiores", "Semelhantes": "Semelhantes",
                 "Inferiores": "Inferiores", "Muito inferiores": "Inferiores", "Não tenho base para comparar": "Sem base para comparar"},
        "niveis": ["Superiores", "Semelhantes", "Inferiores", "Sem base para comparar"],
    },
    "RETENCAO2": {
        "rotulo": "Intenção de manter o aluno", "origem": "Q31",
        "mapa": {"Certamente manterá": "Vai manter", "Provavelmente manterá": "Vai manter",
                 "Provavelmente vai trocar de escola": "Pode trocar", "Certamente vai trocar de escola": "Pode trocar"},
        "niveis": ["Vai manter", "Pode trocar"],
    },
    "SATISFACAO3": {
        "rotulo": "Satisfação geral (3 grupos)", "origem": "Q34",
        "mapa": {"Muito satisfeito(a)": "Satisfeitos", "Satisfeito(a)": "Satisfeitos",
                 "Nem satisfeito(a), nem insatisfeito(a)": "Neutros",
                 "Insatisfeito(a)": "Insatisfeitos", "Muito insatisfeito(a)": "Insatisfeitos"},
        "niveis": ["Satisfeitos", "Neutros", "Insatisfeitos"],
    },
}

# Perfil de quem citou cada categoria (janela de aprovação): comparado com quem respondeu a mesma pergunta
PERFIL = {
    "nps": "Q3",                              # nota 0-10
    "satisfacao": "Q34",                      # satisfação geral (escala de 5)
    "retencao": ("RETENCAO2", "Pode trocar"),
    "grupo": "ESCOLA",
    "atributos": [f"Q{i}" for i in range(6, 27)],  # satisfação por tema (Q6-Q26)
}

BANNERS_PADRAO = ["VINCULO", "NPS_GRUPO", "COMPARACAO3", "RETENCAO2", "SATISFACAO3"]

# --------------------------------------------------------------------------------------
# Planilha final: cópia de data/base_processamento.xlsx com as colunas *_CAT preenchidas
# (categoria principal). A categoria secundária vai numa coluna *_CAT2 criada ao lado.
# --------------------------------------------------------------------------------------
SAIDA_PLANILHA = {
    "arquivo": "base_processamento_categorizada.xlsx",
    "aba": "base",
    "id": "respondent_id",
    "colunas": {"Q2": "Q2_CAT", "Q4": "Q4_CAT", "Q5": "Q5_CAT", "Q29": "Q29_CAT", "Q30": "Q30_CAT",
                "Q32": "Q32_CAT", "Q33": "Q33_CAT", "Q35": "Q35_CAT"},
}

