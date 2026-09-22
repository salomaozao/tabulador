"""Configuração central do pipeline (caminhos, planilha-fonte, LLM).

Os valores que dependem do projeto (NOME, FONTE_XLSX, ABAS, OUTPUT_DIR e subpastas,
CONTEXTO_PROJETO, CLIENTE) são preenchidos por `projetos.ativar()` a partir do `projeto.py` do
projeto ativo. Tudo que o pipeline escreve fica no OUTPUT_DIR do projeto; a planilha-fonte é
somente leitura.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# ---- projeto ativo (preenchido por projetos.ativar) ---------------------------
PROJETO = None  # slug
NOME_PROJETO = ""
CLIENTE = ""
PROJETO_PASTA: Path = BASE_DIR
FONTE_XLSX: Path = BASE_DIR / "fonte.xlsx"
ABAS: dict = {}
CONTEXTO_PROJETO = ""
OUTPUT_DIR: Path = BASE_DIR / "output"
SAIDA_REAL: Path = OUTPUT_DIR  # pasta de resultados reais (no modo teste OUTPUT_DIR aponta para <saída>_teste)
BASE_OUT = PERGUNTAS_OUT = CODEBOOK_OUT = CRUZAMENTOS_OUT = LLM_LOG_OUT = OUTPUT_DIR


def definir_saida(pasta: Path) -> None:
    global OUTPUT_DIR, BASE_OUT, PERGUNTAS_OUT, CODEBOOK_OUT, CRUZAMENTOS_OUT, LLM_LOG_OUT
    OUTPUT_DIR = Path(pasta)
    BASE_OUT = OUTPUT_DIR / "base"
    PERGUNTAS_OUT = OUTPUT_DIR / "perguntas"
    CODEBOOK_OUT = OUTPUT_DIR / "codebook"
    CRUZAMENTOS_OUT = OUTPUT_DIR / "cruzamentos"
    LLM_LOG_OUT = OUTPUT_DIR / "llm_log"


# ---- LLM -------------------------------------------------------------------
# categorizador/.env (gravado pela tela "Configurar IA") tem prioridade; projetos podem indicar
# um .env extra (ex.: o do categorizador legado, somente leitura) via ENV_EXTRA.
load_dotenv(ENV_FILE)
# chave padrão da equipe: .env do categorizador V3 na pasta do SharePoint
# "IA - Jumppi/Categorização de Respostas Abertas", sincronizada como atalho no OneDrive
_ONEDRIVE = BASE_DIR.parents[2]  # ...\OneDrive - INSTITUTO OLHAR - PESQUISA E INFORMACAO ESTRATEGICA LTDA
ENV_EQUIPE = [
    p / "Projeto IA" / sub / ".env"
    for p in sorted((_ONEDRIVE / "Shortcuts").glob("*Categoriza*Respostas Abertas*"))
    for sub in ("V3", "CategorizadorDeRespostasAbertas1")
]
for _env in ENV_EQUIPE:
    if os.getenv("OPENAI_API_KEY"):
        break
    if _env.exists():
        load_dotenv(_env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
# provedores compatíveis com a API da OpenAI (Gemini, Groq, OpenRouter, DeepSeek...): muda só a URL
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_PROVEDOR = os.getenv("OPENAI_PROVEDOR", "openai")

PROVEDORES = {
    "openai": {"nome": "OpenAI (GPT-4.1, GPT-4o mini…)", "base_url": None, "modelo": "gpt-4.1",
               "modelos": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"], "chave_prefixo": "sk-",
               "link": "https://platform.openai.com/api-keys"},
    "gemini": {"nome": "Google Gemini (AI Studio — tem plano gratuito)", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "modelo": "gemini-2.5-flash", "modelos": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.5-pro"],
               "chave_prefixo": "AIza", "link": "https://aistudio.google.com/apikey"},
    "groq": {"nome": "Groq (GPT-OSS 120B, Qwen 27B — gratuito, hiper rápido)", "base_url": "https://api.groq.com/openai/v1",
             "modelo": "openai/gpt-oss-120b", "modelos": ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
             "chave_prefixo": "gsk_", "link": "https://console.groq.com/keys"},
    "openrouter": {"nome": "OpenRouter (modelos gratuitos e pagos)", "base_url": "https://openrouter.ai/api/v1",
                   "modelo": "meta-llama/llama-3.3-70b-instruct:free",
                   "modelos": ["meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat-v3-0324:free", "google/gemini-2.5-flash", "openai/gpt-4.1-mini"],
                   "chave_prefixo": "sk-or-", "link": "https://openrouter.ai/keys"},
    "deepseek": {"nome": "DeepSeek (econômico)", "base_url": "https://api.deepseek.com", "modelo": "deepseek-chat",
                 "modelos": ["deepseek-chat"], "chave_prefixo": "sk-", "link": "https://platform.deepseek.com/api_keys"},
    "personalizado": {"nome": "Personalizado (qualquer API compatível com a OpenAI)", "base_url": "", "modelo": "",
                      "modelos": [], "chave_prefixo": "", "link": ""},
    "simulado": {"nome": "🧪 Modo teste (valores simulados, sem IA)", "base_url": "", "modelo": "simulado",
                 "modelos": ["simulado"], "chave_prefixo": "", "link": "", "sem_chave": True},
}


def modo_teste() -> bool:
    return OPENAI_PROVEDOR == "simulado"


def gravar_env(novos: dict) -> None:
    """Grava/atualiza variáveis no categorizador/.env e no ambiente atual."""
    linhas = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    saida = [l for l in linhas if l.split("=", 1)[0].strip() not in novos] + [f"{k}={v}" for k, v in novos.items()]
    ENV_FILE.write_text("\n".join(saida) + "\n", encoding="utf-8")
    os.environ.update({k: str(v) for k, v in novos.items()})


def alternar_modo_teste(ativo: bool) -> None:
    """Liga o modo teste guardando provedor/modelo atuais; desliga restaurando-os."""
    global OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, OPENAI_PROVEDOR
    if ativo and not modo_teste():
        gravar_env({"CATEGORIZADOR_ANTES_TESTE_PROVEDOR": OPENAI_PROVEDOR, "CATEGORIZADOR_ANTES_TESTE_MODELO": OPENAI_MODEL,
                    "CATEGORIZADOR_ANTES_TESTE_URL": OPENAI_BASE_URL or ""})
        salvar_llm(provedor="simulado", modelo="simulado")
    elif not ativo and modo_teste():
        prov = os.getenv("CATEGORIZADOR_ANTES_TESTE_PROVEDOR") or "openai"
        if prov not in PROVEDORES or prov == "simulado":
            prov = "openai"
        modelo = os.getenv("CATEGORIZADOR_ANTES_TESTE_MODELO") or PROVEDORES[prov]["modelo"] or "gpt-4.1"
        url = os.getenv("CATEGORIZADOR_ANTES_TESTE_URL", PROVEDORES[prov]["base_url"] or "")
        try:
            salvar_llm(provedor=prov, modelo=modelo, base_url=url)
        except ValueError:  # provedor anterior sem chave guardada: sai do teste mesmo assim (a IA pedirá a chave)
            gravar_env({"OPENAI_PROVEDOR": prov, "OPENAI_MODEL": modelo, "OPENAI_BASE_URL": url, "OPENAI_API_KEY": ""})
            OPENAI_PROVEDOR, OPENAI_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY = prov, modelo, url or None, None
LLM_TEMPERATURA = 0
LLM_LOTE = int(os.getenv("ASSERTIVA_LOTE", "30"))  # respostas únicas por chamada de codificação
LLM_PARALELO = int(os.getenv("CATEGORIZADOR_PARALELO", "4"))  # chamadas simultâneas à OpenAI
MAX_RESPOSTAS_INDUCAO = int(os.getenv("CATEGORIZADOR_MAX_INDUCAO", "1500"))  # amostra lida ao propor categorias


def carregar_env_extra(caminho: Path | None) -> None:
    global OPENAI_API_KEY
    if not OPENAI_API_KEY and caminho and Path(caminho).exists():
        load_dotenv(caminho)
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _chave_var(provedor: str) -> str:
    return f"CATEGORIZADOR_CHAVE_{provedor.upper()}"


# variáveis de ambiente padrão de cada provedor (se já existirem no computador, são usadas sozinhas)
CHAVES_PADRAO = {
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "groq": ("GROQ_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
}


def _chave_guardada(provedor: str) -> str | None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    return os.getenv(_chave_var(provedor)) or next((os.getenv(v) for v in CHAVES_PADRAO.get(provedor, ()) if os.getenv(v)), None)


def chave_salva(provedor: str) -> bool:
    """Já existe chave guardada para este provedor? (cada provedor guarda a sua)."""
    if PROVEDORES.get(provedor, {}).get("sem_chave") or _chave_guardada(provedor):
        return True
    return provedor == OPENAI_PROVEDOR and bool(OPENAI_API_KEY)


def salvar_llm(chave: str | None = None, modelo: str | None = None, base_url: str | None = None, provedor: str | None = None) -> None:
    """Grava provedor/chave/modelo/URL em categorizador/.env (usado pela interface) e aplica na hora.
    Cada provedor guarda a própria chave (CATEGORIZADOR_CHAVE_<PROVEDOR>); trocar de provedor sem
    colar chave reaproveita a última chave daquele provedor."""
    global OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, OPENAI_PROVEDOR
    linhas = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    novos: dict = {}
    prov_antigo = OPENAI_PROVEDOR
    if provedor:
        provedor = provedor.strip().lower()
        if provedor not in PROVEDORES:
            raise ValueError(f"Provedor desconhecido: {provedor}")
        novos["OPENAI_PROVEDOR"] = provedor
        if base_url is None:
            base_url = PROVEDORES[provedor]["base_url"] or ""
    prov = provedor or OPENAI_PROVEDOR
    if prov != prov_antigo and OPENAI_API_KEY and not os.getenv(_chave_var(prov_antigo)) and not PROVEDORES.get(prov_antigo, {}).get("sem_chave"):
        novos[_chave_var(prov_antigo)] = OPENAI_API_KEY  # guarda a chave do provedor anterior
    if PROVEDORES[prov].get("sem_chave"):
        pass  # modo teste: não precisa de chave (a chave atual continua guardada para quando voltar)
    elif chave:
        novos["OPENAI_API_KEY"] = chave.strip()
        novos[_chave_var(prov)] = chave.strip()
    elif prov != prov_antigo:
        guardada = _chave_guardada(prov)
        if not guardada:
            raise ValueError(f"Cole a chave do provedor {PROVEDORES[prov]['nome']} para trocar de provedor.")
        novos["OPENAI_API_KEY"] = guardada
    if modelo:
        novos["OPENAI_MODEL"] = modelo.strip()
    elif provedor and prov != prov_antigo and PROVEDORES[prov]["modelo"]:
        novos["OPENAI_MODEL"] = PROVEDORES[prov]["modelo"]
    if base_url is not None:
        novos["OPENAI_BASE_URL"] = base_url.strip()
    saida = [l for l in linhas if l.split("=", 1)[0].strip() not in novos]
    saida += [f"{k}={v}" for k, v in novos.items()]
    ENV_FILE.write_text("\n".join(saida) + "\n", encoding="utf-8")
    for k, v in novos.items():
        os.environ[k] = v
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
    OPENAI_PROVEDOR = os.getenv("OPENAI_PROVEDOR", "openai")


def garantir_pastas() -> None:
    for p in (OUTPUT_DIR, BASE_OUT, PERGUNTAS_OUT, CODEBOOK_OUT, CRUZAMENTOS_OUT, LLM_LOG_OUT):
        p.mkdir(parents=True, exist_ok=True)


# ativa o projeto padrão (CATEGORIZADOR_PROJETO ou o último usado, em projetos.json)
import projetos  # noqa: E402

projetos.ativar()
