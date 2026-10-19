"""Fase 3 dos grupos: payload da página do grupo (cobertura, andamento, saúde) e rota."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["TABULADOR_OUTPUT"] = tempfile.mkdtemp(prefix="tabulador_grupos_f3_")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codeframe as CF  # noqa: E402
import grupos_frame  # noqa: E402
from tests.test_grupos_fase1 import Base  # noqa: E402


class TestPaginaDoGrupo(Base):
    def setUp(self):
        super().setUp()
        import app as APP
        self.APP = APP
        self.cli = APP.app.test_client()

    def test_payload_traz_cobertura_andamento_e_saude(self):
        f = self.quadro_do_grupo()
        f["cobertura"] = {"amostra": False, "limite": 1500, "perguntas": {"Q32": {"unicas": 3, "lidas": 3}, "Q33": {"unicas": 2, "lidas": 2}}}
        grupos_frame._gravar_grupo("motivo_troca", "frame.json", f)
        CF.aprovar("Q32")
        d = self.cli.get("/api/grupo/motivo_troca").get_json()
        self.assertEqual(d["cobertura"]["perguntas"]["Q33"], {"unicas": 2, "lidas": 2})
        self.assertEqual([(a["qid"], a["quadro_aprovado"]) for a in d["andamento"]], [("Q32", True), ("Q33", False)])
        self.assertFalse(d["fechado"])
        self.assertEqual(d["saude"], [])  # sem classificação ainda: nada a diagnosticar
        self.assertEqual([p["qid"] for p in d["perguntas"]], ["Q32", "Q33"])

    def test_grupo_inexistente_da_erro_claro(self):
        r = self.cli.get("/api/grupo/nao_existe")
        self.assertEqual(r.status_code, 400)
        self.assertIn("desconhecido", r.get_json()["erro"])


if __name__ == "__main__":
    unittest.main()
