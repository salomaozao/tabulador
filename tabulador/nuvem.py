"""Armazenamento em nuvem (Turso/libSQL) para os arquivos por pergunta do code frame.

Prova de conceito: guarda cada JSON que `codeframe._ler/_gravar` gravaria em disco (respostas.json,
frame.json, codificacao.json, instrucoes.json...) como uma linha da tabela `blobs`, identificada por
projeto+pergunta+arquivo. Assim vários usuários, em máquinas diferentes, enxergam a mesma revisão
sem precisar copiar a pasta `output/` de um pro outro.

Ativa automaticamente quando `TABULADOR_TURSO_URL` (e, se o banco não for local, `TABULADOR_TURSO_TOKEN`)
estão configurados no `.env`; senão o Tabulador continua gravando em arquivo local, como sempre.
Ver instruções para criar o banco e pegar as credenciais em `docs/nuvem_turso.md`.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

import config

_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS blobs (
    projeto TEXT NOT NULL,
    qid TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    dados TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (projeto, qid, arquivo)
)
"""

_lock = threading.Lock()
_cliente = None
_tabela_pronta = False


def ativa() -> bool:
    if not config.TURSO_URL:
        return False
    # testes automáticos, validação de projeto novo e modo teste gravam numa pasta temporária/separada:
    # nunca podem ler nem gravar no banco de verdade (só num banco local de teste, 'file:...')
    temporario = bool(os.getenv("TABULADOR_OUTPUT")) or config.modo_teste()
    return not temporario or config.TURSO_URL.startswith("file:")


def _url_http(url: str) -> str:
    """O painel do Turso entrega a URL como libsql://... (websocket). Nesta rede o handshake de
    websocket falha (erro 400 no aperto de mão) mas HTTP simples funciona, então troca o esquema
    para não depender de cada pessoa descobrir isso na mão."""
    for esquema, troca in (("libsql://", "https://"), ("wss://", "https://"), ("ws://", "http://")):
        if url.startswith(esquema):
            return troca + url[len(esquema):]
    return url


def _obter_cliente():
    global _cliente, _tabela_pronta
    if _cliente is not None and _tabela_pronta:
        return _cliente
    with _lock:
        if _cliente is None:
            import libsql_client  # importado aqui: só é obrigatório quando a nuvem está ativa

            _cliente = libsql_client.create_client_sync(
                url=_url_http(config.TURSO_URL),
                auth_token=config.TURSO_TOKEN or None,
            )
        if not _tabela_pronta:
            _cliente.execute(_CRIAR_TABELA)
            _tabela_pronta = True
    return _cliente


def ler(projeto: str, qid: str, arquivo: str) -> dict | None:
    rs = _obter_cliente().execute(
        "SELECT dados FROM blobs WHERE projeto = ? AND qid = ? AND arquivo = ?",
        [projeto, qid, arquivo],
    )
    if not rs.rows:
        return None
    return json.loads(rs.rows[0][0])


def existe(projeto: str, qid: str, arquivo: str) -> bool:
    rs = _obter_cliente().execute(
        "SELECT 1 FROM blobs WHERE projeto = ? AND qid = ? AND arquivo = ?",
        [projeto, qid, arquivo],
    )
    return bool(rs.rows)


def remover(projeto: str, qid: str, arquivo: str) -> bool:
    """Apaga de verdade (não tem lixeira na nuvem — diferente do modo arquivo local)."""
    rs = _obter_cliente().execute(
        "DELETE FROM blobs WHERE projeto = ? AND qid = ? AND arquivo = ?",
        [projeto, qid, arquivo],
    )
    return bool(rs.rows_affected)


def gravar(projeto: str, qid: str, arquivo: str, dados: dict) -> None:
    agora = datetime.now(timezone.utc).isoformat()
    _obter_cliente().execute(
        "INSERT INTO blobs (projeto, qid, arquivo, dados, atualizado_em) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (projeto, qid, arquivo) DO UPDATE SET dados = excluded.dados, atualizado_em = excluded.atualizado_em",
        [projeto, qid, arquivo, json.dumps(dados, ensure_ascii=False), agora],
    )
