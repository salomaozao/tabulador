"""Proteção contra perda da base classificada (PEND-24).

Três camadas, a mesma lógica no modo nuvem (Turso) e no modo arquivo local:

1. guarda      : `verificar` recusa gravar um codificacao.json que perca respostas conferidas por
                 pessoa, ou que encolha mais de 20%, a menos que quem chama libere (`permitir_reducao`).
                 Cada recusa vai para `output/_backup/bloqueios.log`.
2. versões     : `salvar_versao` guarda a versão ANTERIOR de codificacao.json/frame.json antes de
                 sobrescrevê-la (no máximo a cada 15 min na revisão manual; sempre antes de operação
                 em massa). Retenção: 7 dias completos, depois uma por dia até 60 dias.
3. backup      : `backup_se_preciso` copia o projeto inteiro para `output/_backup/` ao abrir o app,
                 no máximo uma vez por dia. `codeframe.restaurar_versao` volta uma versão guardada.

Nada aqui lê nem grava o arquivo "de verdade": quem orquestra é `codeframe._gravar/_remover`
(único ponto de escrita), que passa os dados já lidos para cá.
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
import nuvem

ARQUIVOS = ("codificacao.json", "frame.json")  # os que valem snapshot
LIMITE_ENCOLHER = 0.20  # codificação que perde mais que isto dos itens é recusada...
MIN_ITENS_PERCENTUAL = 10  # ...mas só acima de tantos itens (em base minúscula o % não diz nada)
INTERVALO_VERSAO_S = 15 * 60  # revisão manual: no máximo um snapshot a cada 15 min por arquivo
RETENCAO_COMPLETA = timedelta(days=7)
RETENCAO_DIARIA = timedelta(days=60)
BACKUP_A_CADA = timedelta(hours=24)
BACKUPS_GUARDADOS = 14

_ultima_versao: dict[tuple[str, str, str], float] = {}


class GravacaoSuspeita(RuntimeError):
    """A gravação apagaria trabalho já conferido; foi recusada e nada mudou."""


def conferido_por_humano(item: dict) -> bool:
    """Correção ou confirmação feita por uma pessoa (não conta aceite automático nem regra)."""
    if item.get("primaria") is None or item.get("origem") == "erro":
        return False
    return item.get("origem") == "humano" or (bool(item.get("validado")) and item.get("validado_por") != "auto")


def _humanos(cod: dict | None) -> set:
    return {i.get("rid") for i in (cod or {}).get("itens", []) if conferido_por_humano(i)}


def _pasta_backup() -> Path:
    p = config.PERGUNTAS_OUT.parent / "_backup"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ----------------------------------------------------------------------------- 1. guarda
def avaliar(atual: dict | None, novo: dict | None) -> str | None:
    """Texto do problema se trocar `atual` por `novo` apagaria trabalho; None se está tudo bem."""
    if not atual:
        return None
    perdidos = _humanos(atual) - _humanos(novo)
    if perdidos:
        return f"{len(perdidos)} resposta(s) conferida(s) por pessoa deixariam de constar"
    antes, depois = len(atual.get("itens", [])), len((novo or {}).get("itens", []))
    if antes >= MIN_ITENS_PERCENTUAL and depois < antes * (1 - LIMITE_ENCOLHER):
        return f"a classificação encolheria de {antes} para {depois} respostas"
    return None


def verificar(qid: str, atual: dict | None, novo: dict | None, permitir_reducao: bool = False) -> None:
    if permitir_reducao:
        return
    problema = avaliar(atual, novo)
    if not problema:
        return
    try:
        with (_pasta_backup() / "bloqueios.log").open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{config.PROJETO}\t{qid}\t{problema}\n")
    except OSError:
        traceback.print_exc()
    raise GravacaoSuspeita(
        f"{qid}: gravação recusada, pois {problema}. Nada foi alterado. Se a redução é intencional "
        "(apagar, reabrir, desfazer), use a ação própria da tela; para voltar atrás, use 'Restaurar versão'."
    )


# ----------------------------------------------------------------------------- 2. versões
def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir_versoes(qid: str, arquivo: str) -> Path:
    return _pasta_backup() / "versoes" / qid / arquivo.removesuffix(".json")


def resumo(dados: dict | None) -> dict:
    itens = (dados or {}).get("itens")
    return {"n_itens": len(itens), "n_humano": len(_humanos(dados))} if itens is not None else {"n_categorias": len((dados or {}).get("categorias", []))}


def salvar_versao(qid: str, arquivo: str, dados: dict | None, motivo: str, forcar: bool = False) -> bool:
    """Guarda `dados` (a versão que está prestes a ser substituída). Nunca derruba a gravação:
    se o snapshot falhar, só avisa no console. Devolve se gravou."""
    if not dados or arquivo not in ARQUIVOS:
        return False
    chave = (config.PROJETO, qid, arquivo)
    if not forcar and time.monotonic() - _ultima_versao.get(chave, -INTERVALO_VERSAO_S) < INTERVALO_VERSAO_S:
        return False
    try:
        quando = _agora()
        if nuvem.ativa():
            nuvem.gravar_historico(config.PROJETO, qid, arquivo, dados, quando, motivo, resumo(dados))
        else:
            d = _dir_versoes(qid, arquivo)
            d.mkdir(parents=True, exist_ok=True)
            nome = quando.replace(":", "").replace("+", "_")
            (d / f"{nome}.json").write_text(
                json.dumps({"gravado_em": quando, "motivo": motivo, "dados": dados}, ensure_ascii=False), encoding="utf-8")
        _ultima_versao[chave] = time.monotonic()
        podar(qid, arquivo)
        return True
    except Exception:  # noqa: BLE001 - proteção não pode impedir o trabalho
        traceback.print_exc()
        return False


def versoes(qid: str, arquivo: str) -> list[dict]:
    """Versões guardadas, da mais nova para a mais velha: [{gravado_em, motivo, n_itens, n_humano}]."""
    if nuvem.ativa():
        return nuvem.listar_historico(config.PROJETO, qid, arquivo)
    d = _dir_versoes(qid, arquivo)
    saida = []
    for p in sorted(d.glob("*.json"), reverse=True) if d.exists() else []:
        v = json.loads(p.read_text(encoding="utf-8"))
        saida.append({"gravado_em": v["gravado_em"], "motivo": v.get("motivo", ""), **resumo(v["dados"])})
    return saida


def ler_versao(qid: str, arquivo: str, gravado_em: str) -> dict | None:
    if nuvem.ativa():
        return nuvem.ler_historico(config.PROJETO, qid, arquivo, gravado_em)
    d = _dir_versoes(qid, arquivo)
    for p in d.glob("*.json") if d.exists() else []:
        v = json.loads(p.read_text(encoding="utf-8"))
        if v["gravado_em"] == gravado_em:
            return v["dados"]
    return None


def a_podar(quando: list[str], agora: datetime | None = None) -> list[str]:
    """Quais carimbos (ISO) apagar: tudo com mais de 60 dias; entre 7 e 60 dias, só fica o mais
    novo de cada dia; nos últimos 7 dias nada sai."""
    agora = agora or datetime.now(timezone.utc)
    apagar, vistos = [], set()
    for q in sorted(quando, reverse=True):  # do mais novo para o mais velho
        idade = agora - datetime.fromisoformat(q)
        if idade <= RETENCAO_COMPLETA:
            continue
        dia = q[:10]
        if idade > RETENCAO_DIARIA or dia in vistos:
            apagar.append(q)
        vistos.add(dia)
    return apagar


def podar(qid: str, arquivo: str) -> int:
    quando = [v["gravado_em"] for v in versoes(qid, arquivo)]
    sobra = a_podar(quando)
    if not sobra:
        return 0
    if nuvem.ativa():
        nuvem.apagar_historico(config.PROJETO, qid, arquivo, sobra)
    else:
        for p in _dir_versoes(qid, arquivo).glob("*.json"):
            if json.loads(p.read_text(encoding="utf-8"))["gravado_em"] in sobra:
                p.unlink()
    return len(sobra)


# ----------------------------------------------------------------------------- 3. backup do projeto
def _coletar_projeto() -> tuple[str, list[dict]]:
    if nuvem.ativa():
        return "nuvem", nuvem.listar(config.PROJETO)
    linhas = []
    for p in sorted(config.PERGUNTAS_OUT.glob("*/*.json")) if config.PERGUNTAS_OUT.exists() else []:
        linhas.append({"qid": p.parent.name, "arquivo": p.name, "atualizado_em": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                       "dados": json.loads(p.read_text(encoding="utf-8"))})
    return "local", linhas


def backup_se_preciso(forcar: bool = False) -> Path | None:
    """Ao abrir o app: se o último backup tem mais de 24 h, copia o projeto inteiro (o mesmo formato
    do `python src/nuvem.py -p <projeto> backup`). Guarda os 14 mais recentes. Nunca derruba o app."""
    try:
        origem, linhas = _coletar_projeto()
        pasta = _pasta_backup()
        anteriores = sorted(pasta.glob(f"{origem}_*.json"))
        if not forcar and anteriores and datetime.now() - datetime.fromtimestamp(anteriores[-1].stat().st_mtime) < BACKUP_A_CADA:
            return None
        if not linhas:
            return None
        destino = pasta / f"{origem}_{datetime.now():%Y%m%d_%H%M%S}.json"
        destino.write_text(json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
        for velho in sorted(pasta.glob(f"{origem}_*.json"))[:-BACKUPS_GUARDADOS]:
            velho.unlink()
        return destino
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return None
