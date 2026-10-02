#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Canônico de Governança, Memória e Linha de Montagem de Software (.brain)
Metodologia Híbrida: JTBD (Dores) + Shape Up (Anti-Escopo) + MetaGPT (SOPs & Artefatos Estruturados)

Uso Geral:
    python .brain/scripts/manage_brain.py audit
    python .brain/scripts/manage_brain.py sync

Operação da Linha de Montagem MetaGPT:
    python .brain/scripts/manage_brain.py sop status
    python .brain/scripts/manage_brain.py sop novo <slug> [--titulo "Titulo"] [--obj OBJ-XX]
    python .brain/scripts/manage_brain.py sop avancar [--nota "Justificativa"]
    python .brain/scripts/manage_brain.py sop recuar [--motivo "Motivo da rejeição"]
    python .brain/scripts/manage_brain.py sop task <TASK-ID> <TODO|IN_PROGRESS|DONE|BLOCKED>
"""

import sys
import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Garante saída UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BRAIN_DIR = Path(__file__).resolve().parent.parent
OBJETIVOS_DIR = BRAIN_DIR / "objetivos"
OBJETIVOS_FILE = BRAIN_DIR / "objetivos.md"
PENDENCIAS_DIR = BRAIN_DIR / "pendencias"
PENDENCIAS_FILE = BRAIN_DIR / "pendencias.md"
DIALOGO_FILE = BRAIN_DIR / "dialogo_ias.md"

# MetaGPT / SOPs
CICLOS_DIR = BRAIN_DIR / "ciclos"
CICLOS_TEMPLATE_DIR = CICLOS_DIR / "_template"
CICLOS_FILE = BRAIN_DIR / "ciclos.md"
STATE_FILE = BRAIN_DIR / "state.json"

# Suporte de transição legado
DECISOES_DIR = BRAIN_DIR / "decisoes"
DECISOES_FILE = BRAIN_DIR / "decisoes.md"

# Nome do projeto inferido pelo diretório pai ou fixo
PROJECT_NAME = BRAIN_DIR.parent.name.replace("_", " ").title()

FASES_ORDEM = ["IDLE", "PRD", "ARCH", "TASKS", "DEV", "QA", "INTEGRATION", "MERGED"]
ROLES_MAP = {
    "IDLE": ("Product Manager", "Nenhum ciclo ativo. Abra um novo ciclo com 'sop novo <slug>'"),
    "PRD": ("Product Manager", "Elaborar requisitos, dores e critérios de aceite em 01_PRD.md"),
    "ARCH": ("Architect", "Definir módulos afetados, interfaces, tipos e contratos em 02_ARCH.md"),
    "TASKS": ("Project Manager", "Quebrar arquitetura em tarefas atômicas em 03_TASKS.json"),
    "DEV": ("Engineer", "Implementar código e testes unitários para as tarefas de 03_TASKS.json"),
    "QA": ("QA Auditor", "Executar suíte de testes e gerar laudo de conformidade em 04_QA_REPORT.md"),
    "INTEGRATION": ("Integrator", "Verificar semáforo de worktrees, integrar branches para main e desmontar worktrees desocupadas"),
    "MERGED": ("None", "Ciclo concluído, integrado e pronto para produção")
}

def obter_raiz_git():
    """Retorna o diretório raiz do repositório Git."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=BRAIN_DIR,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip())
    except Exception:
        pass
    cur = BRAIN_DIR.resolve()
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return BRAIN_DIR.parent

def detectar_worktrees_git(raiz_git=None):
    """Varre as worktrees reais do git e verifica seus status de diff e merge."""
    raiz = raiz_git or obter_raiz_git()
    resultado = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=False
    )
    if resultado.returncode != 0:
        return []

    worktrees_raw = []
    caminho_atual = None
    branch_atual = "(detached)"
    head_atual = ""

    for linha in resultado.stdout.splitlines():
        if linha.startswith("worktree "):
            if caminho_atual is not None:
                worktrees_raw.append({
                    "caminho": caminho_atual,
                    "branch": branch_atual,
                    "head": head_atual
                })
            caminho_atual = Path(linha.split(" ", 1)[1])
            branch_atual = "(detached)"
            head_atual = ""
        elif linha.startswith("HEAD "):
            head_atual = linha.split(" ", 1)[1][:7]
        elif linha.startswith("branch "):
            branch_atual = linha.split(" ", 1)[1].replace("refs/heads/", "")

    if caminho_atual is not None:
        worktrees_raw.append({
            "caminho": caminho_atual,
            "branch": branch_atual,
            "head": head_atual
        })

    # Obter lista de branches já merged em main
    merged_branches = set()
    try:
        res_merged = subprocess.run(
            ["git", "branch", "--merged", "main"],
            cwd=raiz,
            capture_output=True,
            text=True,
            check=False
        )
        if res_merged.returncode == 0:
            for l in res_merged.stdout.splitlines():
                clean_b = l.strip().lstrip("*+ ").strip()
                if clean_b:
                    merged_branches.add(clean_b)
    except Exception:
        pass

    lista_final = []
    for wt in worktrees_raw:
        caminho_abs = wt["caminho"]
        try:
            caminho_rel = str(caminho_abs.relative_to(raiz)).replace("\\", "/")
        except Exception:
            caminho_rel = str(caminho_abs).replace("\\", "/")

        is_main = (caminho_abs.resolve() == raiz.resolve()) or (wt["branch"] == "main" and caminho_rel in [".", ""])
        
        # Obter diff pendente
        diff_arqs = []
        try:
            res_diff = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=caminho_abs,
                capture_output=True,
                text=True,
                check=False
            )
            if res_diff.returncode == 0:
                diff_arqs = [l[3:].strip() for l in res_diff.stdout.splitlines() if l.strip()]
        except Exception:
            pass

        nome_wt = caminho_abs.name if not is_main else "main"
        is_merged = (wt["branch"] in merged_branches) if wt["branch"] != "main" else True

        # Autor e mensagem do último commit
        ultimo_autor = ""
        ultimo_commit_msg = ""
        try:
            res_log = subprocess.run(
                ["git", "-C", str(caminho_abs), "log", "-1", "--format=%an|%s"],
                capture_output=True,
                text=True,
                check=False
            )
            if res_log.returncode == 0 and "|" in res_log.stdout:
                ultimo_autor, ultimo_commit_msg = res_log.stdout.strip().split("|", 1)
        except Exception:
            pass

        lista_final.append({
            "identificador": nome_wt,
            "caminho": caminho_rel,
            "caminho_abs": str(caminho_abs),
            "branch": wt["branch"],
            "head": wt["head"],
            "is_main": is_main,
            "diff_arquivos": diff_arqs,
            "diff_count": len(diff_arqs),
            "merged_in_main": is_merged,
            "ultimo_autor": ultimo_autor,
            "ultimo_commit_msg": ultimo_commit_msg
        })

    return lista_final

