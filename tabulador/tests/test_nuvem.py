"""Armazenamento em nuvem (nuvem.py) e o gatilho em codeframe._ler/_gravar/_existe.

Usa um banco SQLite local (file:) no lugar do Turso de verdade — mesmo cliente (libsql_client),
só muda a URL, então valida o caminho de código real sem precisar de credenciais.

Rodar:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codeframe as CF  # noqa: E402
import config  # noqa: E402
import nuvem  # noqa: E402


class TestNuvem(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="tabulador_nuvem_")
        self._db = str(Path(self._tmp) / "teste.db")
        self._url_antes = config.TURSO_URL, config.TURSO_TOKEN, config.PROJETO, config.PERGUNTAS_OUT
        config.TURSO_URL, config.TURSO_TOKEN, config.PROJETO = f"file:{self._db}", None, "projeto_teste"
        config.PERGUNTAS_OUT = Path(self._tmp) / "perguntas"  # isola de qualquer output real
        nuvem._cliente = None
        nuvem._tabela_pronta = False

    def tearDown(self):
        if nuvem._cliente is not None:
            nuvem._cliente.close()
        config.TURSO_URL, config.TURSO_TOKEN, config.PROJETO, config.PERGUNTAS_OUT = self._url_antes
        nuvem._cliente = None
        nuvem._tabela_pronta = False

    def test_ler_gravar_existe(self):
        self.assertIsNone(nuvem.ler("projeto_teste", "Q1", "codificacao.json"))
        self.assertFalse(nuvem.existe("projeto_teste", "Q1", "codificacao.json"))
        nuvem.gravar("projeto_teste", "Q1", "codificacao.json", {"a": 1, "b": [1, 2]})
        self.assertTrue(nuvem.existe("projeto_teste", "Q1", "codificacao.json"))
        self.assertEqual(nuvem.ler("projeto_teste", "Q1", "codificacao.json"), {"a": 1, "b": [1, 2]})

    def test_gravar_sobrescreve(self):
        nuvem.gravar("projeto_teste", "Q1", "frame.json", {"v": 1})
        nuvem.gravar("projeto_teste", "Q1", "frame.json", {"v": 2})
        self.assertEqual(nuvem.ler("projeto_teste", "Q1", "frame.json"), {"v": 2})

    def test_projetos_diferentes_nao_se_misturam(self):
        nuvem.gravar("sesi", "Q1", "codificacao.json", {"p": "sesi"})
        nuvem.gravar("assertiva", "Q1", "codificacao.json", {"p": "assertiva"})
        self.assertEqual(nuvem.ler("sesi", "Q1", "codificacao.json"), {"p": "sesi"})
        self.assertEqual(nuvem.ler("assertiva", "Q1", "codificacao.json"), {"p": "assertiva"})

    def test_codeframe_usa_nuvem_quando_ativa(self):
        self.assertTrue(nuvem.ativa())
        self.assertFalse(CF.classificacao_iniciada("Q1"))
        CF._gravar("Q1", "codificacao.json", {"status": "aprovado"})
        self.assertTrue(CF.classificacao_iniciada("Q1"))
        self.assertEqual(CF._ler("Q1", "codificacao.json"), {"status": "aprovado"})
        # não deve ter criado a pasta local de output para esta pergunta
        self.assertFalse((config.PERGUNTAS_OUT / "Q1" / "codificacao.json").exists())

    def test_codeframe_usa_arquivo_local_quando_inativa(self):
        config.TURSO_URL = None
        self.assertFalse(nuvem.ativa())
        qid = "Q_local_teste"
        try:
            self.assertFalse(CF.classificacao_iniciada(qid))
            CF._gravar(qid, "codificacao.json", {"status": "rascunho"})
            self.assertTrue(CF.classificacao_iniciada(qid))
            self.assertEqual(CF._ler(qid, "codificacao.json"), {"status": "rascunho"})
        finally:
            import shutil
            shutil.rmtree(CF.pasta(qid), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
