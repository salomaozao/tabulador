"""Copia um projeto do Tabulador: pasta nova (configuração + planilha) registrada com outro nome.

Opcionalmente leva junto os resultados (categorias, classificações, base lida). Nunca leva backups,
lixeira, log da IA nem a pasta de teste. O original não é alterado."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import projetos
import variables as V

_NAO_COPIAR_RESULTADOS = {"_backup", "_lixeira", "llm_log"}


def _slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", V.norm(nome)).strip("_") or "projeto"


def _renomear(pasta: Path, nome: str) -> None:
    """Troca o NOME do projeto copiado (projeto.json ou projeto.py)."""
    arq_json = pasta / "projeto.json"
    if arq_json.exists():
        dados = json.loads(arq_json.read_text(encoding="utf-8"))
        dados["NOME"] = nome
        arq_json.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    for arq in (pasta / "src" / "projeto.py", pasta / "codigo" / "projeto.py", pasta / "projeto.py"):
        if arq.exists():
            texto = arq.read_text(encoding="utf-8")
            novo, n = re.subn(r"(?m)^NOME\s*=.*$", lambda _: f"NOME = {nome!r}", texto, count=1)
            if not n:
                raise ValueError(f"Não achei a linha NOME = ... em {arq}.")
            arq.write_text(novo, encoding="utf-8")
            return
    raise FileNotFoundError(f"projeto.json/projeto.py não encontrado em {pasta}.")


def copiar(slug: str, nome: str, copiar_resultados: bool = False) -> dict:
    """Devolve {slug, nome, pasta, resultados_copiados, avisos}."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da cópia.")
    reg = projetos._registro()
    if slug not in reg["projetos"]:
        raise KeyError(f"Projeto desconhecido: {slug}")
    novo_slug = _slug(nome)
    if novo_slug in reg["projetos"]:
        raise ValueError(f"Já existe um projeto com o identificador {novo_slug!r}. Escolha outro nome.")
    if nome.lower() in (p["nome"].strip().lower() for p in projetos.listar()):
        raise ValueError("Já existe um projeto com esse nome.")

    origem = projetos.pasta(slug)
    mod = projetos._carregar(slug)
    saida_origem = Path(getattr(mod, "OUTPUT_DIR", origem / "output")).resolve()
    if saida_origem != (origem / "output").resolve():
        raise ValueError("Este projeto grava os resultados fora da sua pasta (OUTPUT_DIR); a cópia dividiria os mesmos "
                         "resultados com o original. Copie a pasta manualmente e ajuste o OUTPUT_DIR.")
    destino = origem.parent / novo_slug
    if destino.exists():
        raise FileExistsError(f"A pasta {destino} já existe.")

    try:
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("output", "output_teste", "__pycache__", "output_*_excluido_*"))
        avisos = []
        if copiar_resultados and saida_origem.exists():
            shutil.copytree(saida_origem, destino / "output",
                            ignore=lambda d, nomes: [n for n in nomes if Path(d) == saida_origem and n in _NAO_COPIAR_RESULTADOS])
        _renomear(destino, nome)
        copiados_nuvem = 0
        if copiar_resultados:
            import nuvem
            if nuvem.ativa():
                for b in nuvem.listar(slug):
                    nuvem.gravar(novo_slug, b["qid"], b["arquivo"], b["dados"])
                    copiados_nuvem += 1
        from . import registrar as REG
        REG.registrar(destino, novo_slug, validar_antes=False)
    except Exception:
        shutil.rmtree(destino, ignore_errors=True)  # pasta recém-criada por nós; nada do original é tocado
        raise
    if not copiar_resultados:
        avisos.append("Cópia sem resultados: use “Recarregar planilha” para ler a base e começar as categorias do zero.")
    return {"slug": novo_slug, "nome": nome, "pasta": str(destino), "resultados_copiados": bool(copiar_resultados),
            "itens_nuvem": copiados_nuvem, "avisos": avisos}
