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
import time
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

_CRIAR_TABELA_PRESENCA = """
CREATE TABLE IF NOT EXISTS presenca (
    projeto TEXT NOT NULL,
    qid TEXT NOT NULL,
    usuario TEXT NOT NULL,
    visto_em TEXT NOT NULL,
    PRIMARY KEY (projeto, qid, usuario)
)
"""

# Presença do projeto inteiro (PEND-09), separada da `presenca` por pergunta acima de propósito:
# tabela nova em vez de generalizar a existente, para não arriscar a que já está em produção durante
# o campo. `sessao_id` é por aba (gerado em memória no navegador, não persiste), `nome_exibicao` é
# autodeclarado (sem login). `origem` já existe no schema para a IA por CLI se anunciar no futuro, mas
# hoje só "browser" é populado — ver decisão do conselho de IAs em PEND-09.
_CRIAR_TABELA_PRESENCA_PROJETO = """
CREATE TABLE IF NOT EXISTS presenca_projeto (
    projeto TEXT NOT NULL,
    sessao_id TEXT NOT NULL,
    nome_exibicao TEXT NOT NULL,
    origem TEXT NOT NULL,
    localizacao TEXT NOT NULL,
    atualizado_em TEXT NOT NULL,
    PRIMARY KEY (projeto, sessao_id)
)
"""

JANELA_PRESENCA_S = 30  # o navegador manda um heartbeat a cada 12s: folga para perder 1 batida

_lock = threading.Lock()
_cliente = None
_tabela_pronta = False

# Cache curto de leitura (chave: projeto/qid/arquivo -> (expira_em, dados)). Cada pergunta aberta na
# interface lê o mesmo arquivo mais de uma vez na mesma requisição (ver codeframe.frame/_exigir_frame,
# coding.tabela) — sem cache isso vira ida e volta de rede ao Turso repetida, e é o principal motivo de
# "mudar de aba/pergunta" ficar lento com a nuvem ativa. TTL curto (poucos segundos) limita o quanto uma
# gravação de outra pessoa pode ficar "atrasada" pra quem só está lendo — grava (`gravar`/`remover`)
# sempre atualiza o cache na hora (write-through), então as próprias mudanças de quem está usando nunca
# ficam desatualizadas; só a leitura de mudança feita por OUTRO processo pode esperar até o TTL.
_CACHE_TTL_S = 5.0
_cache: dict[tuple[str, str, str], tuple[float, dict | None]] = {}


def _cache_get(chave: tuple[str, str, str]):
    item = _cache.get(chave)
    if item is None:
        return False, None
    expira, dados = item
    if time.monotonic() >= expira:
        return False, None
    return True, dados


def _cache_set(chave: tuple[str, str, str], dados: dict | None) -> None:
    _cache[chave] = (time.monotonic() + _CACHE_TTL_S, dados)


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
            _cliente.execute(_CRIAR_TABELA_PRESENCA)
            _cliente.execute(_CRIAR_TABELA_PRESENCA_PROJETO)
            _tabela_pronta = True
    return _cliente


def ler(projeto: str, qid: str, arquivo: str) -> dict | None:
    chave = (projeto, qid, arquivo)
    achou, dados = _cache_get(chave)
    if achou:
        return dados
    rs = _obter_cliente().execute(
        "SELECT dados FROM blobs WHERE projeto = ? AND qid = ? AND arquivo = ?",
        [projeto, qid, arquivo],
    )
    dados = json.loads(rs.rows[0][0]) if rs.rows else None
    _cache_set(chave, dados)
    return dados


def existe(projeto: str, qid: str, arquivo: str) -> bool:
    achou, dados = _cache_get((projeto, qid, arquivo))
    if achou:
        return dados is not None
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
    _cache_set((projeto, qid, arquivo), None)
    return bool(rs.rows_affected)


def gravar(projeto: str, qid: str, arquivo: str, dados: dict) -> None:
    agora = datetime.now(timezone.utc).isoformat()
    _obter_cliente().execute(
        "INSERT INTO blobs (projeto, qid, arquivo, dados, atualizado_em) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (projeto, qid, arquivo) DO UPDATE SET dados = excluded.dados, atualizado_em = excluded.atualizado_em",
        [projeto, qid, arquivo, json.dumps(dados, ensure_ascii=False), agora],
    )
    _cache_set((projeto, qid, arquivo), dados)

