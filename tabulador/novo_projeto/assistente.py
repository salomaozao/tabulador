"""Funções do assistente "Novo projeto" da interface (app.py só repassa as chamadas)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import config
from . import perfil as PF
from . import registrar as REG
from .rascunho import PREENCHER

JUMPPI = config.BASE_DIR.parent  # pasta onde ficam os projetos, ao lado do app (ex.: SESI_cat)


def pasta_padrao(nome: str) -> Path:
    limpo = re.sub(r"[^\w\- ]", "", nome, flags=re.UNICODE).strip().replace(" ", "_") or "Projeto"
    return JUMPPI / f"{limpo}_cat"


def payload(pasta) -> dict:
    """Projeto + colunas do perfil (para a tabela do assistente)."""
    pasta = Path(pasta)
    projeto = json.loads((pasta / "projeto.json").read_text(encoding="utf-8"))
    perfil = json.loads((REG.pasta_perfil(pasta) / "perfil.json").read_text(encoding="utf-8"))
    for campo in ("CONTEXTO_PROJETO",):
        if projeto.get(campo) == PREENCHER:
            projeto[campo] = ""
    conf = projeto.get("CONFERENCIA", {})
    for k, v in list(conf.items()):
        if v == PREENCHER:
            conf[k] = ""
    return {"pasta": str(pasta), "projeto": projeto, "abas": perfil["abas"], "aba": perfil["aba"],
            "cor_maioria": perfil.get("cor_maioria"), "n_linhas": perfil["n_linhas"],
            "colunas": [c for c in perfil["colunas"] if c["n"] > 0 or re.match(r".+_CAT$", c["coluna"])]}


def iniciar(planilha: Path, nome: str, cliente: str | None, pasta: str | None, aba: str | None, substituir: bool) -> dict:
    pasta = Path(pasta) if pasta else pasta_padrao(nome)
    REG.criar_rascunho(pasta, planilha, nome, cliente, aba or None, forcar=substituir)
    return payload(pasta)


def sincronizar(projeto: dict) -> dict:
    """Mantém SAIDA_PLANILHA.colunas igual às abertas marcadas para categorizar."""
    saida = projeto.setdefault("SAIDA_PLANILHA", {})
    atuais = saida.get("colunas", {})
    saida["colunas"] = {p["id"]: atuais.get(p["id"], f"{p.get('coluna', p['id'])}_CAT")
                        for p in projeto.get("PERGUNTAS", []) if p.get("codificar")}
    return projeto


def salvar(pasta, projeto: dict) -> None:
    REG.salvar_json(Path(pasta) / "projeto.json", sincronizar(projeto))


def sugerir(pasta, projeto: dict, notas: str) -> dict:
    """IA (a configurada no app, inclusive CLI local) sugere contexto, rótulos curtos e instruções.
    A pessoa revisa tudo antes de aceitar; nada aqui mexe em tipos, opções ou filtros."""
    import llm

    bruto = PF.ler(Path(projeto["FONTE_XLSX"]) if Path(projeto["FONTE_XLSX"]).is_absolute() else Path(pasta) / projeto["FONTE_XLSX"],
                   projeto["PLANO"]["aba"])
    linhas = []
    for p in projeto["PERGUNTAS"]:
        if p["tipo"] == "meta":
            continue
        linha = f"- {p['id']} ({p['tipo']}): {p.get('rotulo', '')}"
        if p.get("niveis"):
            linha += f" | opções: {'; '.join(map(str, p['niveis'][:8]))}"
        if p.get("codificar"):
            col = p.get("coluna", p["id"])
            ex = [v[:150] for v in PF.texto(bruto[col]) if isinstance(v, str)][:12]
            linha += "\n  exemplos de respostas: " + " || ".join(ex)
        linhas.append(linha)
    abertas = [p["id"] for p in projeto["PERGUNTAS"] if p.get("codificar")]
    schema = {"type": "object", "additionalProperties": False, "required": ["contexto", "rotulos", "instrucoes"], "properties": {
        "contexto": {"type": "string"},
        "rotulos": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["id", "rotulo"],
                                               "properties": {"id": {"type": "string"}, "rotulo": {"type": "string"}}}},
        "instrucoes": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["id", "instrucoes"],
                                                  "properties": {"id": {"type": "string"}, "instrucoes": {"type": "string"}}}},
    }}
    system = ("Você ajuda a configurar um projeto de categorização de respostas abertas de uma pesquisa. Escreva em português "
              "do Brasil. NÃO invente fatos sobre o cliente ou a pesquisa: use só as anotações da pessoa e o que as perguntas mostram.")
    user = (f"Projeto: {projeto.get('NOME')} · Cliente: {projeto.get('CLIENTE')}\n"
            f"Anotações da pessoa: {notas or '(nenhuma)'}\n\nPerguntas:\n" + "\n".join(linhas) +
            "\n\nDevolva:\n1. contexto: um parágrafo para orientar a IA que vai categorizar (quem respondeu, temas, como são as respostas).\n"
            "2. rotulos: rótulo curto (até 60 caracteres) para cada pergunta listada, sem mudar o sentido.\n"
            f"3. instrucoes: para cada aberta a categorizar ({', '.join(abertas)}), 1 ou 2 frases dizendo que TIPO de categoria "
            "criar (ex.: 'Categorias de PONTOS A MELHORAR, temáticas, com nomes curtos e neutros').")
    return llm.chamar_json(system, user, schema, nome="novo_projeto_sugestao")


def criar(pasta, slug: str | None = None) -> str:
    import load
    import projetos

    slug = REG.registrar(pasta, slug or None, ativar=True)
    projetos.ativar(slug, lembrar=True)
    load.executar(verbose=False)
    return slug
