"""Interface web do categorizador (Flask, sem build). Rode:  python app.py  (ou iniciar.bat) — o
navegador abre sozinho em http://127.0.0.1:5000

A página (templates/index.html + static/app.js) fala com a API JSON abaixo; toda a lógica continua
nos módulos do pipeline (load, codeframe, coding, report, codebook, crosstabs, exportar). Nada aqui
grava fora do output/ do projeto ativo (exceto a chave da OpenAI, em categorizador/.env).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

import backcoding
import codebook
import codeframe as CF
import coding as CD
import config
import crosstabs
import exportar
import llm
import llm_cli
import load
import projetos
import report
import usage
import variables as V

app = Flask(__name__, static_folder="static", template_folder="templates")
_lock = threading.Lock()  # uma operação de escrita por vez (arquivos JSON)


# ----------------------------------------------------------------------------- helpers
def _erro(e: Exception, status: int = 400):
    return jsonify({"erro": str(e), "tipo": type(e).__name__, "trace": traceback.format_exc()}), status


def _payload_pergunta(qid: str) -> dict:
    spec = V.por_id(qid)
    resp = CF._ler(qid, "respostas.json")
    frame = CF.frame(qid)
    cod = CD.codificacao(qid)
    itens = []
    contagens: dict = {}
    if frame:
        t = CD.tabela(qid) if resp else None
        if t is not None:
            for r in t.to_dict(orient="records"):
                r.pop("respondent_ids", None)
                for k, v in list(r.items()):
                    if isinstance(v, float) and v != v:  # NaN não é JSON válido
                        r[k] = None
                    elif hasattr(v, "item"):  # numpy -> python
                        r[k] = v.item()
                itens.append(r)
            for r in itens:
                if r["primaria"] is not None:
                    c = contagens.setdefault(int(r["primaria"]), {"primaria": 0, "secundaria": 0})
                    c["primaria"] += r["n"]
                if r["secundaria"] is not None:
                    c = contagens.setdefault(int(r["secundaria"]), {"primaria": 0, "secundaria": 0})
                    c["secundaria"] += r["n"]
    return {
        "qid": qid,
        "rotulo": spec.get("rotulo"),
        "backcoding": qid in V.BACKCODING,
        "instrucoes_fixas": spec.get("instrucoes_frame", ""),
        "instrucoes": CF.instrucoes(qid),
        "respostas": {k: v for k, v in (resp or {}).items() if k != "respostas"},
        "frame": frame,
        "pode_desfazer_refino": (CF.pasta(qid) / "frame_anterior.json").exists(),
        "codificacao": {k: v for k, v in (cod or {}).items() if k != "itens"} if cod else None,
        "itens": itens,
        "contagens": {str(k): v for k, v in contagens.items()},
        "n_alertas": sum(1 for r in itens if r.get("alertas") and r.get("alertas") != "não codificado"),
        "n_comentarios_pendentes": sum(1 for r in itens if r.get("comentario_pendente")),
        "revisao": CD.resumo_revisao(qid) if cod else None,
    }


def _status_base() -> dict:
    p = config.BASE_OUT / "base.json"
    info = {"fonte": str(config.FONTE_XLSX), "fonte_existe": config.FONTE_XLSX.exists(), "modelo": config.OPENAI_MODEL}
    if not p.exists():
        return {"carregada": False, **info}
    df, _ = load.carregar_base()
    return {
        "carregada": True,
        "n": int(len(df)),
        "por_fonte": df["fonte"].value_counts().to_dict(),
        "atualizada_em": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        **info,
    }


def _resultados() -> dict:
    """Arquivos de resultado do projeto ativo (para a seção 'Resultados' do painel)."""
    def _info(p: Path):
        return {"existe": p.exists(), "atualizado_em": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M") if p.exists() else None}
    saida = {
        "codebook": _info(config.CODEBOOK_OUT / "codebook.xlsx"),
        "cruzamentos": _info(config.CRUZAMENTOS_OUT / "cruzamentos.xlsx"),
        "base": _info(config.BASE_OUT / "base.xlsx"),
    }
    if exportar.disponivel():
        saida["planilha"] = _info(config.OUTPUT_DIR / V.SAIDA_PLANILHA.get("arquivo", "planilha_categorizada.xlsx"))
    return saida


def _arquivo_resultado(tipo: str) -> Path:
    caminhos = {
        "codebook": config.CODEBOOK_OUT / "codebook.xlsx",
        "cruzamentos": config.CRUZAMENTOS_OUT / "cruzamentos.xlsx",
        "base": config.BASE_OUT / "base.xlsx",
    }
    if exportar.disponivel():
        caminhos["planilha"] = config.OUTPUT_DIR / V.SAIDA_PLANILHA.get("arquivo", "planilha_categorizada.xlsx")
    if tipo not in caminhos:
        abort(404)
    return caminhos[tipo]


# ----------------------------------------------------------------------------- páginas
@app.get("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.get("/relatorio/<qid>")
def relatorio(qid):
    V.por_id(qid)
    p = report.gerar(qid)
    return send_file(p)


@app.get("/revisao/<qid>.xlsx")
def revisao_xlsx(qid):
    V.por_id(qid)
    p = CD.exportar_revisao(qid)
    return send_file(p, as_attachment=True, download_name=f"revisao_{qid}.xlsx")


# ----------------------------------------------------------------------------- API: geral
@app.get("/api/status")
def api_status():
    try:
        perguntas = [report.status_pergunta(q) for q in V.perguntas_codificaveis()]
        for s in perguntas:
            s["backcoding"] = s["qid"] in V.BACKCODING
        return jsonify({
            "projeto": {"slug": config.PROJETO, "nome": config.NOME_PROJETO, "pasta": str(config.PROJETO_PASTA), "saida": str(config.OUTPUT_DIR)},
            "projetos": projetos.listar(),
            "ia": _ia(),
            "base": _status_base(),
            "perguntas": perguntas,
            "resultados": _resultados(),
        })
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/projeto")
def api_projeto():
    try:
        slug = (request.get_json() or {}).get("slug")
        with _lock:
            projetos.ativar(slug, lembrar=True)
        return jsonify({"ok": True, "projeto": config.PROJETO})
    except Exception as e:
        return _erro(e)


def _ia() -> dict:
    """Estado da IA para a interface (nunca devolve a chave)."""
    return {
        "tem_chave": bool(config.OPENAI_API_KEY) or config.modo_teste() or config.usa_cli(), "modelo": config.OPENAI_MODEL,
        "provedor": config.OPENAI_PROVEDOR, "base_url": config.OPENAI_BASE_URL or "",
        "modo_teste": config.modo_teste(), "saida": str(config.OUTPUT_DIR), "saida_real": str(config.SAIDA_REAL),
        "provedores": {k: {**v, "tem_chave": config.chave_salva(k), "disponivel": not v.get("cli") or llm_cli.disponivel(k)}
                       for k, v in config.PROVEDORES.items()},
    }


@app.post("/api/config")
def api_config():
    """{provedor?, chave?, modelo?, base_url?} -> grava em categorizador/.env e aplica sem reiniciar.
    Entrar/sair do modo teste troca a pasta de resultados (<saída>_teste <-> <saída>)."""
    try:
        d = request.get_json() or {}
        with _lock:
            antes = config.modo_teste()
            config.salvar_llm(chave=d.get("chave") or None, modelo=d.get("modelo") or None,
                              base_url=d["base_url"] if "base_url" in d else None, provedor=d.get("provedor") or None)
            llm.resetar()
            if config.modo_teste() != antes:
                projetos.ativar(config.PROJETO)
        return jsonify({"ok": True, **_ia()})
    except Exception as e:
        return _erro(e)


@app.post("/api/modo-teste")
def api_modo_teste():
    """{ativo: true|false} liga/desliga o modo teste (IA simulada, resultados em <saída>_teste)."""
    try:
        ativo = bool((request.get_json() or {}).get("ativo"))
        with _lock:
            antes = config.modo_teste()
            config.alternar_modo_teste(ativo)
            llm.resetar()
            if config.modo_teste() != antes:
                projetos.ativar(config.PROJETO)
        return jsonify({"ok": True, **_ia()})
    except Exception as e:
        return _erro(e)


@app.post("/api/modo-teste/limpar")
def api_modo_teste_limpar():
    """Apaga os resultados do MODO TESTE do projeto ativo (só a pasta <saída>_teste; os reais não)."""
    try:
        if not config.modo_teste():
            raise RuntimeError("Só disponível no modo teste.")
        pasta = config.OUTPUT_DIR
        if not pasta.name.endswith("_teste") or pasta == config.SAIDA_REAL:
            raise RuntimeError(f"Pasta inesperada, nada foi apagado: {pasta}")
        with _lock:
            shutil.rmtree(pasta, ignore_errors=True)
            projetos.ativar(config.PROJETO)  # recria com a base copiada dos resultados reais
            config.garantir_pastas()
        return jsonify({"ok": True})
    except Exception as e:
        return _erro(e)


@app.post("/api/config/testar")
def api_config_testar():
    """Faz uma chamada mínima ao modelo configurado para conferir chave/URL/modelo.
    Sempre responde 200: {ok, provedor, modelo, segundos} e, se falhar, {erro, explicacao, solucao}."""
    import time
    t0 = time.time()
    base = {"provedor": config.OPENAI_PROVEDOR, "provedor_nome": config.PROVEDORES.get(config.OPENAI_PROVEDOR, {}).get("nome", config.OPENAI_PROVEDOR),
            "modelo": config.OPENAI_MODEL}
    try:
        r = llm.chamar_json("Responda em JSON.", 'Devolva {"ok": true}.',
                            {"type": "object", "additionalProperties": False, "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                            nome="teste_conexao")
        if r.get("ok") is not True:
            raise ValueError(f"resposta inesperada da IA: {json.dumps(r, ensure_ascii=False)[:200]}")
        return jsonify({**base, "ok": True, "segundos": round(time.time() - t0, 1)})
    except Exception as e:
        return jsonify({**base, "ok": False, "segundos": round(time.time() - t0, 1), "erro": str(e.__cause__ or e), **llm.diagnosticar(e)})


@app.get("/api/usage")
def api_usage():
    try:
        return jsonify(usage.consolidar(ultimas=int(request.args.get("ultimas", 50))))
    except Exception as e:
        return _erro(e, 500)


@app.get("/api/progresso")
def api_progresso():
    return jsonify(CD.PROGRESSO)


@app.post("/api/gerar/<tipo>")
def api_gerar(tipo):
    """Gera um resultado: codebook | cruzamentos | planilha (planilha final no formato da fonte)."""
    geradores = {"codebook": codebook.gerar, "cruzamentos": crosstabs.gerar, "planilha": exportar.gerar}
    if tipo not in geradores:
        abort(404)
    try:
        with _lock:
            geradores[tipo](verbose=False)
        return jsonify({"ok": True, "url": f"/arquivo/{tipo}", "resultados": _resultados()})
    except Exception as e:
        return _erro(e, 500)


@app.get("/arquivo/<tipo>")
def arquivo(tipo):
    p = _arquivo_resultado(tipo)
    if not p.exists():
        abort(404)
    return send_file(p, as_attachment=True, download_name=p.name)


@app.post("/api/abrir-pasta")
def api_abrir_pasta():
    """Abre a pasta de resultados no Explorer (o app roda na máquina do próprio usuário)."""
    try:
        config.garantir_pastas()
        if sys.platform.startswith("win"):
            os.startfile(config.OUTPUT_DIR)  # noqa: S606
        else:
            webbrowser.open(config.OUTPUT_DIR.as_uri())
        return jsonify({"ok": True})
    except Exception as e:
        return _erro(e)


@app.post("/api/load")
def api_load():
    try:
        with _lock:
            incluir_tel = bool((request.get_json(silent=True) or {}).get("telefone", True))
            df, _ = load.executar(incluir_telefone=incluir_tel, verbose=False)
            CD.aplicar_na_base(verbose=False)  # reaplica codificações aprovadas na base nova
        return jsonify({"ok": True, "n": int(len(df))})
    except Exception as e:
        return _erro(e, 500)


# ----------------------------------------------------------------------------- API: novo projeto
@app.post("/api/novo/iniciar")
def api_novo_iniciar():
    """Upload da planilha (multipart: planilha, nome, cliente, pasta, aba, substituir) -> rascunho sem IA."""
    import tempfile

    from werkzeug.utils import secure_filename

    from novo_projeto import assistente
    try:
        f = request.files.get("planilha")
        nome = (request.form.get("nome") or "").strip()
        if not nome:
            raise ValueError("Informe o nome do projeto.")
        if not f or not f.filename.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("Escolha a planilha (.xlsx).")
        tmp = Path(tempfile.mkdtemp(prefix="categorizador_upload_")) / (secure_filename(f.filename) or "planilha.xlsx")
        f.save(tmp)
        with _lock:
            dados = assistente.iniciar(tmp, nome, request.form.get("cliente") or None, request.form.get("pasta") or None,
                                       request.form.get("aba") or None, request.form.get("substituir") == "1")
        shutil.rmtree(tmp.parent, ignore_errors=True)
        return jsonify(dados)
    except FileExistsError as e:
        return jsonify({"erro": str(e), "existe": True}), 409
    except Exception as e:
        return _erro(e)


@app.post("/api/novo/aba")
def api_novo_aba():
    """Relê a planilha já copiada usando outra aba (refaz o rascunho)."""
    from novo_projeto import assistente
    try:
        d = request.get_json() or {}
        pasta = Path(d["pasta"])
        atual = json.loads((pasta / "projeto.json").read_text(encoding="utf-8"))
        with _lock:
            dados = assistente.iniciar(pasta / atual["FONTE_XLSX"], atual["NOME"], atual.get("CLIENTE"), str(pasta), d["aba"], True)
        return jsonify(dados)
    except Exception as e:
        return _erro(e)


@app.post("/api/novo/validar")
def api_novo_validar():
    """{pasta, projeto} -> grava o projeto.json e devolve a validação (roda a leitura real)."""
    from novo_projeto import assistente
    from novo_projeto.validar import validar
    try:
        d = request.get_json() or {}
        with _lock:
            assistente.salvar(d["pasta"], d["projeto"])
            res = validar(d["pasta"])
        return jsonify(res)
    except Exception as e:
        return _erro(e)


@app.post("/api/novo/sugerir")
def api_novo_sugerir():
    """{pasta, projeto, notas} -> sugestões da IA (contexto, rótulos, instruções) para a pessoa revisar."""
    from novo_projeto import assistente
    try:
        d = request.get_json() or {}
        return jsonify(assistente.sugerir(d["pasta"], d["projeto"], d.get("notas", "")))
    except Exception as e:
        return _erro(e)


@app.post("/api/novo/criar")
def api_novo_criar():
    """{pasta, projeto, slug?} -> valida, registra em projetos.json, ativa e lê a planilha."""
    from novo_projeto import assistente
    try:
        d = request.get_json() or {}
        with _lock:
            assistente.salvar(d["pasta"], d["projeto"])
            slug = assistente.criar(d["pasta"], d.get("slug"))
        return jsonify({"ok": True, "slug": slug})
    except Exception as e:
        return _erro(e)


# ----------------------------------------------------------------------------- API: pergunta
@app.get("/api/pergunta/<qid>")
def api_pergunta(qid):
    try:
        V.por_id(qid)
        return jsonify(_payload_pergunta(qid))
    except KeyError as e:
        return _erro(e, 404)
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/preparar")
def api_preparar(qid):
    try:
        with _lock:
            CF.preparar(qid)
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/instrucoes")
def api_instrucoes(qid):
    try:
        with _lock:
            CF.salvar_instrucoes(qid, (request.get_json() or {}).get("texto", ""))
        return jsonify({"ok": True})
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/frame/induzir")
def api_induzir(qid):
    try:
        d = request.get_json(silent=True) or {}
        with _lock:
            CF.preparar(qid)
            CF.induzir(qid, forcar=True, min_cat=int(d.get("min", 6)), max_cat=int(d.get("max", 15)))
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/frame/categoria")
def api_frame_categoria(qid):
    """{codigo, nome?, definicao?} edita; {nome, definicao} sem codigo adiciona."""
    try:
        d = request.get_json() or {}
        with _lock:
            if d.get("codigo") is None:
                CF.adicionar(qid, d["nome"], d.get("definicao", ""))
            else:
                CF.renomear(qid, d["codigo"], d.get("nome") or CF._cat(CF.frame(qid), d["codigo"])["nome"], d.get("definicao"))
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.delete("/api/pergunta/<qid>/frame/categoria/<codigo>")
def api_frame_remover(qid, codigo):
    try:
        with _lock:
            CF.remover(qid, codigo)
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/frame/fundir")
def api_frame_fundir(qid):
    try:
        d = request.get_json() or {}
        with _lock:
            CF.fundir(qid, d["destino"], *d["origens"])
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/frame/aprovar")
def api_frame_aprovar(qid):
    try:
        with _lock:
            CF.aprovar(qid)
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/frame/refinar")
def api_frame_refinar(qid):
    """{feedback} -> a IA revisa o frame conforme o pedido do pesquisador."""
    try:
        d = request.get_json() or {}
        with _lock:
            CF.refinar(qid, d.get("feedback", ""))
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/frame/desfazer")
def api_frame_desfazer(qid):
    try:
        with _lock:
            CF.desfazer_refino(qid)
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/codificar")
def api_codificar(qid):
    """{limite?: n} classifica só uma amostra; {restantes: true} classifica o que falta (mantém o resto)."""
    try:
        d = request.get_json(silent=True) or {}
        limite = int(d["limite"]) if d.get("limite") else None
        with _lock:
            cod = CD.codificar(qid, forcar=True, limite=limite, somente_faltantes=bool(d.get("restantes")))
        out = _payload_pergunta(qid)
        out["limite_atingido"] = cod.get("_limite_atingido")
        out["nao_tentados"] = cod.get("_nao_tentados")
        return jsonify(out)
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/validar")
def api_validar(qid):
    """{rids: [..], valor: true} confirma (ou desconfirma) várias respostas de uma vez."""
    try:
        d = request.get_json() or {}
        with _lock:
            n = CD.validar(qid, d.get("rids") or [], bool(d.get("valor", True)))
        out = _payload_pergunta(qid)
        out["alterados"] = n
        return jsonify(out)
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/recodificar")
def api_recodificar(qid):
    """{apenas_comentados: true} (padrão) ou {rids: [..]} ou {apenas_comentados: false} = tudo (mantém correções humanas)."""
    try:
        d = request.get_json(silent=True) or {}
        with _lock:
            if d.get("rids"):
                cod = CD.recodificar(qid, rids=[int(r) for r in d["rids"]])
            elif d.get("apenas_comentados", True):
                cod = CD.recodificar(qid, apenas_comentados=True)
            else:  # 'Reclassificar tudo': o que já foi classificado e ainda não foi conferido
                cod = CD.recodificar(qid, nao_revisados=True)
        out = _payload_pergunta(qid)
        out["recodificados"] = cod.get("_recodificados")
        out["limite_atingido"] = cod.get("_limite_atingido")
        out["nao_tentados"] = cod.get("_nao_tentados")
        return jsonify(out)
    except Exception as e:
        return _erro(e, 500)


@app.post("/api/pergunta/<qid>/item/<int:rid>")
def api_item(qid, rid):
    """{primaria?, secundaria?, comentario?, validado?} — campos ausentes são mantidos."""
    try:
        d = request.get_json() or {}
        with _lock:
            item = CD.atualizar_item(
                qid, rid,
                primaria=d.get("primaria"),
                secundaria=d["secundaria"] if "secundaria" in d else "__manter__",
                comentario=d["comentario"] if "comentario" in d else "__manter__",
                validado=d.get("validado"),
            )
        return jsonify({"ok": True, "item": item})
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/aprovar")
def api_aprovar(qid):
    try:
        with _lock:
            CD.aprovar(qid)
            if qid in V.BACKCODING:
                backcoding.aplicar([qid])
            else:
                CD.aplicar_na_base(verbose=False)
            report.gerar(qid)
            report.gerar_indice()
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


@app.post("/api/pergunta/<qid>/reabrir")
def api_reabrir(qid):
    """Volta uma codificação aprovada para rascunho (para continuar corrigindo)."""
    try:
        with _lock:
            cod = CD.codificacao(qid)
            if cod:
                cod["status"] = "rascunho"
                CF._gravar(qid, "codificacao.json", cod)
        return jsonify(_payload_pergunta(qid))
    except Exception as e:
        return _erro(e)


def _versao_codigo() -> str:
    """Impressão digital do código (tamanho + data dos arquivos): muda a cada atualização do programa."""
    import hashlib
    base = Path(__file__).resolve().parent
    arqs = sorted([*base.glob("*.py"), *base.glob("novo_projeto/*.py"), *base.glob("static/*"), *base.glob("templates/*")])
    h = hashlib.md5("".join(f"{p.name}{p.stat().st_size}{int(p.stat().st_mtime)}" for p in arqs).encode())
    return h.hexdigest()[:12]


VERSAO = _versao_codigo()


@app.get("/api/versao")
def api_versao():
    return jsonify({"versao": VERSAO, "pid": os.getpid()})


def _porta_ocupada(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def _versao_rodando(url: str) -> dict | None:
    import json as _json
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/api/versao", timeout=5) as r:
            return _json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - versão antiga (sem /api/versao) ou travada
        return None


def _pid_na_porta(porta: int) -> int | None:
    import subprocess
    try:
        saida = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=15).stdout
    except Exception:  # noqa: BLE001
        return None
    for linha in saida.splitlines():
        partes = linha.split()
        if len(partes) >= 5 and partes[1].endswith(f":{porta}") and partes[3].upper() in ("LISTENING", "ESCUTANDO"):
            return int(partes[4])
    return None


def _encerrar_antigo(porta: int, info: dict | None) -> bool:
    """Fecha um Categorizador DESATUALIZADO que ocupa a porta (só se for um python rodando app.py)."""
    import subprocess
    import time
    pid = (info or {}).get("pid") or _pid_na_porta(porta)
    if not pid or pid == os.getpid():
        return False
    try:
        cmd = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        cmd = ""
    if "app.py" not in cmd and not info:  # porta ocupada por outro programa: não mexe
        return False
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=20)
    for _ in range(20):
        if not _porta_ocupada(porta):
            return True
        time.sleep(0.5)
    return False


if __name__ == "__main__":
    porta = int(os.getenv("CATEGORIZADOR_PORTA", "5000"))
    url = f"http://127.0.0.1:{porta}"
    if _porta_ocupada(porta):
        info = _versao_rodando(url)
        if info and info.get("versao") == VERSAO:  # mesma versão já aberta (duplo clique de novo): só abre o navegador
            print(f"O Categorizador já está rodando em {url} — abrindo o navegador.")
            webbrowser.open(f"{url}/?projeto={projetos.padrao()}")
            sys.exit(0)
        print("Havia uma versão antiga do Categorizador aberta — fechando e abrindo a versão atual...")
        if not _encerrar_antigo(porta, info):
            print(f"\nA porta {porta} está ocupada por outro programa. Feche as outras janelas do Categorizador")
            print("(janelas pretas) e abra de novo. Se não resolver, reinicie o computador.")
            input("\nPressione Enter para fechar...")
            sys.exit(1)
    config.garantir_pastas()
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # sem log técnico na janela do usuário
    threading.Timer(1.2, lambda: webbrowser.open(f"{url}/?projeto={config.PROJETO}")).start()
    print(f"Categorizador ({config.NOME_PROJETO}) em {url}")
    print("Deixe esta janela aberta enquanto usa o programa. Para encerrar, feche-a.")
    app.run(host="127.0.0.1", port=porta, debug=False, threaded=True)
