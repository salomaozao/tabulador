"""Projetos do tabulador.

Cada projeto é uma pasta com um `projeto.py` (planilha-fonte, contexto para a IA, perguntas,
filtros, banners) ou um `projeto.json` declarativo (criado pelo assistente "Novo projeto";
formato em novo_projeto/FORMATO.md). A lista fica em `projetos.json` (caminhos relativos a esta pasta):

  {"ativo": "sesi", "projetos": {"assertiva": "projetos/assertiva", "sesi": "../../SESI_cat"}}

O projeto ativo é escolhido por, nesta ordem: argumento de `ativar()`, variável de ambiente
TABULADOR_PROJETO, campo "ativo" do projetos.json, primeiro da lista.
As saídas de cada projeto ficam em `<pasta do projeto>/output` (salvo se o projeto definir OUTPUT_DIR).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent
ARQUIVO = _DIR / "projetos.json"
_modulos: dict = {}


def _registro() -> dict:
    if ARQUIVO.exists():
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    return {"ativo": "assertiva", "projetos": {"assertiva": "projetos/assertiva"}}


def pasta(slug: str) -> Path:
    reg = _registro()["projetos"]
    if slug not in reg:
        raise KeyError(f"Projeto desconhecido: {slug}. Disponíveis: {', '.join(reg)}")
    return (_DIR / reg[slug]).resolve()


def _carregar(slug: str):
    if slug not in _modulos:
        arq = pasta(slug) / "projeto.py"
        if not arq.exists() and (pasta(slug) / "projeto.json").exists():
            from novo_projeto import projeto_json  # projeto declarativo (criado pelo assistente)
            _modulos[slug] = projeto_json.carregar(pasta(slug) / "projeto.json")
            return _modulos[slug]
        if not arq.exists():
            raise FileNotFoundError(f"{arq} (ou projeto.json) não existe")
        spec = importlib.util.spec_from_file_location(f"projeto_{slug}", arq)
        mod = importlib.util.module_from_spec(spec)
        antes, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # sem __pycache__ na pasta do projeto
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.dont_write_bytecode = antes
        _modulos[slug] = mod
    return _modulos[slug]


def listar() -> list[dict]:
    saida = []
    for slug in _registro()["projetos"]:
        try:
            mod = _carregar(slug)
            saida.append({"slug": slug, "nome": getattr(mod, "NOME", slug), "ok": True})
        except Exception as e:  # projeto mal configurado não derruba os outros
            saida.append({"slug": slug, "nome": slug, "ok": False, "erro": str(e)})
    return saida


def padrao() -> str:
    reg = _registro()
    return os.getenv("TABULADOR_PROJETO") or reg.get("ativo") or next(iter(reg["projetos"]))


def ativar(slug: str | None = None, lembrar: bool = False) -> None:
    """Carrega o projeto e aponta config.* e variables.* para ele."""
    import config
    import variables as V

    slug = slug or padrao()
    mod = _carregar(slug)
    p = pasta(slug)
    config.PROJETO = slug
    config.PROJETO_PASTA = p
    config.NOME_PROJETO = getattr(mod, "NOME", slug)
    config.CLIENTE = getattr(mod, "CLIENTE", config.NOME_PROJETO)
    config.FONTE_XLSX = Path(getattr(mod, "FONTE_XLSX"))
    config.ABAS = getattr(mod, "ABAS", {})
    config.CONTEXTO_PROJETO = getattr(mod, "CONTEXTO_PROJETO", "")
    raiz_teste = os.getenv("TABULADOR_OUTPUT")  # testes automatizados: tudo numa pasta temporária
    saida = Path(raiz_teste) / slug if raiz_teste else Path(getattr(mod, "OUTPUT_DIR", p / "output"))
    config.SAIDA_REAL = saida
    if config.modo_teste():
        # modo teste (IA simulada): resultados numa pasta à parte, nunca misturados com os reais;
        # na primeira vez copia a base já lida, para não precisar reler a planilha
        teste = saida.parent / (saida.name + "_teste")
        if not (teste / "base" / "base.json").exists() and (saida / "base" / "base.json").exists():
            shutil.copytree(saida / "base", teste / "base", dirs_exist_ok=True)
        saida = teste
    config.definir_saida(saida)
    config.carregar_env_extra(getattr(mod, "ENV_EXTRA", None))
    V.ativar(mod)
    if lembrar:
        reg = _registro()
        reg["ativo"] = slug
        ARQUIVO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
