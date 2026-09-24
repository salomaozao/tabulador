"""Base nova (mais respondentes, frequências diferentes): o que já foi classificado e conferido
continua nas MESMAS respostas (rid estável pela chave do texto), sem chamar a IA de verdade.

Rodar:  python -m unittest tests.test_base_nova -v
Escreve numa pasta temporária (TABULADOR_OUTPUT), nunca em SESI_cat/output.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TMP = tempfile.mkdtemp(prefix="tabulador_basenova_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import codeframe as CF  # noqa: E402
import coding as CD  # noqa: E402
import config  # noqa: E402
import llm  # noqa: E402
import load  # noqa: E402
import projetos  # noqa: E402

from tests.test_sesi import _llm_fake  # noqa: E402

QID = "Q33"


def _base_nova(df: pd.DataFrame) -> pd.DataFrame:
    """Simula a próxima versão da planilha: tira 1 respondente, repete muitas vezes a resposta
    MENOS frequente (vira a mais frequente, embaralhando a ordem) e traz 1 resposta inédita."""
    com = df[df[QID].notna()]
    removido = com.iloc[0]["respondent_id"]
    rara = com[QID].value_counts().index[-1]
    molde = com.iloc[1]
    novos = []
    prox = int(df["respondent_id"].max()) + 1
    for k in range(12):
        novos.append({**molde.to_dict(), "respondent_id": prox + k, QID: rara})
    novos.append({**molde.to_dict(), "respondent_id": prox + 12, QID: "Resposta totalmente inédita sobre transporte"})
    out = pd.concat([df[df["respondent_id"] != removido], pd.DataFrame(novos)], ignore_index=True)
    return out.astype(df.dtypes.to_dict(), errors="ignore")


@unittest.skipUnless(projetos.pasta("sesi").joinpath("data", "base_processamento.xlsx").exists(), "planilha SESI não disponível")
class TestBaseNova(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env_antes = os.environ.get("TABULADOR_OUTPUT")
        os.environ["TABULADOR_OUTPUT"] = _TMP
        projetos.ativar("sesi")
        llm.set_cliente(_llm_fake)
        load.executar(verbose=False)

    @classmethod
    def tearDownClass(cls):
        llm.set_cliente(None)
        # devolve a pasta temporária dos outros módulos de teste (cada um usa a sua)
        if cls._env_antes is None:
            os.environ.pop("TABULADOR_OUTPUT", None)
        else:
            os.environ["TABULADOR_OUTPUT"] = cls._env_antes

    def setUp(self):
        os.environ["TABULADOR_OUTPUT"] = _TMP
        projetos.ativar("sesi")

    def test_classificacao_segue_o_texto(self):
        self.assertTrue(str(config.OUTPUT_DIR).startswith(_TMP))
        antes = CF.preparar(QID)
        CF.induzir(QID, forcar=True)
        CF.aprovar(QID)
        CD.codificar(QID)
        itens = CD.codificacao(QID)["itens"]
        # confirma 3 e corrige 1 à mão, e aprova a classificação
        CD.validar(QID, [i["rid"] for i in itens[:3]])
        corr = itens[3]
        CD.atualizar_item(QID, corr["rid"], primaria=2 if corr["primaria"] != 2 else 1)
        CD.aprovar(QID)
        texto_de = {r["rid"]: r["chave"] for r in antes["respostas"]}
        por_chave = {texto_de[i["rid"]]: dict(i) for i in CD.codificacao(QID)["itens"]}

        # base nova: recarregar pela mesma rotina do botão "Recarregar planilha"
        df_novo = _base_nova(load.carregar_base()[0])
        fake_exec = lambda **kw: (load.salvar_base(df_novo, load.carregar_base()[1]) or (df_novo, None))  # noqa: E731
        with mock.patch.object(load, "executar", side_effect=fake_exec):
            r = CD.recarregar_base()
        m = r["perguntas"][QID]
        self.assertEqual(m["respondentes_novos"], 13)
        self.assertEqual(m["respondentes_removidos"], 1)
        self.assertEqual(m["unicas_novas"], 1)          # só a inédita; a repetida herda
        self.assertEqual(m["sem_classificacao"], 1)
        self.assertTrue(m["reaberta"])                  # aprovada + resposta nova => volta p/ revisão

        depois = CF.respostas(QID)
        self.assertEqual(len({r["rid"] for r in depois["respostas"]}), len(depois["respostas"]))
        chave_de = {r["rid"]: r["chave"] for r in depois["respostas"]}
        cod = CD.codificacao(QID)
        self.assertEqual(cod["status"], "rascunho")
        for it in cod["itens"]:
            ant = por_chave[chave_de[it["rid"]]]    # mesma resposta de antes
            self.assertEqual(it["chave"], chave_de[it["rid"]])
            self.assertEqual((it["primaria"], it.get("validado"), it.get("origem")),
                             (ant["primaria"], ant.get("validado"), ant.get("origem")))
        # a resposta que ficou sem ninguém (se houver) foi guardada, não apagada
        self.assertEqual(len(cod.get("removidos", [])), m["unicas_removidas"])
        # a nova é a única pendente; classificar as restantes não mexe no resto
        CD.codificar(QID, somente_faltantes=True)
        self.assertEqual(CD.resumo_revisao(QID)["n_faltantes"], 0)
        CD.aprovar(QID)
        CD.aplicar_na_base(verbose=False)
        df, _ = load.carregar_base()
        self.assertEqual(int(df[f"{QID}_COD1"].notna().sum()), int(df[QID].notna().sum()))
        versoes = __import__("json").loads((config.BASE_OUT / "versoes.json").read_text(encoding="utf-8"))
        self.assertEqual(versoes[-1]["n_respondentes"], len(df_novo))


if __name__ == "__main__":
    unittest.main()
