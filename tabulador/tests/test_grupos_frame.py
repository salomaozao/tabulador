import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Garante import do src
_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import variables as V
import grupos_frame


class MockProjetoComGrupos:
    PERGUNTAS = [
        {"id": "Q32", "tipo": "aberta", "codificar": True, "rotulo": "Provavelmente vai trocar"},
        {"id": "Q33", "tipo": "aberta", "codificar": True, "rotulo": "Certamente vai trocar"},
        {"id": "Q1", "tipo": "unica", "rotulo": "Vínculo"},
    ]
    GRUPOS = {
        "motivo_troca": {
            "rotulo": "Motivo para trocar de escola",
            "perguntas": ["Q32", "Q33"],
            "instrucoes_frame": "Instruções do grupo",
        }
    }


class TestGruposFrame(unittest.TestCase):
    def setUp(self):
        V.ativar(MockProjetoComGrupos())

    def test_lookup_grupo_de(self):
        nome, cfg = grupos_frame.grupo_de("Q32")
        self.assertEqual(nome, "motivo_troca")
        self.assertEqual(cfg["rotulo"], "Motivo para trocar de escola")

        nome33, _ = grupos_frame.grupo_de("Q33")
        self.assertEqual(nome33, "motivo_troca")

        nome_none, cfg_none = grupos_frame.grupo_de("Q1")
        self.assertIsNone(nome_none)
        self.assertIsNone(cfg_none)

    def test_membros_e_rotulo(self):
        mems = grupos_frame.membros("motivo_troca")
        self.assertEqual(mems, ["Q32", "Q33"])
        self.assertEqual(grupos_frame.rotulo("motivo_troca"), "Motivo para trocar de escola")

    def test_assimetrias_sem_dados(self):
        # sem frame gerado ainda, assimetrias retorna lista vazia sem explodir
        al = grupos_frame.assimetrias("motivo_troca")
        self.assertEqual(al, [])


if __name__ == "__main__":
    unittest.main()
