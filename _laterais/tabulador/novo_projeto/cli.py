"""Linha de comando para criar projetos (usada pela skill novo-projeto e por quem prefere o terminal).
Rodar na pasta do tabulador, com o Python do ambiente dele:

  python -m novo_projeto.cli perfil <planilha.xlsx> [--aba base]
  python -m novo_projeto.cli rascunho <planilha.xlsx> --pasta <pasta do projeto> --nome "Nome" [--cliente C] [--aba A] [--forcar]
  python -m novo_projeto.cli validar <pasta do projeto> [--sem-conferencia]
  python -m novo_projeto.cli registrar <pasta do projeto> [--slug nome] [--ativar]

Código de saída 1 quando há erro (validar/registrar), para agentes e scripts pararem ali.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # acentos e ✅ no console do Windows

from . import perfil as PF  # noqa: E402
from . import registrar as REG  # noqa: E402
from .validar import relatorio, validar  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="novo_projeto")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("perfil")
    a.add_argument("planilha")
    a.add_argument("--aba")
    a.add_argument("--json", action="store_true", help="imprime o perfil completo em JSON")
    a = sub.add_parser("rascunho")
    a.add_argument("planilha")
    a.add_argument("--pasta", required=True)
    a.add_argument("--nome", required=True)
    a.add_argument("--cliente")
    a.add_argument("--aba")
    a.add_argument("--forcar", action="store_true")
    a = sub.add_parser("validar")
    a.add_argument("pasta")
    a.add_argument("--sem-conferencia", action="store_true")
    a = sub.add_parser("registrar")
    a.add_argument("pasta")
    a.add_argument("--slug")
    a.add_argument("--ativar", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "perfil":
        p = PF.perfilar(args.planilha, args.aba)
        print(json.dumps(p, ensure_ascii=False, indent=1) if args.json else PF.resumo(p))
        return 0
    if args.cmd == "rascunho":
        perfil, projeto = REG.criar_rascunho(args.pasta, args.planilha, args.nome, args.cliente, args.aba, args.forcar)
        print(PF.resumo(perfil))
        print(f"\nRascunho gravado em {args.pasta}/projeto.json · perfil em {REG.pasta_perfil(args.pasta)}/perfil.json")
        print("\nConfira:")
        for n in projeto["_notas"]:
            print(f"  - {n}")
        return 0
    if args.cmd == "validar":
        res = validar(args.pasta, exigir_conferencia=not args.sem_conferencia)
        print(relatorio(res))
        return 0 if res["valido"] else 1
    if args.cmd == "registrar":
        try:
            slug = REG.registrar(args.pasta, args.slug, args.ativar)
        except ValueError as e:
            print(e)
            return 1
        print(f"✅ Projeto registrado como {slug!r}. Próximo passo: python run.py --projeto {slug} load")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
