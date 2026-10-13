"""Correlaciona o Timeline de COMUNICACAO_IAS.md com o estado real do git.

Uso:
    python tabulador/.claude/scripts/coordenacao_ias.py

O que faz:
- Lê o `## Timeline` de COMUNICACAO_IAS.md (na raiz do repo) e casa cada `INÍCIO` com o próximo
  `FIM` do mesmo agente (heurística FIFO por nome de agente — não é um parser rigoroso, é um apoio
  de auditoria).
- Roda `git worktree list` + `git status --porcelain` em cada worktree para ver quem tem diff vivo
  de verdade agora.
- Aponta duas divergências comuns:
    1. worktree com diff vivo que não tem nenhum INÍCIO em aberto declarado (alguém esqueceu de
       anunciar no Timeline);
    2. INÍCIO em aberto cuja worktree/árvore já não tem diff nenhum (provavelmente falta um FIM).

Não escreve nada — só imprime o relatório. Editar COMUNICACAO_IAS.md continua manual, de propósito
(evita duas ferramentas tentando escrever no mesmo arquivo ao mesmo tempo).
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ENTRY_RE = re.compile(
    r"^### (?P<data>\d{4}-\d{2}-\d{2})(?: (?P<hora>\d{2}:\d{2}))? — (?P<agente>.+?) — (?P<tipo>INÍCIO|FIM)\s*$"
)
BACKTICK_RE = re.compile(r"`([^`]+)`")


@dataclass
class Entrada:
    data: str
    hora: str | None
    agente: str
    tipo: str
    linhas: list[str] = field(default_factory=list)

    @property
    def quando(self) -> str:
        return f"{self.data} {self.hora}" if self.hora else self.data

    def arquivos(self) -> list[str]:
        arquivos: list[str] = []
        for linha in self.linhas:
            if "mexer em" in linha.lower() or "tocados de fato" in linha.lower():
                arquivos.extend(BACKTICK_RE.findall(linha))
        return arquivos


def git(args: list[str], cwd: Path) -> str:
    resultado = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return resultado.stdout.strip()


def achar_raiz_repo() -> Path:
    aqui = Path(__file__).resolve().parent
    topo = git(["rev-parse", "--show-toplevel"], cwd=aqui)
    if not topo:
        sys.exit("Não consegui achar a raiz do repositório git a partir deste script.")
    return Path(topo)


def parsear_timeline(caminho: Path) -> list[Entrada]:
    if not caminho.exists():
        sys.exit(f"Não achei {caminho}")
    entradas: list[Entrada] = []
    atual: Entrada | None = None
    dentro_timeline = False
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.startswith("## Timeline"):
            dentro_timeline = True
            continue
        if dentro_timeline and linha.startswith("## "):
            break  # próxima seção (ex.: "## Pendências...") encerra o Timeline
        if not dentro_timeline:
            continue
        m = ENTRY_RE.match(linha.strip())
        if m:
            atual = Entrada(
                data=m["data"], hora=m["hora"], agente=m["agente"], tipo=m["tipo"]
            )
            entradas.append(atual)
        elif atual is not None and linha.strip().startswith("- "):
            atual.linhas.append(linha.strip())
    return entradas


def casar_inicio_fim(entradas: list[Entrada]) -> list[Entrada]:
    """Retorna os INÍCIOs sem FIM correspondente (heurística FIFO por agente)."""
    abertos: dict[str, list[Entrada]] = {}
    # Timeline tem as mais novas no topo; processa em ordem cronológica (mais antiga primeiro).
    for entrada in reversed(entradas):
        if entrada.tipo == "INÍCIO":
            abertos.setdefault(entrada.agente, []).append(entrada)
        else:  # FIM
            fila = abertos.get(entrada.agente)
            if fila:
                fila.pop(0)
    return [e for fila in abertos.values() for e in fila]


def listar_worktrees(raiz: Path) -> list[tuple[Path, str]]:
    saida = git(["worktree", "list", "--porcelain"], cwd=raiz)
    worktrees: list[tuple[Path, str]] = []
    caminho_atual: Path | None = None
    branch_atual = "(detached)"
    for linha in saida.splitlines():
        if linha.startswith("worktree "):
            if caminho_atual is not None:
                worktrees.append((caminho_atual, branch_atual))
            caminho_atual = Path(linha.split(" ", 1)[1])
            branch_atual = "(detached)"
        elif linha.startswith("branch "):
            branch_atual = linha.split(" ", 1)[1].replace("refs/heads/", "")
    if caminho_atual is not None:
        worktrees.append((caminho_atual, branch_atual))
    return worktrees


def arquivos_modificados(worktree: Path) -> list[str]:
    saida = git(["status", "--porcelain"], cwd=worktree)
    return [linha[3:].strip() for linha in saida.splitlines() if linha.strip()]


def esta_ignorado(raiz: Path, arquivo: str) -> bool:
    resultado = subprocess.run(
        ["git", "check-ignore", "--quiet", arquivo], cwd=raiz, check=False
    )
    return resultado.returncode == 0


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    raiz = achar_raiz_repo()
    comunicacao = raiz / "COMUNICACAO_IAS.md"
    entradas = parsear_timeline(comunicacao)
    abertos = casar_inicio_fim(entradas)

    print(f"Repositório: {raiz}")
    print(f"Arquivo lido: {comunicacao}\n")

    print("== INÍCIOs em aberto no Timeline ==")
    if not abertos:
        print("(nenhum)")
    for e in abertos:
        arqs = ", ".join(e.arquivos()) or "(não especificado)"
        print(f"- {e.quando} — {e.agente} — arquivos: {arqs}")

    print("\n== Worktrees reais com diff vivo agora ==")
    worktrees = listar_worktrees(raiz)
    algum_diff = False
    arquivos_anunciados = {a for e in abertos for a in e.arquivos()}
    for caminho, branch in worktrees:
        mods = arquivos_modificados(caminho)
        if not mods:
            continue
        algum_diff = True
        print(f"- {caminho} [{branch}] — {len(mods)} arquivo(s) modificado(s)")
        sobrepostos = [
            m for m in mods if any(m.endswith(a) or a.endswith(m) for a in arquivos_anunciados)
        ]
        nao_anunciados = [m for m in mods if m not in sobrepostos]
        if nao_anunciados and not abertos:
            print(
                "  ⚠ diff vivo sem NENHUM `INÍCIO` aberto no Timeline — considere registrar um,"
                " ou checar se é a sua própria sessão atual."
            )
    if not algum_diff:
        print("(nenhuma worktree com diff pendente)")

    print("\n== Possíveis FIM esquecidos ==")
    algum_orfao = False
    for e in abertos:
        arqs = [a for a in e.arquivos() if not esta_ignorado(raiz, a)]
        if not arqs:
            continue  # nada verificável via git (arquivo fora do versionamento, ex.: .brain, .md solto)
        ainda_tem_diff = any(
            any(m.endswith(a) or a.endswith(m) for m in arquivos_modificados(caminho))
            for caminho, _ in worktrees
            for a in arqs
        )
        if not ainda_tem_diff:
            algum_orfao = True
            print(
                f"- {e.quando} — {e.agente} — nenhum dos arquivos anunciados tem diff em nenhuma"
                " worktree agora; pode já ter sido commitado/mesclado — vale registrar o FIM."
            )
    if not algum_orfao:
        print("(nenhum)")


if __name__ == "__main__":
    main()