def sincronizar_worktrees(estado=None, salvar=True):
    """Cruza as worktrees físicas do Git com os metadados do state.json e atualiza o semáforo."""
    if estado is None:
        estado = carregar_estado()
    
    raiz = obter_raiz_git()
    wts_git = detectar_worktrees_git(raiz)
    wts_dict = estado.get("worktrees", {})

    wts_git_map = {wt["identificador"]: wt for wt in wts_git if not wt["is_main"]}
    
    # Atualizar ou adicionar worktrees detectadas
    for ident, info_git in wts_git_map.items():
        if ident not in wts_dict:
            # Nova worktree detectada - heurística de status
            if info_git["diff_count"] > 0:
                init_status = "EM_ANDAMENTO"
            elif info_git["merged_in_main"]:
                init_status = "DESOCUPADA"
            else:
                init_status = "PRONTO_PARA_MERGE"

            # Tenta inferir agente a partir do último commit
            autor = info_git.get("ultimo_autor", "")
            agente_inferido = "Antigravity" if "antigravity" in autor.lower() else (
                "Claude Code" if ("claude" in autor.lower() or "salomao" in autor.lower()) else (autor or "Não atribuído")
            )

            wts_dict[ident] = {
                "identificador": ident,
                "caminho": info_git["caminho"],
                "branch": info_git["branch"],
                "tarefa": None,
                "ciclo": None,
                "agente": agente_inferido,
                "status": init_status,
                "diff_arquivos": info_git["diff_arquivos"],
                "diff_count": info_git["diff_count"],
                "merged_in_main": info_git["merged_in_main"],
                "head": info_git["head"],
                "nota": info_git.get("ultimo_commit_msg", "Detectada automaticamente via Git"),
                "atualizado_em": datetime.now().isoformat()
            }
        else:
            # Atualizar dados dinâmicos do Git
            reg = wts_dict[ident]
            reg["caminho"] = info_git["caminho"]
            reg["branch"] = info_git["branch"]
            reg["head"] = info_git["head"]
            reg["diff_arquivos"] = info_git["diff_arquivos"]
            reg["diff_count"] = info_git["diff_count"]
            reg["merged_in_main"] = info_git["merged_in_main"]
            
            # Se a branch foi merged em main e está sem diff, marcar DESOCUPADA
            if info_git["merged_in_main"] and info_git["diff_count"] == 0 and reg.get("status") == "PRONTO_PARA_MERGE":
                reg["status"] = "DESOCUPADA"
                reg["nota"] = "Branch já integrada em main."
            # Se o status era PRONTO_PARA_MERGE mas surgiram diffs, alertar
            elif reg.get("status") in ["PRONTO_PARA_MERGE", "DESOCUPADA"] and info_git["diff_count"] > 0:
                reg["status"] = "EM_ANDAMENTO"
                reg["nota"] = f"Alterações detectadas ({info_git['diff_count']} arquivo(s))."
            
            reg["atualizado_em"] = datetime.now().isoformat()

    # Remover do registro worktrees que deixaram de existir no Git
    for ident in list(wts_dict.keys()):
        if ident not in wts_git_map:
            del wts_dict[ident]

    estado["worktrees"] = wts_dict

    # Avaliar o Gatekeeper de Merge
    ocupadas = []
    prontas = []
    desocupadas = []

    for ident, reg in wts_dict.items():
        st = reg.get("status", "EM_ANDAMENTO").upper()
        diff = reg.get("diff_count", 0)
        
        if st in ["EM_ANDAMENTO", "BLOQUEADA"] or diff > 0:
            ocupadas.append(ident)
        elif st in ["PRONTO_PARA_MERGE"]:
            if reg.get("merged_in_main"):
                desocupadas.append(ident)
            else:
                prontas.append(ident)
        elif st in ["DESOCUPADA", "MERGED"]:
            desocupadas.append(ident)
        else:
            ocupadas.append(ident)

    total_ativas = len(wts_dict)
    todas_desocupadas = (len(ocupadas) == 0)

    if total_ativas == 0:
        status_gatekeeper = "NEUTRO"
        proxima_acao = "Nenhuma worktree concorrente ativa. Árvore limpa para desenvolvimento."
    elif not todas_desocupadas:
        status_gatekeeper = "BLOQUEADO"
        proxima_acao = f"Merge BLOQUEADO. Existem {len(ocupadas)} worktree(s) ocupada(s) ({', '.join(ocupadas)}). Nenhuma IA deve iniciar o merge até que todas estejam prontas e desocupadas."
    elif len(prontas) > 0:
        status_gatekeeper = "LIBERADO"
        proxima_acao = f"🟢 TODAS AS WORKTREES DESOCUPADAS! A última IA deve assumir a Role: Integrator e iniciar o processo de merge sequencial das branches ({', '.join(prontas)}) para main."
    else:
        status_gatekeeper = "DESOCUPADAS"
        proxima_acao = "Todas as worktrees estão desocupadas/já integradas em main. Pronto para limpeza (git worktree remove)."

    estado["merge_gatekeeper"] = {
        "status": status_gatekeeper,
        "todas_desocupadas": todas_desocupadas,
        "total_worktrees": total_ativas,
        "ocupadas": ocupadas,
        "prontas_para_merge": prontas,
        "desocupadas": desocupadas,
        "ultima_verificacao": datetime.now().isoformat(),
        "instrucao_ia": proxima_acao
    }

    if salvar:
        salvar_estado(estado)

    return estado

def parse_frontmatter(file_path):
    """Extrai metadados do bloco YAML frontmatter e separa o corpo markdown."""
    if not file_path.exists():
        return {}, ""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}, ""
    
    if not content.strip():
        return {}, ""
    
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}, content
    
    fm_raw = match.group(1)
    body = content[match.end():]
    metadata = {}
    
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                metadata[key] = items
            else:
                metadata[key] = val.strip("'\"")
    return metadata, body

def extrair_secao(body, titulo_secao):
    """Extrai o texto sob uma seção específica markdown."""
    padrao = rf"###?\s*(?:\d+\.\s*)?{re.escape(titulo_secao)}.*?\n(.*?)(?=\n###?|\Z)"
    match = re.search(padrao, body, re.IGNORECASE | re.DOTALL)
    if match:
        linhas = [l.strip() for l in match.group(1).strip().splitlines() if l.strip() and not l.strip().startswith(">")]
        if linhas:
            texto = " ".join(linhas[:2])
            texto = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", texto)
            texto = texto.replace("*", "").replace("`", "").replace("- [ ]", "").replace("- [x]", "").replace("-", "").strip()
            if len(texto) > 130:
                return texto[:127] + "..."
            return texto
    return ""

def extrair_resumo_body(body):
    """Captura um parágrafo conciso inicial do corpo do texto."""
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---") and not line.startswith(">"):
            resumo = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", line)
            resumo = resumo.replace("*", "").replace("`", "").replace("-", "").strip()
            if len(resumo) > 130:
                return resumo[:127] + "..."
            return resumo
    return "Consulte o arquivo detalhado para mais informações."

def carregar_estado():
    """Lê o arquivo central state.json."""
    if not STATE_FILE.exists():
        estado_padrao = {
            "ciclo_ativo": None,
            "fase_atual": "IDLE",
            "role_ativa": "Product Manager",
            "tarefa_atual": None,
            "worktree": None,
            "instrucao_proximo_agente": "Nenhum ciclo ativo. Inicie com 'manage_brain.py sop novo <slug>'",
            "ultima_atualizacao": datetime.now().isoformat(),
            "historico_transicoes": [],
            "worktrees": {},
            "merge_gatekeeper": {}
        }
        STATE_FILE.write_text(json.dumps(estado_padrao, indent=2, ensure_ascii=False), encoding="utf-8")
        return estado_padrao
    try:
        estado = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if "worktrees" not in estado:
            estado["worktrees"] = {}
        if "merge_gatekeeper" not in estado:
            estado["merge_gatekeeper"] = {}
        return estado
    except Exception as e:
        print(f"[AVISO] Erro ao ler {STATE_FILE}: {e}. Recriando estado seguro.")
        return {}

