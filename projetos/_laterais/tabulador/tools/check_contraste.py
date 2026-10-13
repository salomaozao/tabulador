#!/usr/bin/env python3
"""Gate de contraste (WCAG AA 4,5:1) dos tokens de static/app.css, nos temas claro e escuro.

Lê os dois primeiros blocos de tokens (:root e o @media dark). Sai com 0 se tudo passa, 2 se algum par falha.
Uso: python tools/check_contraste.py [static/app.css] [--json]
"""
import json
import re
import sys
from pathlib import Path

MINIMO = 4.5
TEXTOS = ["text", "text-2", "text-3", "accent-text", "ok", "warn", "danger", "human"]
FUNDOS = ["surface", "surface-2", "surface-3"]


def lum(h):
    h = h.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(css):
    claro = css.split("@media", 1)[0]
    m = re.search(r"@media \(prefers-color-scheme:dark\)\{:root:not\(\[data-theme=light\]\)\{(.*?)\}\}", css, re.S)
    escuro = m.group(1) if m else ""
    def par(s):
        out = {}
        for k, v in re.findall(r"--([\w-]+):(#[0-9a-fA-F]{3,6})", s):
            if len(v) == 4:
                v = "#" + "".join(ch * 2 for ch in v[1:])
            if len(v) == 7:
                out[k] = v
        return out
    c = par(claro)
    e = {**c, **par(escuro)}
    return {"claro": c, "escuro": e}


def main(argv):
    alvo = next((a for a in argv if not a.startswith("--")), "static/app.css")
    css = Path(alvo).read_text(encoding="utf-8")
    falhas, total = [], 0
    for tema, t in tokens(css).items():
        for nome in TEXTOS:
            cor = t.get(nome) or (t.get("accent") if nome == "accent-text" else None)
            if not cor:
                continue
            for f in FUNDOS:
                total += 1
                r = ratio(cor, t[f])
                if r < MINIMO:
                    falhas.append({"tema": tema, "texto": nome, "fundo": f, "razao": round(r, 2)})
        total += 1
        r = ratio("#ffffff", t["accent"])
        if r < MINIMO:
            falhas.append({"tema": tema, "texto": "#fff", "fundo": "accent", "razao": round(r, 2)})
    if "--json" in argv:
        print(json.dumps({"pares": total, "falhas": falhas}, ensure_ascii=False, indent=1))
    else:
        for x in falhas:
            print(f"[{x['tema']}] {x['texto']} sobre {x['fundo']}: {x['razao']}:1 (< {MINIMO})")
        print(f"pares={total} falhas={len(falhas)}")
    return 2 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
