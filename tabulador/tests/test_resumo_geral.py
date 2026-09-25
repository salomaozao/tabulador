"""Regressão: a aba Resultados (Visão geral) não pode quebrar quando uma pergunta aprovada ainda
tem alguma resposta sem código primário/secundário (vira NaN, não None, depois de DataFrame.to_dict())."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix="tabulador_test_resumo_geral_")
os.environ["TABULADOR_OUTPUT"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pandas as pd

import resumo_geral


class TestResumoGeralComRespostaNaoCodificada(unittest.TestCase):
    def test_nao_quebra_com_nan_na_coluna_primaria(self):
        # Mistura int (codificado) e None (não codificado) na coluna 'primaria': depois de
        # DataFrame -> to_dict(), pandas costuma promover a coluna pra float64 e o None vira NaN
        # (reproduzido com dados reais do SESI: ValueError ao converter para int).
        tabela = pd.DataFrame([
            {"rid": 1, "texto": "Bom atendimento", "n": 5, "primaria": 1, "secundaria": None},
            {"rid": 2, "texto": "Ainda sem revisão", "n": 2, "primaria": None, "secundaria": None},
        ])
        frame = {"categorias": [{"codigo": 1, "nome": "Elogio ao atendimento"}]}

        with patch.object(resumo_geral, "_perguntas_aprovadas", return_value=["Q_TESTE"]), \
             patch.object(resumo_geral.CF, "frame", return_value=frame), \
             patch.object(resumo_geral.CD, "tabela", return_value=tabela), \
             patch.object(resumo_geral.V, "por_id", return_value={"rotulo": "Pergunta de teste"}):
            dados = resumo_geral._temas_e_trechos()

        self.assertEqual(dados["temas"], [{"qid": "Q_TESTE", "pergunta": "Pergunta de teste", "nome": "Elogio ao atendimento", "mencoes": 5}])
        self.assertEqual(dados["trechos"], [{"qid": "Q_TESTE", "pergunta": "Pergunta de teste", "texto": "Bom atendimento"}])


if __name__ == "__main__":
    unittest.main()
