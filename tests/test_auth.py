import unittest
from unittest.mock import patch, MagicMock
import app
import auth

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_auth_desativada_por_padrao_local(self):
        """Sem MICROSOFT_CLIENT_ID e SECRET, o app roda livremente sem bloquear o pesquisador."""
        with patch.object(auth, 'auth_ativa', return_value=False):
            res = self.client.get("/")
            self.assertEqual(res.status_code, 200)

    def test_tela_login_renderiza(self):
        """Rota /login deve renderizar com sucesso."""
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Tabulador de Respostas", res.data)
        self.assertIn(b"Microsoft (Jumppi)", res.data)

    def test_bloqueio_quando_auth_ativa_sem_sessao(self):
        """Quando a auth está ativa e não há usuário na sessão, redireciona para /login."""
        with patch.object(auth, 'auth_ativa', return_value=True):
            with patch.object(auth, 'usuario_logado', return_value=None):
                res = self.client.get("/")
                self.assertEqual(res.status_code, 302)
                self.assertTrue(res.headers["Location"].endswith("/login"))

                # API deve retornar 401 JSON
                res_api = self.client.get("/api/status")
                self.assertEqual(res_api.status_code, 401)
                self.assertTrue(res_api.json.get("precisa_login"))

    def test_acesso_permitido_com_usuario_jumppi(self):
        """Quando a auth está ativa e o usuário está logado com conta Jumppi, o acesso é liberado."""
        usuario_fake = {"email": "gabriel@jumppi.com.br", "nome": "Gabriel Nascimento"}
        with patch.object(auth, 'auth_ativa', return_value=True):
            with patch.object(auth, 'usuario_logado', return_value=usuario_fake):
                res = self.client.get("/")
                self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