# ----------------------------------------------------------------------------- manutenção (linha de comando)
def fechar() -> None:
    """Fecha a conexão (o cliente síncrono mantém uma thread aberta; sem isto um script não termina)."""
    global _cliente, _tabela_pronta
    if _cliente is not None:
        _cliente.close()
    _cliente, _tabela_pronta = None, False


def status(projeto: str) -> dict:
    """Para o topo da interface: se a nuvem está configurada, se a conexão está de pé agora e a
    última vez que ALGUÉM (qualquer pessoa da equipe) gravou algo desse projeto."""
    if not ativa():
        return {"ativa": False, "conectada": False, "ultima_sincronizacao": None}
    try:
        rs = _obter_cliente().execute("SELECT MAX(atualizado_em) FROM blobs WHERE projeto = ?", [projeto])
        return {"ativa": True, "conectada": True, "ultima_sincronizacao": rs.rows[0][0] if rs.rows else None}
    except Exception:
        return {"ativa": True, "conectada": False, "ultima_sincronizacao": None}


def marcar_presenca(projeto: str, qid: str, usuario: str) -> list[str]:
    """'usuario' está vendo 'qid' agora: grava o heartbeat e devolve quem MAIS (excluindo ele) está
    ativo na mesma pergunta agora, para avisar sobre edição simultânea (a última gravação vence)."""
    agora = datetime.now(timezone.utc)
    c = _obter_cliente()
    c.execute(
        "INSERT INTO presenca (projeto, qid, usuario, visto_em) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (projeto, qid, usuario) DO UPDATE SET visto_em = excluded.visto_em",
        [projeto, qid, usuario, agora.isoformat()],
    )
    rs = c.execute("SELECT usuario, visto_em FROM presenca WHERE projeto = ? AND qid = ?", [projeto, qid])
    return [u for u, visto in rs.rows if u != usuario and (agora - datetime.fromisoformat(visto)).total_seconds() <= JANELA_PRESENCA_S]


def sair_presenca(projeto: str, qid: str, usuario: str) -> None:
    _obter_cliente().execute("DELETE FROM presenca WHERE projeto = ? AND qid = ? AND usuario = ?", [projeto, qid, usuario])


def marcar_presenca_projeto(projeto: str, sessao_id: str, nome_exibicao: str, localizacao: str, origem: str = "browser") -> list[dict]:
    """'sessao_id' (uma aba) está em 'localizacao' (qid:<id> | painel | resultados | usage | gerenciar)
    agora: grava o heartbeat e devolve as OUTRAS sessões ativas no projeto inteiro (sidebar de
    presença, PEND-09) — não confundir com `marcar_presenca` (por pergunta, mais antiga)."""
    agora = datetime.now(timezone.utc)
    c = _obter_cliente()
    c.execute(
        "INSERT INTO presenca_projeto (projeto, sessao_id, nome_exibicao, origem, localizacao, atualizado_em) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (projeto, sessao_id) DO UPDATE SET "
        "nome_exibicao = excluded.nome_exibicao, origem = excluded.origem, localizacao = excluded.localizacao, "
        "atualizado_em = excluded.atualizado_em",
        [projeto, sessao_id, nome_exibicao, origem, localizacao, agora.isoformat()],
    )
    rs = c.execute("SELECT sessao_id, nome_exibicao, origem, localizacao, atualizado_em FROM presenca_projeto WHERE projeto = ?", [projeto])
    return [
        {"nome_exibicao": nome, "origem": org, "localizacao": loc}
        for sid, nome, org, loc, visto in rs.rows
        if sid != sessao_id and (agora - datetime.fromisoformat(visto)).total_seconds() <= JANELA_PRESENCA_S
    ]


def sair_presenca_projeto(projeto: str, sessao_id: str) -> None:
    _obter_cliente().execute("DELETE FROM presenca_projeto WHERE projeto = ? AND sessao_id = ?", [projeto, sessao_id])


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
