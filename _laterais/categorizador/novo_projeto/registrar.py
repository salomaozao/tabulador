"""Pasta do projeto novo (planilha em data/, perfil em output/, projeto.json) e registro em projetos.json.
O registro só acontece se a validação passar."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import projetos
import variables as V
from . import perfil as PF
from . import rascunho as R
from .validar import relatorio, validar


def slug_de(pasta) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", V.norm(Path(pasta).name)).strip("_")
    return re.sub(r"_cat$", "", s) or "projeto"


def pasta_perfil(pasta: Path) -> Path:
    return Path(pasta) / "output" / "novo_projeto"  # output/ fica fora do git (tem amostras de respostas)


def copiar_planilha(pasta: Path, planilha: Path) -> Path:
    """Copia a planilha para <pasta>/data/ (se ainda não estiver dentro da pasta)."""
    pasta, planilha = Path(pasta).resolve(), Path(planilha).resolve()
    try:
        planilha.relative_to(pasta)
        return planilha
    except ValueError:
        destino = pasta / "data" / planilha.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists():
            shutil.copy2(planilha, destino)
        return destino


def criar_rascunho(pasta, planilha, nome: str, cliente: str | None = None, aba=None, forcar: bool = False) -> tuple[dict, dict]:
    """Planilha -> perfil + projeto.json de rascunho (sem IA). Devolve (perfil, projeto)."""
    pasta = Path(pasta).resolve()
    arq = pasta / "projeto.json"
    if (arq.exists() or (pasta / "projeto.py").exists()) and not forcar:
        raise FileExistsError(f"Já existe projeto em {pasta} (use forcar para substituir o projeto.json).")
    pasta.mkdir(parents=True, exist_ok=True)
    fonte = copiar_planilha(pasta, planilha)
    perfil = PF.perfilar(fonte, aba)
    salvar_json(pasta_perfil(pasta) / "perfil.json", perfil)
    projeto = R.gerar(perfil, pasta, nome, cliente)
    salvar_json(arq, projeto)
    return perfil, projeto


def salvar_json(arq: Path, dados) -> None:
    arq = Path(arq)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def registrar(pasta, slug: str | None = None, ativar: bool = False) -> str:
    pasta = Path(pasta).resolve()
    res = validar(pasta)
    if not res["valido"]:
        raise ValueError(relatorio(res))
    slug = slug or slug_de(pasta)
    reg = projetos._registro()
    if slug in reg["projetos"] and projetos.pasta(slug) != pasta:
        raise ValueError(f"Já existe um projeto {slug!r} em outra pasta ({projetos.pasta(slug)}). Escolha outro nome.")
    try:
        caminho = os.path.relpath(pasta, projetos._DIR)
    except ValueError:  # outro disco
        caminho = str(pasta)
    reg["projetos"][slug] = caminho.replace("\\", "/")
    if ativar:
        reg["ativo"] = slug
    projetos.ARQUIVO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    projetos._modulos.pop(slug, None)
    return slug
