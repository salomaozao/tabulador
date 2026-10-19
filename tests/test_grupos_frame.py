import os
import tempfile
import unittest
from unittest.mock import patch
import sys
from pathlib import Path

os.environ["TABULADOR_OUTPUT"] = tempfile.mkdtemp(prefix="tabulador_grupos_")  # nuvem desligada nos testes

# Garante import do src
_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import config
import variables as V
import grupos_frame


class MockProjetoComGrupos:
    PERGUNTAS = [
        {"id": "Q32", "tipo": "aberta", "codificar": True, "rotulo": "Provavelmente vai trocar"},
        {"id": "Q33", "tipo": "aberta", "codificar": True, "rotulo": "Certamente vai trocar"},
        {"id": "Q1", "tipo": "unica", "rotulo": "Vínculo"},
        {"id": "Q4", "tipo": "aberta", "codificar": True, "rotulo": "Melhorar"},
        {"id": "Q5", "tipo": "aberta", "codificar": True, "rotulo": "Destaca"},
        {"id": "Q35", "tipo": "aberta", "codificar": True, "rotulo": "Melhoria"},
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


class TestAdministracaoGrupos(unittest.TestCase):
    """Edição à mão dos grupos (aba Grupos): config em arquivo, avisos antes de gravar, dissolver."""

    def setUp(self):
        V.ativar(MockProjetoComGrupos())
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._p = [patch.object(config, "OUTPUT_DIR", Path(self._tmp.name)),
                   patch.object(grupos_frame, "_situacao", lambda q: self.situacao.get(q, {"n_cod": 0, "n_rev": 0, "frame_proprio": False})),
                   patch.object(grupos_frame, "_respondentes", lambda q: self.resp.get(q, set()))]
        for p in self._p:
            p.start()
            self.addCleanup(p.stop)
        self.situacao, self.resp = {}, {}

    def test_grupo_sem_quadro_nao_esconde_o_quadro_da_pergunta(self):
        import codeframe as CF
        with patch.object(config, "PERGUNTAS_OUT", Path(self._tmp.name) / "perguntas"):
            proprio = {"status": "aprovado", "categorias": [{"codigo": 1, "nome": "A", "definicao": "x"}], "historico": []}
            (CF.pasta("Q32") / "frame.json").write_text(__import__("json").dumps(proprio), encoding="utf-8")
            self.assertEqual(grupos_frame.grupo_de("Q32")[0], "motivo_troca")
            self.assertEqual(grupos_frame.grupo_efetivo("Q32"), (None, None))
            self.assertEqual(CF.frame("Q32")["status"], "aprovado")           # segue com o quadro dela
            CF.renomear("Q32", 1, "B")                                          # e dá para editar
            self.assertEqual(CF.frame("Q32")["categorias"][0]["nome"], "B")
            grupos_frame._gravar_grupo("motivo_troca", "frame.json", {"status": "rascunho", "categorias": [{"codigo": 7, "nome": "G", "definicao": "g"}]})
            self.assertEqual(CF.frame("Q32")["categorias"][0]["nome"], "G")     # quadro do grupo passa a valer
            CF.renomear("Q32", 7, "H")                                          # e a edição passa a valer para o grupo
            self.assertEqual(grupos_frame.frame("motivo_troca")["categorias"][0]["nome"], "H")

    def test_sem_arquivo_vale_o_projeto_py(self):
        self.assertEqual(list(grupos_frame.todos()), ["motivo_troca"])

    def test_salvar_novo_grupo_grava_arquivo_e_vira_o_que_vale(self):
        nome = grupos_frame.salvar(None, "Nota da escola", ["Q4", "Q5"], "instr")
        self.assertEqual(nome, "nota_da_escola")
        self.assertEqual(grupos_frame.grupo_de("Q4")[0], "nota_da_escola")
        self.assertEqual(grupos_frame.grupo_de("Q32")[0], "motivo_troca")  # os demais grupos foram preservados

    def test_erros_bloqueiam(self):
        self.assertTrue(grupos_frame.impacto(None, "", ["Q4", "Q5"])["erros"])            # sem nome
        self.assertTrue(grupos_frame.impacto(None, "x", ["Q4"])["erros"])                 # menos de 2
        self.assertTrue(grupos_frame.impacto(None, "x", ["Q4", "Q1"])["erros"])           # Q1 não é aberta a categorizar
        self.assertTrue(grupos_frame.impacto(None, "x", ["Q4", "Q32"])["erros"])          # Q32 já está em outro grupo
        with self.assertRaises(ValueError):
            grupos_frame.salvar(None, "x", ["Q4"])

    def test_entrar_com_trabalho_feito_avisa_e_sair_tambem(self):
        self.situacao["Q4"] = {"n_cod": 100, "n_rev": 40, "frame_proprio": True}
        r = grupos_frame.impacto(None, "Nota", ["Q4", "Q5"])
        self.assertTrue(any(a["nivel"] == "alto" and "Q4" in a["msg"] and "100" in a["msg"] for a in r["avisos"]))
        self.situacao["Q32"] = {"n_cod": 50, "n_rev": 10, "frame_proprio": False}
        r = grupos_frame.impacto("motivo_troca", "Motivo", ["Q33", "Q4"])
        msgs = " ".join(a["msg"] for a in r["avisos"])
        self.assertIn("Q32", msgs)
        self.assertIn("sem categorias", msgs)  # Q32 sai e não tem quadro próprio

    def test_mudar_membros_de_quadro_aprovado_volta_a_rascunho(self):
        grupos_frame._gravar_grupo("motivo_troca", "frame.json", {"status": "aprovado", "categorias": [], "historico": []})
        r = grupos_frame.impacto("motivo_troca", "Motivo", ["Q32", "Q33", "Q4"])
        self.assertTrue(any("APROVADO" in a["msg"] for a in r["avisos"]))
        grupos_frame.salvar("motivo_troca", "Motivo", ["Q32", "Q33", "Q4"])
        f = grupos_frame.frame("motivo_troca")
        self.assertEqual(f["status"], "rascunho")
        self.assertEqual(f["perguntas"], ["Q32", "Q33", "Q4"])
        self.assertEqual(f["historico"][-1]["acao"], "membros_alterados")

    def test_so_renomear_nao_mexe_no_status(self):
        grupos_frame._gravar_grupo("motivo_troca", "frame.json", {"status": "aprovado", "categorias": [], "historico": []})
        grupos_frame.salvar("motivo_troca", "Outro nome", ["Q32", "Q33"])
        self.assertEqual(grupos_frame.frame("motivo_troca")["status"], "aprovado")
        self.assertEqual(grupos_frame.rotulo("motivo_troca"), "Outro nome")

    def test_perguntas_respondidas_pelas_mesmas_pessoas_avisam(self):
        self.resp = {"Q4": {1, 2, 3, 4}, "Q35": {1, 2, 3, 9}}
        r = grupos_frame.impacto(None, "x", ["Q4", "Q35"])
        self.assertTrue(any("mesmas pessoas" in a["msg"] for a in r["avisos"]))
        self.resp = {"Q4": {1, 2}, "Q5": {3, 4}}
        self.assertFalse(any("mesmas pessoas" in a["msg"] for a in grupos_frame.impacto(None, "x", ["Q4", "Q5"])["avisos"]))

    def test_agrupar_avisa_que_editar_categorias_do_grupo_ainda_nao_existe(self):
        r = grupos_frame.impacto(None, "x", ["Q4", "Q5"])
        self.assertTrue(any(a["nivel"] == "alto" and "renomear" in a["msg"] for a in r["avisos"]))

    def test_sugerir_acha_pares_excludentes(self):
        self.resp = {"Q4": set(range(0, 100)), "Q5": set(range(100, 300)), "Q35": set(range(0, 300))}
        sug = grupos_frame.sugerir(minimo=30)
        self.assertEqual([s["perguntas"] for s in sug], [["Q4", "Q5"]])
        self.assertEqual(sug[0]["em_comum"], 0)

    def test_dissolver_guarda_a_pasta_e_libera_as_perguntas(self):
        grupos_frame._gravar_grupo("motivo_troca", "frame.json", {"status": "rascunho", "categorias": []})
        self.assertEqual(grupos_frame.dissolver("motivo_troca"), ["Q32", "Q33"])
        self.assertIsNone(grupos_frame.grupo_de("Q32")[0])
        self.assertFalse((grupos_frame.pasta_grupos() / "motivo_troca").exists())
        guardadas = list((grupos_frame.pasta_grupos() / "_dissolvidos").iterdir())
        self.assertEqual(len(guardadas), 1)
        self.assertTrue((guardadas[0] / "frame.json").exists())
        with self.assertRaises(KeyError):
            grupos_frame.dissolver("motivo_troca")


if __name__ == "__main__":
    unittest.main()
