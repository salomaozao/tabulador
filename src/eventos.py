"""Log de eventos append-only (PEND-26): quem fez o quê, quando, com qual modelo e em qual versão do quadro.

Só se acrescenta: nada aqui lê para decidir comportamento nem apaga. Com a nuvem ativa vai para a tabela
`eventos` do Turso; sem ela, para `output/eventos.jsonl`. Registrar NUNCA derruba a operação que está
sendo registrada (como em protecao.salvar_versao): se falhar, só avisa no console.

Base do painel de administração (PEND-27) e da comparação de modelos (PEND-30, PEND-32).
"""
from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime
from pathlib import Path

import config
import nuvem


_local = threading.local()


def definir_quem(nome: str | None) -> None:
    """Nome autodeclarado na aba que fez a requisição em curso (o app chama isto antes de cada requisição)."""
    _local.nome = nome or None


def quem() -> str:
    """Quem está agindo: o nome declarado na aba, ou o usuário desta máquina."""
    return getattr(_local, "nome", None) or config.USUARIO


def modelo_atual() -> str:
    """'provedor:modelo' da IA em uso agora (o que carimba classificado_por)."""
    return f"{config.OPENAI_PROVEDOR}:{config.OPENAI_MODEL}"


def _arquivo() -> Path:
    return config.PERGUNTAS_OUT.parent / "eventos.jsonl"


def registrar(qid: str | None, acao: str, alvo=None, de=None, para=None, modelo: str | None = None,
              frame_versao: int | None = None, por: str | None = None, **detalhe) -> None:
    """Acrescenta um evento. `alvo` = rid, código de categoria ou lista deles; `de`/`para` = antes e depois;
    `detalhe` = o resto (quantidades, motivo, rids em bloco). `por` só é passado quando não é quem usa a tela
    (ex.: 'ia:gemini:gemini-2.5-flash' ou 'auto')."""
    ev = {"quando": datetime.now().isoformat(timespec="seconds"), "projeto": config.PROJETO, "qid": qid,
          "quem": por or quem(), "acao": acao, "alvo": alvo, "de": de, "para": para, "modelo": modelo,
          "frame_versao": frame_versao, "detalhe": detalhe or None}
    try:
        if nuvem.ativa():
            nuvem.gravar_evento(ev)
        else:
            a = _arquivo()
            a.parent.mkdir(parents=True, exist_ok=True)
            with a.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - telemetria não pode impedir o trabalho
        traceback.print_exc()


def listar(qid: str | None = None, limite: int = 500) -> list[dict]:
    """Eventos do projeto (mais novos primeiro), opcionalmente de uma pergunta."""
    if nuvem.ativa():
        return nuvem.listar_eventos(config.PROJETO, qid, limite)
    a = _arquivo()
    if not a.exists():
        return []
    evs = [json.loads(l) for l in a.read_text(encoding="utf-8").splitlines() if l.strip()]
    if qid:
        evs = [e for e in evs if e.get("qid") == qid]
    return evs[::-1][:limite]
