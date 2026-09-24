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

# ----------------------------------------------------------------------------- manutenção (linha de comando)
def fechar() -> None:
    """Fecha a conexão (o cliente síncrono mantém uma thread aberta; sem isto um script não termina)."""
    global _cliente, _tabela_pronta
    if _cliente is not None:
        _cliente.close()
    _cliente, _tabela_pronta = None, False


def listar(projeto: str) -> list[dict]:
    rs = _obter_cliente().execute("SELECT qid, arquivo, atualizado_em, dados FROM blobs WHERE projeto = ? ORDER BY qid, arquivo", [projeto])
    return [{"qid": r[0], "arquivo": r[1], "atualizado_em": r[2], "dados": json.loads(r[3])} for r in rs.rows]


def apagar_projeto(projeto: str) -> int:
    """Apaga TODAS as linhas do projeto na nuvem (faça o backup antes: `backup`)."""
    return _obter_cliente().execute("DELETE FROM blobs WHERE projeto = ?", [projeto]).rows_affected


def subir_pasta(projeto: str, pasta_perguntas) -> list[tuple[str, str]]:
    """Sobe os JSON de <pasta>/<QID>/*.json (os mesmos que codeframe grava) para a nuvem."""
    from pathlib import Path
    enviados = []
    for d in sorted(p for p in Path(pasta_perguntas).iterdir() if p.is_dir()):
        for arq in sorted(d.glob("*.json")):
            gravar(projeto, d.name, arq.name, json.loads(arq.read_text(encoding="utf-8")))
            enviados.append((d.name, arq.name))
    return enviados


def _main() -> None:
    """python nuvem.py -p sesi status | backup | subir [--limpar-antes]"""
    import argparse
    from pathlib import Path

    import projetos
    ap = argparse.ArgumentParser(description="Banco em nuvem do Tabulador (Turso)")
    ap.add_argument("-p", "--projeto", required=True)
    ap.add_argument("acao", choices=["status", "backup", "subir"])
    ap.add_argument("--limpar-antes", action="store_true", help="subir: apaga o que o projeto tem na nuvem antes (depois do backup)")
    a = ap.parse_args()
    projetos.ativar(a.projeto)
    if not config.TURSO_URL:
        raise SystemExit("Nuvem não configurada (TABULADOR_TURSO_URL no .env).")
    try:
        linhas = listar(a.projeto)
        print(f"nuvem: {len(linhas)} arquivo(s) do projeto '{a.projeto}'")
        for r in linhas:
            print(f"  {r['qid']:>6} {r['arquivo']:<22} {r['atualizado_em']}")
        if a.acao in ("backup", "subir"):
            destino = config.SAIDA_REAL / "_backup" / f"nuvem_{datetime.now():%Y%m%d_%H%M%S}.json"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps(linhas, ensure_ascii=False), encoding="utf-8")
            print(f"backup: {destino}")
        if a.acao == "subir":
            if a.limpar_antes:
                print(f"apagadas: {apagar_projeto(a.projeto)} linha(s)")
            enviados = subir_pasta(a.projeto, Path(config.SAIDA_REAL) / "perguntas")
            print(f"enviados: {len(enviados)} arquivo(s) de {len({q for q, _ in enviados})} pergunta(s)")
            # confere: o que está na nuvem agora é igual ao arquivo local
            for qid, nome in enviados:
                local = json.loads((Path(config.SAIDA_REAL) / "perguntas" / qid / nome).read_text(encoding="utf-8"))
                if ler(a.projeto, qid, nome) != local:
                    raise SystemExit(f"DIFERENTE depois de subir: {qid}/{nome}")
            print("conferido: nuvem igual aos arquivos locais")
    finally:
        fechar()


if __name__ == "__main__":
    _main()
