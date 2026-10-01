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

FASES_ORDEM = ["IDLE", "PRD", "ARCH", "TASKS", "DEV", "QA", "MERGED"]
ROLES_MAP = {
    "IDLE": ("Product Manager", "Nenhum ciclo ativo. Abra um novo ciclo com 'sop novo <slug>'"),
    "PRD": ("Product Manager", "Elaborar requisitos, dores e critérios de aceite em 01_PRD.md"),
    "ARCH": ("Architect", "Definir módulos afetados, interfaces, tipos e contratos em 02_ARCH.md"),
    "TASKS": ("Project Manager", "Quebrar arquitetura em tarefas atômicas em 03_TASKS.json"),
    "DEV": ("Engineer", "Implementar código e testes unitários para as tarefas de 03_TASKS.json"),
    "QA": ("QA Auditor", "Executar suíte de testes e gerar laudo de conformidade em 04_QA_REPORT.md"),
    "MERGED": ("None", "Ciclo concluído, integrado e pronto para produção")
}

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
            "historico_transicoes": []
        }
        STATE_FILE.write_text(json.dumps(estado_padrao, indent=2, ensure_ascii=False), encoding="utf-8")
        return estado_padrao
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
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

    # 4. Checagem de Diálogo
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

    conteudo = f"""# Linha de Montagem de Software (MetaGPT / SOPs)

Este documento centraliza todos os ciclos de engenharia do projeto **{PROJECT_NAME}**, operados através de artefatos estruturados e papéis tipados.

---

## 🚦 Estado da Linha de Montagem em Tempo Real
- **Ciclo Ativo:** `{ciclo_ativo}`
- **Fase Vigente:** `{fase_atual}`
- **Role da Vez:** `{role_ativa}`
- **Próxima Ação:** {estado.get("instrucao_proximo_agente", "Consulte state.json")}

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

# Iniciar novo ciclo a partir do template
python .brain/scripts/manage_brain.py sop novo <slug-da-feature> --titulo "Nome da Demanda" --obj OBJ-01

# Avançar para a próxima fase (PRD -> ARCH -> TASKS -> DEV -> QA -> MERGED)
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
    print("=" * 65 + "\n")

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
        else:
            print(f"Subcomando SOP '{sub}' desconhecido. Use: status, novo, avancar, recuar, task.")
    else:
        print(f"Comando '{comando}' desconhecido. Use: audit, sync, sop.")
