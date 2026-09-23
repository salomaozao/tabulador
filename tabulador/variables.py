"""Mapa Canônico de Variáveis do projeto ATIVO.

O conteúdo (PERGUNTAS, FILTROS, BACKCODING, DERIVADAS, BANNERS_PADRAO...) vem do `projeto.py` do
projeto ativado em `projetos.py` (ex.: projetos/assertiva/projeto.py, SESI_cat/projeto.py). Este
módulo só repassa esses nomes (`V.PERGUNTAS` lê o projeto ativo) e guarda os utilitários comuns.

Tipos de pergunta:
  meta           - identificação/controle (não é pergunta)
  unica          - resposta única (uma coluna "Response"; pode ter coluna "Outro. Qual?")
  aberta         - texto livre (com "codificar": True entra no fluxo de categorização)
  multipla       - múltipla escolha dicotômica (uma coluna por item; vira 0/1)
  numerica       - número (com "nps": True ganha promotores/detratores nos cruzamentos)
  grade_numerica - grade 0-10 (uma coluna numérica por atributo)
"""
from __future__ import annotations

import re
import unicodedata
from types import ModuleType

# valores usados quando o projeto não define o nome
_PADROES = {
    "FORMATO": "surveymonkey",
    "FILTROS_DESCRICAO": {},
    "PII_MATCH": [],
    "BACKCODING": {},
    "DERIVADAS": {},
    "BANNERS_PADRAO": [],
    "SAIDA_PLANILHA": None,
    "PLANO": {},
}

_ativo: ModuleType | None = None


def ativar(modulo: ModuleType) -> None:
    global _ativo
    _ativo = modulo


def _p() -> ModuleType:
    if _ativo is None:
        import projetos
        projetos.ativar()
    return _ativo


def __getattr__(nome: str):
    if nome.startswith("__"):
        raise AttributeError(nome)
    mod = _p()
    if hasattr(mod, nome):
        return getattr(mod, nome)
    if nome in _PADROES:
        return _PADROES[nome]
    raise AttributeError(f"o projeto ativo não define {nome!r}")


def norm(texto) -> str:
    """Normaliza texto para matching: sem acento, minúsculo, espaços colapsados."""
    if texto is None:
        return ""
    s = str(texto).replace("–", "-").replace("—", "-")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def slug(texto: str) -> str:
    s = norm(texto)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s.upper()


def por_id(qid: str) -> dict:
    for p in _p().PERGUNTAS:
        if p["id"] == qid:
            return p
        if p.get("outro") and p["outro"]["id"] == qid:
            return {**p["outro"], "tipo": "aberta", "pai": p["id"], "base": p["outro"].get("base", p.get("base", "todos"))}
    raise KeyError(f"Pergunta desconhecida: {qid}")


def perguntas_codificaveis() -> list[str]:
    """Perguntas abertas que passam pelo fluxo de code frame + codificação (inclui back-coding)."""
    ids = [p["id"] for p in _p().PERGUNTAS if p.get("codificar")]
    return list(getattr(_p(), "BACKCODING", {}).keys()) + ids
