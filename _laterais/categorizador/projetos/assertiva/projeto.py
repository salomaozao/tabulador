"""Projeto ASSERTIVA — "Mapeamento do Mercado de Análise de Crédito e Risco no Brasil".

Definição do projeto para o categorizador (ver projetos.py): planilha-fonte, contexto para a IA
e o Mapa Canônico de Variáveis.

Cada pergunta do questionário recebe um identificador estável (ex.: Q02_CARGO) e é localizada
na planilha SurveyMonkey pelo TEXTO do enunciado (linha 1 do cabeçalho) e da opção (linha 2),
nunca pelo índice da coluna. Assim as abas `dados_originais_autopreenchidos` e
`dados_originais_pesquisadores` (que têm colunas extras e ordem diferente) caem no mesmo mapa.

Tipos:
  meta           - identificação/controle (não é pergunta)
  unica          - resposta única (uma coluna "Response"; pode ter coluna "Outro. Qual?")
  aberta         - texto livre
  multipla       - múltipla escolha dicotômica (uma coluna por item; vira 0/1)
  numerica       - número (NPS)
  grade_numerica - grade 0-10 (uma coluna numérica por atributo)
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------------------
# Projeto: nome, planilha-fonte, saídas e contexto para a IA
# --------------------------------------------------------------------------------------
NOME = "Assertiva"
CLIENTE = "Assertiva"
FORMATO = "surveymonkey"  # cabeçalho duplo, duas abas (autopreenchido + telefone)

_CATEGORIZADOR = Path(__file__).resolve().parents[2]
_ONEDRIVE = _CATEGORIZADOR.parents[1]  # ...\INSTITUTO OLHAR - PESQUISA E INFORMACAO ESTRATEGICA LTDA
PROJETO_DIR = _ONEDRIVE / "Shortcuts" / "Projetos - ASSERTIVA - Análise de Credito"
LEGADO_DIR = _ONEDRIVE / "Shortcuts" / "Projetos - Categorização de Respostas Abertas" / "Projeto IA" / "CategorizadorDeRespostasAbertas1"
ENV_EXTRA = LEGADO_DIR / ".env"  # chave OpenAI do categorizador legado (somente leitura), se não houver outra

# Planilha-fonte (SurveyMonkey exportado) e abas
FONTE_XLSX = Path(os.getenv("ASSERTIVA_FONTE", PROJETO_DIR / "Acompanhamento de campo" / "Acompanhamento de campo.xlsx"))
ABAS = {
    "autopreenchido": "dados_originais_autopreenchidos",
    "telefone": "dados_originais_pesquisadores",
}
# Saídas continuam em categorizador/output (onde já estão os resultados da Assertiva)
OUTPUT_DIR = Path(os.getenv("ASSERTIVA_OUTPUT", _CATEGORIZADOR / "output"))

CONTEXTO_PROJETO = (
    "Pesquisa de mercado quantitativa 'Mapeamento do Mercado de Análise de Crédito e Risco no Brasil', "
    "realizada pelo Instituto Olhar / Jumppi para a Assertiva Soluções (empresa de dados e soluções para "
    "análise de crédito, cobrança e prevenção a fraudes). Respondentes: profissionais que participam do "
    "processo de análise de risco ou aprovação de crédito em empresas brasileiras (bancos, fintechs, "
    "varejo, indústria, serviços). Respostas curtas, em português, muitas vezes com erros de digitação."
)


# --------------------------------------------------------------------------------------
# Filtros de base (quem deveria ter respondido a pergunta). Avaliados sobre o DataFrame.
# --------------------------------------------------------------------------------------
NUNCA_OUVIU = "Não. Nunca ouviu falar"
CONHECE_NAO_CLIENTE = ("Sim. Conhece, mas não é cliente", "Sim. Conhece, mas é ex-cliente")
CLIENTE_OU_EX = ("Sim. Conhece e é cliente", "Sim. Conhece, mas é ex-cliente")

FILTROS = {
    "todos": lambda df: df["respondent_id"].notna(),
    "cargo_outro": lambda df: df["Q02_CARGO"].eq("Outro. Qual?"),
    "segmento_outro": lambda df: df["Q04_SEGMENTO"].isin(["Outro. Qual?", "Outro"]),
    "motivo_negar_outro": lambda df: df["Q16_MOTIVO_NEGAR"].eq("Outros. Quais?"),
    "dificuldade_outro": lambda df: df["Q18_DIFICULDADE"].eq("Outra. Qual?"),
    "info_falta_sim": lambda df: df["Q26_INFO_FALTA"].eq("Sim. Quais?"),
    "conhece_assertiva": lambda df: df["Q27_CONHECE_ASSERTIVA"].notna() & df["Q27_CONHECE_ASSERTIVA"].ne(NUNCA_OUVIU),
    "cliente_ou_ex": lambda df: df["Q27_CONHECE_ASSERTIVA"].isin(CLIENTE_OU_EX),
    "conhece_nao_cliente": lambda df: df["Q27_CONHECE_ASSERTIVA"].isin(CONHECE_NAO_CLIENTE),
    "dificilmente_contrataria": lambda df: df["Q35_PROB_CONTRATAR"].fillna("").str.startswith("Dificilmente"),
    "dificilmente_escolheria": lambda df: df["Q37_PROB_ESCOLHER"].fillna("").str.startswith("Dificilmente"),
}

FILTROS_DESCRICAO = {
    "todos": "Todos os respondentes",
    "cargo_outro": "Cargo = 'Outro. Qual?'",
    "segmento_outro": "Segmento = 'Outro'",
    "motivo_negar_outro": "Principal motivo para negar = 'Outros'",
    "dificuldade_outro": "Maior dificuldade = 'Outra'",
    "info_falta_sim": "Gostaria de consultar informação que não consegue = 'Sim'",
    "conhece_assertiva": "Conhece ou já ouviu falar da Assertiva",
    "cliente_ou_ex": "Cliente ou ex-cliente da Assertiva",
    "conhece_nao_cliente": "Conhece a Assertiva mas não é cliente (inclui ex-cliente)",
    "dificilmente_contrataria": "Dificilmente contrataria a Assertiva",
    "dificilmente_escolheria": "Dificilmente escolheria a Assertiva",
}

# --------------------------------------------------------------------------------------
# Especificação das perguntas. `match` = trecho (normalizado) que identifica o enunciado.
# Pode ser lista de alternativas (texto diverge entre as abas). `ocorrencia` distingue
# enunciados idênticos ("Porque você {{ Qxx }}...") pela ordem em que aparecem.
# --------------------------------------------------------------------------------------
PERGUNTAS: list[dict] = [
    # ---- meta --------------------------------------------------------------------
    {"id": "respondent_id", "tipo": "meta", "match": "respondent_id", "rotulo": "ID SurveyMonkey"},
    {"id": "collector_id", "tipo": "meta", "match": "collector_id", "rotulo": "Coletor SurveyMonkey"},
    {"id": "date_created", "tipo": "meta", "match": "date_created", "rotulo": "Data de início"},
    {"id": "date_modified", "tipo": "meta", "match": "date_modified", "rotulo": "Data de conclusão"},
    {"id": "uf", "tipo": "meta", "match": "uf", "rotulo": "UF (campo do coletor)", "exato": True},
    {"id": "regiao", "tipo": "meta", "match": "regiao", "rotulo": "Região (campo do coletor)", "exato": True},
    {
        "id": "controle",
        "tipo": "meta_bloco",
        "match": "controle interno",
        "rotulo": "Controle interno (telefone)",
        "itens": {"nome do pesquisador": "pesquisador", "id": "id_controle"},
    },
    # ---- filtro / triagem ---------------------------------------------------------
    {"id": "Q00_CONFIDENCIALIDADE", "tipo": "unica", "match": "a pesquisa garante confidencialidade", "rotulo": "Aceite de confidencialidade (telefone)"},
    {"id": "Q01_PARTICIPA", "tipo": "unica", "match": "participa do processo de analise de risco", "rotulo": "Participa do processo de análise de risco/crédito"},
    # ---- perfil -------------------------------------------------------------------
    {"id": "Q02_CARGO", "tipo": "unica", "match": "qual seu cargo", "rotulo": "Cargo",
     "outro": {"id": "Q02_CARGO_OUTRO", "rotulo": "Cargo - Outro. Qual?", "base": "cargo_outro"}},
    {"id": "Q03_AREA", "tipo": "aberta", "match": "qual sua area/departamento", "rotulo": "Área/departamento",
     "codificar": True,
     "instrucoes_frame": (
         "Agrupe as respostas em ÁREAS FUNCIONAIS da empresa (ex.: Crédito/Risco, Cobrança/Recuperação, "
         "Financeiro/Controladoria, Comercial/Vendas, Diretoria/Gestão geral, TI/Dados/Tecnologia, "
         "Marketing, Administrativo/Operações, Jurídico/Compliance, Atendimento/CS, RH). Uma categoria por área; "
         "não separe sinônimos (Vendas = Comercial)."
     )},
    {"id": "Q04_SEGMENTO", "tipo": "unica", "match": "qual o segmento de atuacao", "rotulo": "Segmento de atuação da empresa",
     "outro": {"id": "Q04_SEGMENTO_OUTRO", "rotulo": "Segmento - Outro. Qual?", "base": "segmento_outro"}},
    {"id": "Q05_PORTE", "tipo": "unica", "match": "numero de colaboradores", "rotulo": "Porte (nº de colaboradores)",
     "niveis": ["Até 09 colaboradores", "10 a 49 colaboradores", "50 a 99 colaboradores", "100 a 499 colaboradores", "500 colaboradores ou mais"]},
    {"id": "Q06_PUBLICO", "tipo": "unica", "match": ["concede credito ou analise de risco para pessoa", "concede credito para pessoa fisica"], "rotulo": "Público atendido (PF/PJ/Ambos)"},
    {"id": "Q07_VOLUME", "tipo": "unica", "match": "quantas analises de credito", "rotulo": "Volume mensal de análises de crédito/risco",
     "niveis": ["Até 100", "101 a 500", "501 a 2.000", "2.001 a 5.000", "Mais de 5.000", "Não sabe informar"]},
    # ---- processo de crédito --------------------------------------------------------
    {"id": "Q08_BASE_DECISAO", "tipo": "unica", "match": ["quando sua empresa avalia credito/risco", "quando sua empresa avalia se libera credito"], "rotulo": "Principal base de decisão de crédito"},
    {"id": "Q09_USA_IA", "tipo": "unica", "match": "utiliza inteligencia artificial", "rotulo": "Uso de IA na avaliação de crédito/risco"},
    {"id": "Q10_SABE_DIFERENCA", "tipo": "unica", "match": "sabe a diferenca entre analise comportamental", "rotulo": "Sabe a diferença entre análise comportamental e restritiva"},
    {"id": "Q11_USA_COMPORTAMENTAL", "tipo": "unica", "match": "utiliza analise comportamental", "rotulo": "Utiliza análise comportamental (dados positivos)"},
    {"id": "Q12_ONDE_DECISAO", "tipo": "unica", "match": "onde, na pratica, a decisao", "rotulo": "Onde a decisão de crédito é tomada"},
    {"id": "Q13_VALIDACAO_ID", "tipo": "unica", "match": "confirma que a pessoa ou empresa", "rotulo": "Como valida identidade"},
    {"id": "Q14_TEMPO_RESPOSTA", "tipo": "unica", "match": "quanto tempo sua empresa leva", "rotulo": "Tempo de resposta ao pedido de crédito",
     "niveis": ["Minutos, de forma totalmente automatizada", "Menos de 1 hora", "Algumas horas no mesmo dia", "Entre 1 e 2 dias úteis", "Mais de 2 dias úteis"]},
    {"id": "Q15_POLITICA", "tipo": "unica", "match": "regras e criterios formais", "rotulo": "Política de crédito formal"},
    {"id": "Q16_MOTIVO_NEGAR", "tipo": "unica", "match": "principal motivo para negar", "rotulo": "Principal motivo para negar crédito",
     "outro": {"id": "Q16_MOTIVO_NEGAR_OUTRO", "rotulo": "Motivo para negar - Outros. Quais?", "base": "motivo_negar_outro"}},
    {"id": "Q17_MODELOS_BONS", "tipo": "unica", "match": "modelos atuais de analise de credito", "rotulo": "Modelos atuais identificam bons pagadores rejeitados?"},
    {"id": "Q18_DIFICULDADE", "tipo": "unica", "match": "maior dificuldade para conceder", "rotulo": "Maior dificuldade para conceder crédito",
     "outro": {"id": "Q18_DIFICULDADE_OUTRO", "rotulo": "Maior dificuldade - Outra. Qual?", "base": "dificuldade_outro"}},
    {"id": "Q19_INADIMPLENCIA", "tipo": "unica", "match": "aumento da inadimplencia", "rotulo": "Percepção de aumento da inadimplência vs 2025",
     "niveis": ["Sim, forte aumento", "Sim, leve aumento", "Estável", "Queda"]},
    {"id": "Q20_FRAUDES", "tipo": "unica", "match": "fraudes estao mais frequentes", "rotulo": "Fraudes mais frequentes que há um ano?"},
    {"id": "Q21_EXCLUI_BONS", "tipo": "unica", "match": "exclui bons pagadores", "rotulo": "Sistema atual exclui bons pagadores?"},
    # ---- mercado ------------------------------------------------------------------
    {"id": "Q22_TOM", "tipo": "aberta", "match": "primeira empresa que vem a mente", "rotulo": "Top of mind - sistema de avaliação de crédito",
     "codificar": True, "unica_com_outro": True,
     "outro": {"id": "Q22_TOM_OUTRO", "rotulo": "Top of mind - Outra. Qual? (fundido em Q22_TOM)", "fundir": True},
     "instrucoes_frame": (
         "Cada categoria é UMA EMPRESA/MARCA com nome canônico (ex.: 'Serasa Experian', 'SPC Brasil', 'Boa Vista', "
         "'Quod', 'Equifax', 'Assertiva', 'Nubank', 'Pipefy'). Normalize variações de grafia/caixa (serasa, SERASA, "
         "Serasa Experian = 'Serasa Experian'). Marcas citadas por 1 respondente podem ir para 'Outras empresas'. "
         "Respostas compostas ('Equifax, Serasa') recebem a PRIMEIRA marca como primária e a segunda como secundária."
     )},
    {"id": "Q23_CONHECE_EMPRESAS", "tipo": "multipla", "match": "empresas voce conhece nesse mercado", "rotulo": "Empresas conhecidas/consideradas boas ou possíveis fornecedores",
     "outro": {"id": "Q23_CONHECE_EMPRESAS_OUTRO", "rotulo": "Empresas conhecidas - Outra. Qual?"}},
    {"id": "Q24_FONTES", "tipo": "multipla", "match": "quais sistemas ou solucoes a sua empresa utiliza", "rotulo": "Fontes de informação utilizadas",
     "outro": {"id": "Q24_FONTES_OUTRO", "rotulo": "Fontes - Outra. Qual?"}},
    {"id": "Q25_ESCOLHA_FORNECEDOR", "tipo": "multipla", "match": "influencia a escolha de um fornecedor", "rotulo": "O que mais influencia a escolha de fornecedor (até 3)",
     "outro": {"id": "Q25_ESCOLHA_FORNECEDOR_OUTRO", "rotulo": "Escolha de fornecedor - Outro. Qual?"}},
    {"id": "Q26_INFO_FALTA", "tipo": "unica", "match": "gostaria de consultar e nao consegue", "rotulo": "Há informação que gostaria de consultar e não consegue?",
     "outro": {"id": "Q26_INFO_FALTA_QUAIS", "rotulo": "Informação que gostaria de consultar - Sim. Quais?", "base": "info_falta_sim"}},
    # ---- Assertiva ----------------------------------------------------------------
    {"id": "Q27_CONHECE_ASSERTIVA", "tipo": "unica", "match": "voce conhece a assertiva", "rotulo": "Conhece a Assertiva?",
     "niveis": ["Sim. Conhece e é cliente", "Sim. Conhece, mas é ex-cliente", "Sim. Conhece, mas não é cliente", "Já ouviu falar (não é cliente)", NUNCA_OUVIU]},
    {"id": "Q28_IMG_ASSERTIVA", "tipo": "aberta", "match": "primeira palavra ou ideia", "rotulo": "Primeira palavra/ideia associada à Assertiva", "base": "conhece_assertiva",
     "codificar": True,
     "instrucoes_frame": "Categorias de IMAGEM/ASSOCIAÇÃO de marca (atributos, produtos, sentimentos). Respostas que apenas repetem o nome 'Assertiva'/'assertividade' formam uma categoria própria."},
    {"id": "Q29_POSITIVOS", "tipo": "aberta", "match": "pontos positivos da assertiva", "rotulo": "Principais pontos positivos da Assertiva", "base": "conhece_assertiva",
     "codificar": True,
     "instrucoes_frame": "Categorias de ATRIBUTOS POSITIVOS (ex.: rapidez/agilidade, confiabilidade, qualidade/riqueza dos dados, atendimento, preço, tecnologia). Inclua uma categoria para quem declara não conhecer o suficiente para opinar."},
    {"id": "Q30_NEGATIVOS", "tipo": "aberta", "match": "pontos negativos da assertiva", "rotulo": "Principais pontos negativos da Assertiva", "base": "conhece_assertiva",
     "codificar": True,
     "instrucoes_frame": "Categorias de ATRIBUTOS NEGATIVOS/CRÍTICAS (ex.: preço/custo, falta de dados, suporte, divulgação). Separe 'Nenhum ponto negativo' (declara que não há) de 'Não conhece o suficiente para opinar'."},
    {"id": "Q31_ASSOCIACOES", "tipo": "multipla", "match": "selecione as tres que mais estao associadas", "rotulo": "Características associadas à Assertiva (até 3)", "base": "conhece_assertiva"},
    {"id": "Q32_NPS", "tipo": "numerica", "match": "indicar a assertiva para um colega", "rotulo": "NPS - probabilidade de indicar a Assertiva (0-10)", "base": "conhece_assertiva", "nps": True},
    {"id": "Q33_MOTIVO_NPS", "tipo": "aberta", "match": "por que deu essa nota", "rotulo": "Motivo da nota (NPS)", "base": "conhece_assertiva",
     "codificar": True,
     "instrucoes_frame": "Categorias de MOTIVO da nota: podem ser positivos (qualidade, confiança, rapidez), negativos (preço, falta de dados, burocracia) ou de baixo conhecimento ('conhece pouco / só ouviu falar'). Mantenha a polaridade explícita no nome da categoria."},
    {"id": "Q34_AVAL_ATRIBUTOS", "tipo": "grade_numerica", "match": "avalia cada um dos atributos", "rotulo": "Avaliação dos atributos da Assertiva (0-10)", "base": "cliente_ou_ex"},
    {"id": "Q35_PROB_CONTRATAR", "tipo": "unica", "match": "probabilidade do sr(a) vir a contratar", "rotulo": "Probabilidade de vir a contratar a Assertiva", "base": "conhece_nao_cliente",
     "outro": {"id": "Q35_PROB_CONTRATAR_PORQUE", "rotulo": "Probabilidade de contratar - Por quê? (campo não utilizado)"}},
    {"id": "Q36_MOTIVO_CONTRATAR", "tipo": "aberta", "match": "porque voce {{", "ocorrencia": 1, "rotulo": "Por que dificilmente contrataria a Assertiva", "base": "dificilmente_contrataria"},
    {"id": "Q37_PROB_ESCOLHER", "tipo": "unica", "match": "queira contratar uma nova empresa", "rotulo": "Probabilidade de escolher a Assertiva ao contratar nova empresa", "base": "conhece_nao_cliente"},
    {"id": "Q38_MOTIVO_ESCOLHER", "tipo": "aberta", "match": "porque voce {{", "ocorrencia": 2, "rotulo": "Por que dificilmente escolheria a Assertiva", "base": "dificilmente_escolheria"},
    {"id": "Q39_MELHORIA", "tipo": "aberta", "match": "precisaria melhorar ou oferecer", "rotulo": "O que a Assertiva precisaria melhorar para ser a primeira opção", "base": "conhece_nao_cliente",
     "codificar": True,
     "instrucoes_frame": "Categorias de SUGESTÃO DE MELHORIA (ex.: preço, divulgação/comunicação da marca, mais dados/atualização, integração/automação, menos burocracia). Separe 'Nada a melhorar / já está no caminho certo' de 'Não conhece o suficiente'."},
]

# Colunas que são PII ou lixo e devem ser descartadas (match no enunciado normalizado).
PII_MATCH = ["ip_address", "email_address", "first_name", "last_name", "nome completo", "whatsapp", "whatsap", "e-mail", "identificacao do respondente"]

# --------------------------------------------------------------------------------------
# Back-coding: frames FIXOS para reclassificar 'Outro. Qual?' e fechar os banners.
# --------------------------------------------------------------------------------------
BACKCODING = {
    "Q02_CARGO_OUTRO": {
        "pergunta_pai": "Q02_CARGO",
        "banner": "CARGO4",
        "frame": [
            {"codigo": 1, "nome": "Sócio(a)/Diretoria", "definicao": "Proprietário, sócio, MEI, diretor, C-level, presidente, head de área com status de diretoria."},
            {"codigo": 2, "nome": "Gerência", "definicao": "Gerente (inclui gerente sênior, gerente de grupo/regional), líder/head de equipe de nível gerencial."},
            {"codigo": 3, "nome": "Coordenação/Supervisão", "definicao": "Coordenador, supervisor, líder de célula/time."},
            {"codigo": 4, "nome": "Analista/Técnico/Operacional", "definicao": "Analista, especialista, consultor, assessor, assistente, agente comercial, administrativo, engenheiro, desenvolvedor."},
        ],
        "mapa_banner": {1: "Diretoria", 2: "Gerência/Coordenação", 3: "Gerência/Coordenação", 4: "Analista/Operacional", 97: "Outro"},
        "fechados": {
            "Sócio(a) e/ou Diretor(a)": "Diretoria",
            "Gerente": "Gerência/Coordenação",
            "Coordenador(a)/Supervisor(a)": "Gerência/Coordenação",
            "Analista": "Analista/Operacional",
        },
    },
    "Q04_SEGMENTO_OUTRO": {
        "pergunta_pai": "Q04_SEGMENTO",
        "banner": "SEGMENTO4",
        "frame": [
            {"codigo": 1, "nome": "Serviços financeiros", "definicao": "Corretora, gestora de fundos, FIDC, consórcio, seguradora, meios de pagamento, securitizadora, factoring."},
            {"codigo": 2, "nome": "Varejo/Comércio", "definicao": "Loja, comércio, ótica, e-commerce, atacado, distribuidora."},
            {"codigo": 3, "nome": "Indústria/Agro/Construção", "definicao": "Indústria, agronegócio, construtora, incorporadora, mercado imobiliário, energia."},
            {"codigo": 4, "nome": "Serviços", "definicao": "Turismo, consultoria, software/tecnologia, telecom, logística/transporte, comunicação/publicidade/mídia, serviços em geral, educação, saúde."},
        ],
        "mapa_banner": {1: "Financeiro", 2: "Varejo", 3: "Indústria e Serviços", 4: "Indústria e Serviços", 97: "Outro"},
        "fechados": {
            "Banco": "Financeiro",
            "Instituição Financeira": "Financeiro",
            "Fintech": "Financeiro",
            "Promotora de Crédito": "Financeiro",
            "Cooperativa de Crédito": "Financeiro",
            "Varejo": "Varejo",
            "Indústria": "Indústria e Serviços",
            "Saúde": "Indústria e Serviços",
            "Imobiliária": "Indústria e Serviços",
            "Educação": "Indústria e Serviços",
        },
    },
}

# --------------------------------------------------------------------------------------
# Variáveis derivadas (banners). Ordem dos níveis = ordem de exibição nos cruzamentos.
# --------------------------------------------------------------------------------------
DERIVADAS = {
    "PORTE3": {
        "rotulo": "Porte (3 faixas)", "origem": "Q05_PORTE",
        "mapa": {
            "Até 09 colaboradores": "Até 49 colaboradores",
            "10 a 49 colaboradores": "Até 49 colaboradores",
            "50 a 99 colaboradores": "50 a 499 colaboradores",
            "100 a 499 colaboradores": "50 a 499 colaboradores",
            "500 colaboradores ou mais": "500 colaboradores ou mais",
        },
        "niveis": ["Até 49 colaboradores", "50 a 499 colaboradores", "500 colaboradores ou mais"],
    },
    "VOLUME4": {
        "rotulo": "Volume mensal de análises (4 faixas)", "origem": "Q07_VOLUME",
        "mapa": {
            "Até 100": "Até 100",
            "101 a 500": "101 a 2.000",
            "501 a 2.000": "101 a 2.000",
            "2.001 a 5.000": "Mais de 2.000",
            "Mais de 5.000": "Mais de 2.000",
            "Não sabe informar": "Não sabe informar",
        },
        "niveis": ["Até 100", "101 a 2.000", "Mais de 2.000", "Não sabe informar"],
    },
    "PUBLICO": {
        "rotulo": "Público atendido", "origem": "Q06_PUBLICO",
        "mapa": None,
        "niveis": ["Pessoa Física", "Pessoa Jurídica", "Ambos"],
    },
    "CONHECE_ASSERTIVA2": {
        "rotulo": "Conhecimento da Assertiva (2 grupos)", "origem": "Q27_CONHECE_ASSERTIVA",
        "mapa": {
            "Sim. Conhece e é cliente": "Conhece / já ouviu falar",
            "Sim. Conhece, mas é ex-cliente": "Conhece / já ouviu falar",
            "Sim. Conhece, mas não é cliente": "Conhece / já ouviu falar",
            "Já ouviu falar (não é cliente)": "Conhece / já ouviu falar",
            NUNCA_OUVIU: "Não conhece",
        },
        "niveis": ["Conhece / já ouviu falar", "Não conhece"],
    },
    "NPS_GRUPO": {
        "rotulo": "Grupo NPS", "origem": "Q32_NPS",
        "faixas": [(0, 6, "Detratores (0-6)"), (7, 8, "Neutros (7-8)"), (9, 10, "Promotores (9-10)")],
        "niveis": ["Promotores (9-10)", "Neutros (7-8)", "Detratores (0-6)"],
    },
    "USA_IA2": {
        "rotulo": "Usa IA na avaliação de crédito (2 grupos)", "origem": "Q09_USA_IA",
        "mapa": {
            "Usamos IA de forma plena, cruzando score e outros dados em 100% das aprovações": "Sim",
            "Usamos IA para cruzar score e outros dados, mas só em parte das decisões": "Sim",
            "Usamos algum sistema automatizado, mas sem IA (regras fixas, tipo \"se score < X, recusa\")": "Não",
            "Não usamos IA, mas cruzamos manualmente o score com outras informações": "Não",
            "Não, usamos apenas a consulta de score, sem cruzamento adicional": "Não",
        },
        "niveis": ["Sim", "Não"],
    },
    "CARGO4": {
        "rotulo": "Cargo (4 grupos, com back-coding)", "origem": "Q02_CARGO",
        "backcoding": "Q02_CARGO_OUTRO",
        "niveis": ["Diretoria", "Gerência/Coordenação", "Analista/Operacional", "Outro"],
    },
    "SEGMENTO4": {
        "rotulo": "Segmento (4 grupos, com back-coding)", "origem": "Q04_SEGMENTO",
        "backcoding": "Q04_SEGMENTO_OUTRO",
        "niveis": ["Financeiro", "Varejo", "Indústria e Serviços", "Outro"],
    },
}

# Banners padrão dos cruzamentos (ordem de exibição)
BANNERS_PADRAO = ["PORTE3", "VOLUME4", "PUBLICO", "SEGMENTO4", "CARGO4", "USA_IA2", "CONHECE_ASSERTIVA2", "NPS_GRUPO"]