def salvar_estado(estado):
    """Salva o estado central state.json formatado."""
    estado["ultima_atualizacao"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")

def audit():
    """Verifica a integridade entre sumários, pendências e ciclos MetaGPT."""
    print("=" * 60)
    print(f"AUDITORIA DO .BRAIN ({PROJECT_NAME})")
    print("=" * 60)
    
    errors = 0
    warnings = 0

    OBJETIVOS_DIR.mkdir(parents=True, exist_ok=True)
    PENDENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    CICLOS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Checagem de Objetivos
    obj_files = sorted(OBJETIVOS_DIR.glob("*.md"))
    obj_sumario_text = OBJETIVOS_FILE.read_text(encoding="utf-8") if OBJETIVOS_FILE.exists() else ""
    print(f"\n[OBJETIVOS] {len(obj_files)} objetivos encontrados.")
    for f in obj_files:
        meta, _ = parse_frontmatter(f)
        if not meta.get("id"):
            print(f"  [ERRO] {f.name}: Falta 'id' no frontmatter!")
            errors += 1
        rel_link = f"objetivos/{f.name}"
        if rel_link not in obj_sumario_text:
            print(f"  [AVISO] {f.name}: Nao referenciado em objetivos.md!")
            warnings += 1
        else:
            status = meta.get('status', 'ativo')
            print(f"  [OK] {f.name} -> {meta.get('id', 'N/A')} [{status.upper()}] ({meta.get('titulo', 'Sem titulo')})")

    # 2. Checagem de Pendências
    pend_files = sorted(PENDENCIAS_DIR.glob("*.md"))
    pend_sumario_text = PENDENCIAS_FILE.read_text(encoding="utf-8") if PENDENCIAS_FILE.exists() else ""
    print(f"\n[PENDENCIAS] {len(pend_files)} pendencias encontradas.")
    for f in pend_files:
        if f.stat().st_size == 0:
            print(f"  [AVISO] {f.name}: Arquivo vazio (0 bytes). Preencha ou remova.")
            warnings += 1
            continue
        meta, _ = parse_frontmatter(f)
        if not meta.get("id"):
            print(f"  [ERRO] {f.name}: Falta 'id' no frontmatter!")
            errors += 1
        rel_link = f"pendencias/{f.name}"
        if rel_link not in pend_sumario_text:
            print(f"  [AVISO] {f.name}: Nao referenciada em pendencias.md!")
            warnings += 1
        else:
            status = meta.get('status', 'aberto')
            obj_ref = meta.get('objetivo_relacionado') or meta.get('objetivo')
            obj_tag = f" -> {obj_ref}" if obj_ref else " (sem objetivo)"
            print(f"  [OK] {f.name} -> {meta.get('id', 'N/A')} [{status.upper()}]{obj_tag} ({meta.get('titulo', 'Sem titulo')})")

    # 3. Checagem MetaGPT (state.json e ciclos/)
    print("\n[METAGPT / CICLOS]")
    estado = carregar_estado()
    ciclo_ativo = estado.get("ciclo_ativo")
    fase_atual = estado.get("fase_atual", "IDLE")
    role_ativa = estado.get("role_ativa", "N/A")
    print(f"  Estado atual: Ciclo={ciclo_ativo or 'Nenhum'} | Fase={fase_atual} | Role={role_ativa}")

    ciclos_dirs = [d for d in sorted(CICLOS_DIR.iterdir()) if d.is_dir() and d.name != "_template"]
    print(f"  {len(ciclos_dirs)} ciclos encontrados em .brain/ciclos/.")
    for c_dir in ciclos_dirs:
        has_prd = (c_dir / "01_PRD.md").exists()
        has_arch = (c_dir / "02_ARCH.md").exists()
        has_tasks = (c_dir / "03_TASKS.json").exists()
        has_qa = (c_dir / "04_QA_REPORT.md").exists()
        artifacts = f"PRD:{'✓' if has_prd else '✗'} ARCH:{'✓' if has_arch else '✗'} TASKS:{'✓' if has_tasks else '✗'} QA:{'✓' if has_qa else '✗'}"
        print(f"  [CICLO] {c_dir.name} [{artifacts}]")

    if ciclo_ativo:
        ativo_dir = CICLOS_DIR / ciclo_ativo
        if not ativo_dir.exists():
            print(f"  [ERRO] Ciclo ativo '{ciclo_ativo}' em state.json nao existe em .brain/ciclos/!")
            errors += 1

    # 4. Checagem de Worktrees e Concorrência (Gatekeeper MetaGPT)
    print("\n[WORKTREES / CONCORRÊNCIA]")
    sincronizar_worktrees(estado, salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    wts = estado.get("worktrees", {})
    st_gk = gk.get("status", "NEUTRO")
    print(f"  Gatekeeper de Merge: [{st_gk}]")
    print(f"  Instrução: {gk.get('instrucao_ia')}")
    print(f"  Worktrees ativas no Git: {len(wts)}")
    for ident, reg in wts.items():
        st = reg.get("status", "EM_ANDAMENTO")
        diff = reg.get("diff_count", 0)
        if st == "PRONTO_PARA_MERGE" and diff > 0:
            print(f"  [AVISO] {ident}: Marcada como PRONTO_PARA_MERGE, mas possui {diff} arquivo(s) modificado(s)!")
            warnings += 1
        elif st == "EM_ANDAMENTO" and diff == 0 and reg.get("merged_in_main"):
            print(f"  [AVISO] {ident}: Marcada como EM_ANDAMENTO, mas já integrada em main sem diff pendente!")
            warnings += 1
        else:
            print(f"  [OK] {ident} -> [{st}] (diff={diff}, branch={reg.get('branch')})")

    # 5. Checagem de Diálogo
    if not DIALOGO_FILE.exists():
        print("\n  [ERRO] dialogo_ias.md nao encontrado!")
        errors += 1
    else:
        print(f"\n[DIALOGO] dialogo_ias.md presente ({DIALOGO_FILE.stat().st_size} bytes).")

    print("\n" + "=" * 60)
    print(f"Resultado: {errors} erros criticos, {warnings} avisos.")
    print("=" * 60)
    return errors == 0

def sync_ciclos():
    """Gera o arquivo ciclos.md com a visão executiva de todos os ciclos MetaGPT."""
    ciclos_dirs = [d for d in sorted(CICLOS_DIR.iterdir(), reverse=True) if d.is_dir() and d.name != "_template"]
    linhas = []

    for c_dir in ciclos_dirs:
        prd_file = c_dir / "01_PRD.md"
        arch_file = c_dir / "02_ARCH.md"
        tasks_file = c_dir / "03_TASKS.json"
        qa_file = c_dir / "04_QA_REPORT.md"

        prd_meta, prd_body = parse_frontmatter(prd_file) if prd_file.exists() else ({}, "")
        qa_meta, _ = parse_frontmatter(qa_file) if qa_file.exists() else ({}, "")

        titulo = prd_meta.get("titulo") or c_dir.name.replace("_", " ").title()
        status = prd_meta.get("status", "em_andamento").upper()
        obj = prd_meta.get("objetivo_relacionado", "-")
        veredito = qa_meta.get("veredito", "PENDENTE").upper()

        # Progresso de tarefas
        prog_str = "-"
        if tasks_file.exists():
            try:
                tdata = json.loads(tasks_file.read_text(encoding="utf-8"))
                tarefas = tdata.get("tarefas", [])
                if tarefas:
                    total = len(tarefas)
                    feitas = sum(1 for t in tarefas if t.get("status") in ["DONE", "CONCLUIDO"])
                    prog_str = f"{feitas}/{total}"
            except Exception:
                prog_str = "erro"

        rel = f"ciclos/{c_dir.name}"
        links = f"[PRD]({rel}/01_PRD.md) · [ARCH]({rel}/02_ARCH.md) · [TASKS]({rel}/03_TASKS.json) · [QA]({rel}/04_QA_REPORT.md)"
        linhas.append(f"| **[{c_dir.name}]({rel})** | {titulo} | `{obj}` | `{status}` | `{prog_str}` | `{veredito}` | {links} |")

    estado = carregar_estado()
    ciclo_ativo = estado.get("ciclo_ativo") or "Nenhum"
    fase_atual = estado.get("fase_atual", "IDLE")
    role_ativa = estado.get("role_ativa", "Product Manager")

    # Sincroniza worktrees e semáforo
    sincronizar_worktrees(estado, salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    wts = estado.get("worktrees", {})

    st_gk = gk.get("status", "NEUTRO")
    icon_gk = "🟢" if st_gk == "LIBERADO" else ("🔴" if st_gk == "BLOQUEADO" else "⚪")
    
    wt_linhas = []
    for ident, reg in sorted(wts.items()):
        st = reg.get("status", "EM_ANDAMENTO")
        diff = reg.get("diff_count", 0)
        diff_str = f"`{diff} arquivo(s)`" if diff > 0 else "Limpo (0)"
        branch_str = f"`{reg.get('branch', '-')}`"
        tarefa_str = f"`{reg.get('tarefa') or '-'}`"
        agente_str = reg.get("agente") or "Não atribuído"
        
        situacao = "Pronta para merge" if st == "PRONTO_PARA_MERGE" and diff == 0 else (
            "Desocupada / Merged" if st in ["DESOCUPADA", "MERGED"] else (
                "Em desenvolvimento ativo" if diff > 0 or st == "EM_ANDAMENTO" else "Bloqueada"
            )
        )
        wt_linhas.append(f"| `{ident}` | {branch_str} | {tarefa_str} | {agente_str} | `{st}` | {diff_str} | {situacao} |")

    wt_tabela = "\n".join(wt_linhas) if wt_linhas else "| *Nenhuma worktree concorrente ativa* | - | - | - | - | - | - |"

    conteudo = f"""# Linha de Montagem de Software (MetaGPT / SOPs)

Este documento centraliza todos os ciclos de engenharia do projeto **{PROJECT_NAME}**, operados através de artefatos estruturados e papéis tipados.

---

## 🚦 Estado da Linha de Montagem em Tempo Real
- **Ciclo Ativo:** `{ciclo_ativo}`
- **Fase Vigente:** `{fase_atual}`
- **Role da Vez:** `{role_ativa}`
- **Próxima Ação:** {estado.get("instrucao_proximo_agente", "Consulte state.json")}

---

## 🚦 Semáforo de Worktrees & Concorrência (MetaGPT Integrator)

> **Regra de Ouro da Janela de Merge:** Nenhuma IA deve iniciar o merge para `main` enquanto houver qualquer worktree com status `EM_ANDAMENTO` ou com alterações não comitadas (`diff > 0`). O processo de merge só é liberado para a **última IA** quando todas as worktrees estiverem desocupadas/prontas.

- **Status do Gatekeeper:** {icon_gk} **`{st_gk}`**
- **Diagnóstico da Vez:** {gk.get("instrucao_ia")}
- **Total de Worktrees:** `{len(wts)}` (Ocupadas: `{len(gk.get("ocupadas", []))}` · Prontas: `{len(gk.get("prontas_para_merge", []))}` · Desocupadas: `{len(gk.get("desocupadas", []))}`)

| Worktree | Branch | Tarefa | Agente | Status | Diff Pendente | Situação |
| :--- | :--- | :---: | :--- | :---: | :---: | :--- |
{wt_tabela}

---

## 📦 Inventário de Ciclos de Desenvolvimento

| Ciclo / Identificador | Título / Objetivo de Negócio | Objetivo | Status | Tarefas | Veredito QA | Artefatos |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
""" + ("\n".join(linhas) if linhas else "| *Nenhum ciclo cadastrado ainda* | - | - | - | - | - | - |") + f"""

---

## 🛠️ Comandos da Linha de Montagem (CLI)
```bash
# Ver status detalhado da esteira
python .brain/scripts/manage_brain.py sop status

# Ver semáforo de worktrees e concorrência
python .brain/scripts/manage_brain.py sop wt status

# Atualizar status da worktree (EM_ANDAMENTO, PRONTO_PARA_MERGE, DESOCUPADA)
python .brain/scripts/manage_brain.py sop wt set <worktree> PRONTO_PARA_MERGE --tarefa PEND-XX --agente "Nome"

# Verificar se a última IA pode iniciar o merge (exit 0 se sim, 1 se bloqueado)
python .brain/scripts/manage_brain.py sop can-merge

# Iniciar fase de integração (Role: Integrator)
python .brain/scripts/manage_brain.py sop merge-start

# Iniciar novo ciclo a partir do template
python .brain/scripts/manage_brain.py sop novo <slug-da-feature> --titulo "Nome da Demanda" --obj OBJ-01

# Avançar para a próxima fase (PRD -> ARCH -> TASKS -> DEV -> QA -> INTEGRATION -> MERGED)
python .brain/scripts/manage_brain.py sop avancar --nota "Artefato validado"

# Recuar em caso de rejeição em teste ou arquitetura
python .brain/scripts/manage_brain.py sop recuar --motivo "Falha nos testes de regressão"

# Atualizar status de uma tarefa no WBS
python .brain/scripts/manage_brain.py sop task TASK-01 DONE
```
"""
    CICLOS_FILE.write_text(conteudo, encoding="utf-8")
    print(f"  [OK] ciclos.md sincronizado ({len(linhas)} ciclos registrados).")

def sync():
    """Reescreve os sumários executivos garantindo sincronização estrita."""
    OBJETIVOS_DIR.mkdir(parents=True, exist_ok=True)
    PENDENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    CICLOS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Sincronizar Objetivos
    obj_files = sorted(OBJETIVOS_DIR.glob("*.md"))
    if obj_files or not DECISOES_DIR.exists():
        print("Sincronizando objetivos.md...")
        ativos_rows = []
        alcancados_rows = []

        for f in obj_files:
            meta, body = parse_frontmatter(f)
            obj_id = meta.get("id", f.stem)
            titulo = meta.get("titulo", f.stem.replace("_", " ").title())
            area = meta.get("area") or meta.get("modulo_afetado", "Geral")
            area_str = ", ".join(f"`{a}`" for a in area) if isinstance(area, list) else f"`{area}`"
            
            status = meta.get("status", "ativo").lower()
            prio = meta.get("prioridade", "media").capitalize()
            prio_fmt = f"**{prio}**" if prio.lower() == "alta" else prio
            
            vitoria = extrair_secao(body, "Critérios de Vitória") or extrair_secao(body, "Ganhos Esperados") or extrair_resumo_body(body)
            validacao = extrair_secao(body, "Validação dos Ganhos") or meta.get("impacto", "Ganhos validados conforme critérios.")
            rel_path = f"objetivos/{f.name}"

            if status in ["alcancado", "concluido", "fechado", "resolvido"]:
                data_fim = meta.get("data_conclusao") or meta.get("data_resolucao", "Concluído")
                alcancados_rows.append(f"| **[{obj_id}]({rel_path})** | **{titulo}** | {area_str} | {data_fim} | {validacao} | [Abrir]({rel_path}) |")
            else:
                ativos_rows.append(f"| **[{obj_id}]({rel_path})** | **{titulo}** | {area_str} | {prio_fmt} | {vitoria} | [Abrir]({rel_path}) |")

        obj_content = f"""# Bússola Estratégica: Objetivos e Dores do Projeto

Este arquivo é a bússola de valor do projeto **{PROJECT_NAME}**.
Ele define as dores reais a serem sanadas, os ganhos esperados, critérios de vitória e os limites rígidos de escopo (No-Gos / Rabbit Holes).

> **Atenção para as IAs:** Nenhuma tarefa ou código deve ser produzido sem estar a serviço de um dos objetivos ativos abaixo. Consulte sempre os Anti-Escopos e Rabbit Holes no arquivo detalhado antes de propor alterações.

---

## 🎯 Objetivos Ativos (Dores Prioritárias)

| ID | Objetivo / Dor | Área | Prioridade | Vitória Esperada / Ganhos | Detalhes |
| :--- | :--- | :---: | :---: | :--- | :---: |
""" + ("\n".join(ativos_rows) if ativos_rows else "| *Nenhum objetivo ativo no momento* | - | - | - | - | - |") + f"""

---

## 🏁 Objetivos Alcançados (Problemas Resolvidos)

| ID | Objetivo | Área | Conclusão | Ganhos Obtidos vs Esperados | Registro |
| :--- | :--- | :---: | :---: | :--- | :---: |
""" + ("\n".join(alcancados_rows) if alcancados_rows else "| *Nenhum objetivo arquivado ainda* | - | - | - | - | - |") + f"""

---

## Como Operar a Bússola
1. **Adicionar Objetivo:** Crie `.brain/objetivos/XX_nome.md` com YAML frontmatter e seções padronizadas.
2. **Encerrar Objetivo:** Altere `status: alcancado` e informe `data_conclusao: AAAA-MM-DD`.
3. Sincronize com:
   ```bash
   python .brain/scripts/manage_brain.py sync
   ```
"""
        OBJETIVOS_FILE.write_text(obj_content, encoding="utf-8")
        print(f"  [OK] objetivos.md sincronizado ({len(ativos_rows)} ativos, {len(alcancados_rows)} alcancados).")

    # 2. Sincronizar Pendências
    print("\nSincronizando pendencias.md...")
    pend_files = sorted(PENDENCIAS_DIR.glob("*.md"))
    abertas_rows = []
    resolvidas_rows = []

    for f in pend_files:
        if f.stat().st_size == 0:
            continue
        meta, body = parse_frontmatter(f)
        pend_id = meta.get("id", f.stem)
        titulo = meta.get("titulo", f.stem.replace("_", " ").title())
        resp = meta.get("responsavel", "A definir")
        crit = meta.get("criticidade", "media").capitalize()
        status = meta.get("status", "aberto").capitalize()
        resumo = meta.get("resumo") or extrair_resumo_body(body)
        rel_path = f"pendencias/{f.name}"
        
        obj_ref = meta.get("objetivo_relacionado") or meta.get("objetivo", "")
        obj_tag = f"`{obj_ref}`" if obj_ref else "-"

        if status.lower() in ["resolvido", "concluido", "fechado"]:
            resolvidas_rows.append(f"| *{pend_id}* | *{titulo}* | {obj_tag} | {resumo} | {meta.get('data_resolucao', 'N/A')} | [Abrir]({rel_path}) |")
        else:
            crit_fmt = f"**{crit}**" if crit.lower() == "alta" else crit
            abertas_rows.append(f"| **[{pend_id}]({rel_path})** | **{titulo}** | {obj_tag} | {resp} | {crit_fmt} | `{status}` | {resumo} | [Abrir]({rel_path}) |")

    pend_content = f"""# Sumário Executivo de Pendências e Backlog

Este arquivo é o inventário de pendências ativas, bloqueios e itens a monitorar no projeto **{PROJECT_NAME}**.
Cada pendência deve, idealmente, estar associada a um objetivo estratégico ativo em [`objetivos.md`](objetivos.md).

---

## 📋 Pendências Abertas / Em Andamento

| ID | Assunto / Pendência | Objetivo | Responsável | Criticidade | Status | Resumo e Ação | Detalhes |
| :--- | :--- | :---: | :--- | :---: | :---: | :--- | :---: |
""" + ("\n".join(abertas_rows) if abertas_rows else "| *Nenhuma pendência aberta* | - | - | - | - | - | - |") + f"""

---

## 🏁 Pendências Concluídas / Resolvidas

| ID | Assunto | Objetivo | Conclusão | Data Resolução | Registro |
| :--- | :--- | :---: | :--- | :---: | :---: |
""" + ("\n".join(resolvidas_rows) if resolvidas_rows else "| *Nenhum registro concluído ainda* | - | - | - | - |") + f"""

---

## Como Operar o Backlog
- Para **abrir uma nova pendência**: crie um arquivo `PEND-XX` em `pendencias/` e execute `python .brain/scripts/manage_brain.py sync`.
- Para **resolver uma pendência**: altere `status: resolvido` no frontmatter e execute `python .brain/scripts/manage_brain.py sync`.
"""
    PENDENCIAS_FILE.write_text(pend_content, encoding="utf-8")
    print(f"  [OK] pendencias.md sincronizado ({len(abertas_rows)} abertas, {len(resolvidas_rows)} resolvidas).")

    # 3. Sincronizar Ciclos MetaGPT
    print("\nSincronizando ciclos.md...")
    sync_ciclos()

def sop_status():
    """Exibe o estado da linha de montagem MetaGPT no terminal."""
    estado = carregar_estado()
    ciclo = estado.get("ciclo_ativo")
    fase = estado.get("fase_atual", "IDLE")
    role, descricao_role = ROLES_MAP.get(fase, ("Indefinido", ""))
    worktree = estado.get("worktree") or "main"
    instrucao = estado.get("instrucao_proximo_agente", "")

    print("\n" + "=" * 65)
    print(f"ESTEIRA METAGPT / SOP: {PROJECT_NAME.upper()}")
    print("=" * 65)
    print(f" Ciclo Ativo:  {ciclo or '[NENHUM - ESTEIRA EM ESPERA]'}")
    print(f" Fase Atual:   [{fase}]")
    print(f" Role Ativa:   {role} (Operador / Modelo)")
    print(f" Missão Role:  {descricao_role}")
    print(f" Worktree:     {worktree}")
    print("-" * 65)
    print(f" Próxima Ação:\n   -> {instrucao}")
    
    if ciclo:
        c_dir = CICLOS_DIR / ciclo
        tasks_file = c_dir / "03_TASKS.json"
        if tasks_file.exists():
            try:
                tdata = json.loads(tasks_file.read_text(encoding="utf-8"))
                tarefas = tdata.get("tarefas", [])
                print("-" * 65)
                print(" Tarefas WBS:")
                for t in tarefas:
                    st = t.get("status", "TODO")
                    tag = "✅" if st in ["DONE", "CONCLUIDO"] else ("🔄" if st == "IN_PROGRESS" else "⏳")
                    print(f"   {tag} [{st:^11}] {t.get('id')}: {t.get('titulo')} ({t.get('modulo_arquivo')})")
            except Exception as e:
                print(f"   [Erro ao ler tarefas: {e}]")

    # Concorrência & Worktrees (Gatekeeper)
    sincronizar_worktrees(estado, salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    wts = estado.get("worktrees", {})
    st_gk = gk.get("status", "NEUTRO")
    icon_gk = "🟢" if st_gk == "LIBERADO" else ("🔴" if st_gk == "BLOQUEADO" else "⚪")
    print("-" * 65)
    print(f" CONCORRÊNCIA & WORKTREES (Merge Gatekeeper): {icon_gk} [{st_gk}]")
    print(f" -> {gk.get('instrucao_ia')}")
    if wts:
        for ident, reg in sorted(wts.items()):
            st = reg.get("status", "EM_ANDAMENTO")
            diff = reg.get("diff_count", 0)
            tag_icon = "✅" if st in ["PRONTO_PARA_MERGE", "DESOCUPADA", "MERGED"] and diff == 0 else "⏳"
            resp = f"{reg.get('tarefa') or '-'} ({reg.get('agente') or 'IA'})"
            print(f"    {tag_icon} [{st:^16}] {ident:<26} (diff={diff:<2}) | {resp}")
    print("=" * 65 + "\n")

def sop_wt_status():
    """Exibe no terminal o painel executivo de concorrência de worktrees."""
    estado = sincronizar_worktrees(salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    wts = estado.get("worktrees", {})

    print("\n" + "=" * 70)
    print(f"SEMÁFORO DE WORKTREES & CONCORRÊNCIA (METAGPT) — {PROJECT_NAME.upper()}")
    print("=" * 70)
    
    st_gk = gk.get("status", "NEUTRO")
    icon_gk = "🟢" if st_gk == "LIBERADO" else ("🔴" if st_gk == "BLOQUEADO" else "⚪")
    print(f" Gatekeeper de Merge: {icon_gk} [{st_gk}]")
    print(f" Diagnóstico da Vez : {gk.get('instrucao_ia')}")
    print(f" Estatísticas       : Total={gk.get('total_worktrees', 0)} | Ocupadas={len(gk.get('ocupadas', []))} | Prontas={len(gk.get('prontas_para_merge', []))} | Desocupadas={len(gk.get('desocupadas', []))}")
    print("-" * 70)
    
    if not wts:
        print(" (Nenhuma worktree concorrente ativa no momento)")
    else:
        print(f" {'WORKTREE':<26} | {'STATUS':<17} | {'DIFF':<7} | {'TAREFA / AGENTE':<18}")
        print("-" * 70)
        for ident, reg in sorted(wts.items()):
            st = reg.get("status", "EM_ANDAMENTO")
            diff = reg.get("diff_count", 0)
            diff_str = f"{diff} arq(s)" if diff > 0 else "Limpo"
            tag_icon = "✅" if st in ["PRONTO_PARA_MERGE", "DESOCUPADA", "MERGED"] and diff == 0 else "⏳"
            if st == "BLOQUEADA":
                tag_icon = "🛑"
            elif diff > 0 and st in ["PRONTO_PARA_MERGE", "DESOCUPADA"]:
                tag_icon = "⚠️"
                st = "DIFF_PENDENTE"
            
            resp = f"{reg.get('tarefa') or '-'} ({reg.get('agente') or 'IA'})"
            print(f" {ident:<26} | {tag_icon} {st:<15} | {diff_str:<7} | {resp:<18}")
            if diff > 0:
                mod_preview = ", ".join(reg.get("diff_arquivos", [])[:3])
                if len(reg.get("diff_arquivos", [])) > 3:
                    mod_preview += f" (+{len(reg.get('diff_arquivos')) - 3})"
                print(f"   ↳ Modificados: {mod_preview}")
    print("=" * 70 + "\n")

def sop_wt_set(identificador, novo_status, tarefa=None, agente=None, nota=None):
    """Atualiza o status e os metadados de uma worktree específica."""
    estado = carregar_estado()
    sincronizar_worktrees(estado, salvar=False)
    wts = estado.get("worktrees", {})
    
    # Buscar por identificador ou por branch
    alvo = None
    for k, v in wts.items():
        if k.lower() == identificador.lower() or v.get("branch", "").lower() == identificador.lower() or identificador.lower() in k.lower():
            alvo = k
            break
            
    if not alvo:
        print(f"[ERRO] Worktree '{identificador}' não encontrada. Worktrees disponíveis: {', '.join(wts.keys())}")
        return False
        
    status_limpo = novo_status.upper()
    validos = ["EM_ANDAMENTO", "PRONTO_PARA_MERGE", "DESOCUPADA", "BLOQUEADA", "MERGED"]
    if status_limpo not in validos:
        print(f"[ERRO] Status inválido '{novo_status}'. Valores permitidos: {', '.join(validos)}")
        return False
        
    reg = wts[alvo]
    reg["status"] = status_limpo
    if tarefa:
        reg["tarefa"] = tarefa
    if agente:
        reg["agente"] = agente
    if nota:
        reg["nota"] = nota
    reg["atualizado_em"] = datetime.now().isoformat()
    
    # Re-sincroniza e salva
    sincronizar_worktrees(estado, salvar=True)
    sync()
    print(f"\n[SUCESSO] Worktree '{alvo}' atualizada para [{status_limpo}]!")
    sop_wt_status()
    return True

def sop_can_merge():
    """Checa se todas as worktrees estão desocupadas e se a última IA pode iniciar o merge."""
    estado = sincronizar_worktrees(salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    status = gk.get("status", "BLOQUEADO")
    
    print("\n" + "=" * 65)
    print("PORTAL DE MERGE / GATEKEEPER (METAGPT INTEGRATOR)")
    print("=" * 65)
    
    if status == "LIBERADO":
        print(" [STATUS]: 🟢 LIBERADO PARA MERGE")
        print(f" [AÇÃO]  : {gk.get('instrucao_ia')}")
        print(f" [PRONTAS]: {', '.join(gk.get('prontas_para_merge', []))}")
        print("=" * 65 + "\n")
        return True
    elif status == "BLOQUEADO":
        print(" [STATUS]: 🔴 MERGE BLOQUEADO")
        print(f" [MOTIVO]: {gk.get('instrucao_ia')}")
        print(f" [OCUPADAS]: {', '.join(gk.get('ocupadas', []))}")
        print("=" * 65 + "\n")
        return False
    else:
        print(f" [STATUS]: ⚪ {status}")
        print(f" [INFO]  : {gk.get('instrucao_ia')}")
        print("=" * 65 + "\n")
        return True

def sop_merge_start():
    """Inicia a fase de integração na esteira MetaGPT se o gatekeeper estiver liberado."""
    estado = carregar_estado()
    sincronizar_worktrees(estado, salvar=True)
    gk = estado.get("merge_gatekeeper", {})
    
    if not gk.get("todas_desocupadas", False):
        print("\n[BLOQUEIO DE INTEGRAÇÃO]")
        print(f"Não é possível iniciar o processo de merge. Existem worktrees ocupadas:\n -> {', '.join(gk.get('ocupadas', []))}")
        print("Aguarde todos os agentes concluírem e marcarem suas worktrees como PRONTO_PARA_MERGE ou DESOCUPADA.\n")
        return False
        
    print("\n[INICIANDO FASE DE INTEGRAÇÃO]")
    estado["fase_atual"] = "INTEGRATION"
    estado["role_ativa"] = "Integrator"
    estado["instrucao_proximo_agente"] = (
        "Role: Integrator. Todas as worktrees estão desocupadas. "
        "Proceda com o merge sequencial das branches prontas em main, execute a suíte de testes de regressão "
        "e remova as worktrees integradas com 'git worktree remove'."
    )
    estado["historico_transicoes"].append({
        "timestamp": datetime.now().isoformat(),
        "ciclo": estado.get("ciclo_ativo"),
        "de": estado.get("fase_atual"),
        "para": "INTEGRATION",
        "autor": "Integrator",
        "nota": "Gatekeeper liberado: todas as worktrees desocupadas para merge."
    })
    salvar_estado(estado)
    sync()
    sop_status()
    return True

def sop_novo(slug, titulo=None, obj_id=None):
    """Cria um novo ciclo a partir do template."""
    data_str = datetime.now().strftime("%Y-%m-%d")
    slug_limpo = re.sub(r"[^a-zA-Z0-9_\-]", "_", slug).lower()
    ciclo_nome = f"{data_str}_{slug_limpo}"
    ciclo_dir = CICLOS_DIR / ciclo_nome

    if ciclo_dir.exists():
        print(f"[ERRO] O ciclo '{ciclo_nome}' já existe em .brain/ciclos/!")
        return

    ciclo_dir.mkdir(parents=True, exist_ok=True)
    titulo_final = titulo or slug.replace("_", " ").title()
    obj_final = obj_id or "OBJ-01"

    # Copia arquivos do template substituindo variáveis
    for f in sorted(CICLOS_TEMPLATE_DIR.glob("*")):
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            content = content.replace("{SLUG}", ciclo_nome)
            content = content.replace("{TITULO}", titulo_final)
            content = content.replace("{DATA}", data_str)
            content = content.replace("{OBJ_ID}", obj_final)
            content = content.replace("{AUTOR}", "Product Manager")
            content = content.replace("{WORKTREE_OU_BRANCH}", f"feat/{slug_limpo}")
            content = content.replace("{COMMIT_HASH}", "pendente")
            dest = ciclo_dir / f.name
            dest.write_text(content, encoding="utf-8")
            print(f"  [CRIADO] {dest.relative_to(BRAIN_DIR)}")

    # Atualiza state.json
    estado = carregar_estado()
    estado["ciclo_ativo"] = ciclo_nome
    estado["fase_atual"] = "PRD"
    estado["role_ativa"] = "Product Manager"
    estado["tarefa_atual"] = None
    estado["worktree"] = f"feat/{slug_limpo}"
    estado["instrucao_proximo_agente"] = f"Role: Product Manager. Preencha e aprove o arquivo .brain/ciclos/{ciclo_nome}/01_PRD.md com requisitos e anti-escopos."
    estado["historico_transicoes"].append({
        "timestamp": datetime.now().isoformat(),
        "ciclo": ciclo_nome,
        "de": "IDLE",
        "para": "PRD",
        "autor": "Product Manager",
        "nota": f"Ciclo iniciado: {titulo_final}"
    })
    salvar_estado(estado)
    sync()
    print(f"\n[SUCESSO] Ciclo '{ciclo_nome}' iniciado na fase PRD!")
    sop_status()

def sop_avancar(nota=""):
    """Avança a fase atual da esteira para o próximo estágio."""
    estado = carregar_estado()
    ciclo = estado.get("ciclo_ativo")
    fase = estado.get("fase_atual", "IDLE")

    if not ciclo:
        print("[ERRO] Nenhum ciclo ativo para avançar. Crie um novo com 'sop novo <slug>'.")
        return

    c_dir = CICLOS_DIR / ciclo
    idx = FASES_ORDEM.index(fase) if fase in FASES_ORDEM else -1
    if idx == -1 or idx >= len(FASES_ORDEM) - 1:
        print(f"[ERRO] Fase atual '{fase}' não pode mais avançar.")
        return

    proxima_fase = FASES_ORDEM[idx + 1]

    # Validações estritas de artefatos antes de avançar
    if fase == "PRD":
        prd_file = c_dir / "01_PRD.md"
        if not prd_file.exists() or prd_file.stat().st_size < 200:
            print("[BLOQUEIO] O arquivo 01_PRD.md precisa estar preenchido antes de avançar para ARCH!")
            return
    elif fase == "ARCH":
        arch_file = c_dir / "02_ARCH.md"
        if not arch_file.exists() or arch_file.stat().st_size < 200:
            print("[BLOQUEIO] O arquivo 02_ARCH.md precisa estar preenchido antes de avançar para TASKS!")
            return
    elif fase == "TASKS":
        tasks_file = c_dir / "03_TASKS.json"
        if not tasks_file.exists():
            print("[BLOQUEIO] O arquivo 03_TASKS.json não foi encontrado!")
            return
    elif fase == "DEV":
        tasks_file = c_dir / "03_TASKS.json"
        if tasks_file.exists():
            try:
                tdata = json.loads(tasks_file.read_text(encoding="utf-8"))
                pendentes = [t.get("id") for t in tdata.get("tarefas", []) if t.get("status") not in ["DONE", "CONCLUIDO"]]
                if pendentes:
                    print(f"[BLOQUEIO] Ainda existem tarefas não concluídas no WBS: {', '.join(pendentes)}. Conclua-as antes de enviar para QA!")
                    return
            except Exception as e:
                print(f"[ERRO] Falha ao validar tarefas: {e}")
                return
    elif fase == "QA":
        qa_file = c_dir / "04_QA_REPORT.md"
        meta, _ = parse_frontmatter(qa_file)
        if meta.get("veredito", "").upper() != "APROVADO":
            print(f"[BLOQUEIO] O laudo 04_QA_REPORT.md não está com 'veredito: APROVADO' (atual: {meta.get('veredito')})!")
            return
    elif fase == "INTEGRATION":
        pode = sop_can_merge()
        if not pode:
            print("[BLOQUEIO] Nem todas as worktrees estão desocupadas! Finalize as worktrees ocupadas antes de concluir a integração para MERGED.")
            return

    # Efetua transição
    role_nova, missao_nova = ROLES_MAP.get(proxima_fase, ("Indefinido", ""))
    estado["fase_atual"] = proxima_fase
    estado["role_ativa"] = role_nova
    
    if proxima_fase == "MERGED":
        estado["ciclo_ativo"] = None
        estado["fase_atual"] = "IDLE"
        estado["role_ativa"] = "Product Manager"
        estado["instrucao_proximo_agente"] = f"Ciclo '{ciclo}' concluído e homologado. Pronto para novo ciclo."
    else:
        estado["instrucao_proximo_agente"] = f"Role: {role_nova}. {missao_nova} no ciclo '{ciclo}'."

    estado["historico_transicoes"].append({
        "timestamp": datetime.now().isoformat(),
        "ciclo": ciclo,
        "de": fase,
        "para": proxima_fase,
        "autor": role_nova,
        "nota": nota or f"Avanço de {fase} para {proxima_fase}"
    })
    salvar_estado(estado)
    sync()
    print(f"\n[SUCESSO] Esteira avançou de [{fase}] -> [{proxima_fase}]!")
    sop_status()

def sop_recuar(motivo=""):
    """Recua a fase atual da esteira em caso de rejeição."""
    estado = carregar_estado()
    ciclo = estado.get("ciclo_ativo")
    fase = estado.get("fase_atual", "IDLE")

    if not ciclo:
        print("[ERRO] Nenhum ciclo ativo para recuar.")
        return

    idx = FASES_ORDEM.index(fase) if fase in FASES_ORDEM else -1
    if idx <= 1:
        print(f"[ERRO] Fase atual '{fase}' não pode recuar mais.")
        return

    fase_anterior = FASES_ORDEM[idx - 1]
    role_anterior, missao_anterior = ROLES_MAP.get(fase_anterior, ("Indefinido", ""))
    
    estado["fase_atual"] = fase_anterior
    estado["role_ativa"] = role_anterior
    estado["instrucao_proximo_agente"] = f"REJEIÇÃO/AJUSTE: Role: {role_anterior}. Motivo: {motivo or 'Revisão necessária'}"
    
    estado["historico_transicoes"].append({
        "timestamp": datetime.now().isoformat(),
        "ciclo": ciclo,
        "de": fase,
        "para": fase_anterior,
        "autor": "Auditor",
        "nota": f"RECUO: {motivo or 'Não informado'}"
    })
    salvar_estado(estado)
    sync()
    print(f"\n[RECUO REGISTRADO] Esteira recuou de [{fase}] para [{fase_anterior}].")
    sop_status()

def sop_task(task_id, novo_status):
    """Atualiza o status de uma tarefa no 03_TASKS.json do ciclo ativo."""
    estado = carregar_estado()
    ciclo = estado.get("ciclo_ativo")
    if not ciclo:
        print("[ERRO] Nenhum ciclo ativo.")
        return

    tasks_file = CICLOS_DIR / ciclo / "03_TASKS.json"
    if not tasks_file.exists():
        print(f"[ERRO] {tasks_file} não existe.")
        return

    try:
        tdata = json.loads(tasks_file.read_text(encoding="utf-8"))
        encontrou = False
        status_valido = novo_status.upper()
        for t in tdata.get("tarefas", []):
            if t.get("id").upper() == task_id.upper():
                t["status"] = status_valido
                encontrou = True
                break
        if not encontrou:
            print(f"[ERRO] Tarefa '{task_id}' não encontrada em {tasks_file.name}.")
            return
        tasks_file.write_text(json.dumps(tdata, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Tarefa {task_id} atualizada para {status_valido}!")
        sync()
        sop_status()
    except Exception as e:
        print(f"[ERRO] Falha ao atualizar tarefa: {e}")

if __name__ == "__main__":
    args = sys.argv[1:]
    comando = args[0] if args else "audit"

    if comando == "audit":
        audit()
    elif comando == "sync":
        sync()
    elif comando == "sop":
        sub = args[1] if len(args) > 1 else "status"
        if sub == "status":
            sop_status()
        elif sub == "novo":
            if len(args) < 3:
                print("Uso: python manage_brain.py sop novo <slug> [--titulo 'Titulo'] [--obj OBJ-XX]")
                sys.exit(1)
            slug = args[2]
            titulo = None
            obj_id = None
            if "--titulo" in args:
                idx = args.index("--titulo")
                if idx + 1 < len(args):
                    titulo = args[idx + 1]
            if "--obj" in args:
                idx = args.index("--obj")
                if idx + 1 < len(args):
                    obj_id = args[idx + 1]
            sop_novo(slug, titulo, obj_id)
        elif sub == "avancar":
            nota = ""
            if "--nota" in args:
                idx = args.index("--nota")
                if idx + 1 < len(args):
                    nota = args[idx + 1]
            sop_avancar(nota)
        elif sub == "recuar":
            motivo = ""
            if "--motivo" in args:
                idx = args.index("--motivo")
                if idx + 1 < len(args):
                    motivo = args[idx + 1]
            sop_recuar(motivo)
        elif sub == "task":
            if len(args) < 4:
                print("Uso: python manage_brain.py sop task <TASK-ID> <TODO|IN_PROGRESS|DONE|BLOCKED>")
                sys.exit(1)
            sop_task(args[2], args[3])
        elif sub == "wt":
            # sop wt [status|set|sync]
            acao_wt = args[2] if len(args) > 2 else "status"
            if acao_wt in ["status", "listar", "list"]:
                sop_wt_status()
            elif acao_wt == "sync":
                sincronizar_worktrees(salvar=True)
                sync()
                sop_wt_status()
            elif acao_wt == "set":
                if len(args) < 4:
                    print("Uso: python manage_brain.py sop wt set <nome_ou_branch> <EM_ANDAMENTO|PRONTO_PARA_MERGE|DESOCUPADA> [--tarefa PEND-XX] [--agente 'Nome'] [--nota 'Texto']")
                    sys.exit(1)
                wt_target = args[3]
                wt_status_val = args[4] if len(args) > 4 else "EM_ANDAMENTO"
                tarefa_val = None
                agente_val = None
                nota_val = None
                if "--tarefa" in args:
                    idx = args.index("--tarefa")
                    if idx + 1 < len(args):
                        tarefa_val = args[idx + 1]
                if "--agente" in args:
                    idx = args.index("--agente")
                    if idx + 1 < len(args):
                        agente_val = args[idx + 1]
                if "--nota" in args:
                    idx = args.index("--nota")
                    if idx + 1 < len(args):
                        nota_val = args[idx + 1]
                sop_wt_set(wt_target, wt_status_val, tarefa=tarefa_val, agente=agente_val, nota=nota_val)
            else:
                sop_wt_set(acao_wt, args[3] if len(args) > 3 else "EM_ANDAMENTO")
        elif sub == "can-merge":
            pode = sop_can_merge()
            sys.exit(0 if pode else 1)
        elif sub == "merge-start":
            sop_merge_start()
        else:
            print(f"Subcomando SOP '{sub}' desconhecido. Use: status, novo, avancar, recuar, task, wt, can-merge, merge-start.")
    else:
        print(f"Comando '{comando}' desconhecido. Use: audit, sync, sop.")
