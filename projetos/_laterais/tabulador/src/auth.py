"""Autenticação corporativa Microsoft Entra ID (Azure AD) para o Tabulador.

Se as credenciais MICROSOFT_CLIENT_ID e MICROSOFT_CLIENT_SECRET estiverem configuradas,
o acesso a todas as rotas da interface e da API passa a exigir login corporativo @jumppi.
Se não estiverem configuradas (modo desenvolvimento local), o acesso permanece liberado.
"""
from __future__ import annotations

import os
import secrets
import urllib.parse
from typing import Any
import requests
from flask import session, request

TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
DOMINIO_PERMITIDO = os.getenv("AUTH_DOMINIO_PERMITIDO", "jumppi").lower()

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
AUTHORIZE_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_ME_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

SCOPES = ["User.Read", "openid", "profile", "email"]


def auth_ativa() -> bool:
    """Informa se a autenticação corporativa está configurada e ativa."""
    return bool(CLIENT_ID and CLIENT_SECRET and os.getenv("AUTH_DESATIVADA") != "1")


def get_redirect_uri() -> str:
    """Calcula a URL de redirecionamento dinamicamente a partir do host da requisição."""
    config_uri = os.getenv("MICROSOFT_REDIRECT_URI")
    if config_uri:
        return config_uri
    return urllib.parse.urljoin(request.host_url, "/auth/callback")


def gerar_url_login() -> str:
    """Gera a URL segura de autorização do Microsoft Entra ID."""
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": get_redirect_uri(),
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_ENDPOINT}?{urllib.parse.urlencode(params)}"


def processar_callback(code: str, state: str) -> dict[str, Any]:
    """Troca o authorization code pelo token e valida o usuário via Microsoft Graph."""
    saved_state = session.get("oauth_state")
    if not saved_state or saved_state != state:
        raise ValueError("Estado de segurança inválido (CSRF detectado). Tente fazer login novamente.")

    redirect_uri = get_redirect_uri()
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
    }

    resp = requests.post(TOKEN_ENDPOINT, data=token_data, timeout=15)
    if not resp.ok:
        raise ValueError(f"Falha ao obter token da Microsoft ({resp.status_code}): {resp.text}")

    token_json = resp.json()
    access_token = token_json.get("access_token")
    if not access_token:
        raise ValueError("Token de acesso não retornado pela Microsoft.")

    # Busca os dados do usuário no Microsoft Graph API
    me_resp = requests.get(
        GRAPH_ME_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if not me_resp.ok:
        raise ValueError(f"Falha ao consultar perfil Microsoft Graph: {me_resp.text}")

    user_info = me_resp.json()
    email = (user_info.get("mail") or user_info.get("userPrincipalName") or "").lower().strip()
    nome = user_info.get("displayName") or email.split("@")[0]

    # Validação estrita de domínio corporativo
    if DOMINIO_PERMITIDO and not any(DOMINIO_PERMITIDO in email.split("@")[-1:]):
        raise PermissionError(
            f"O e-mail '{email}' não tem autorização. O acesso é restrito a contas da equipe @{DOMINIO_PERMITIDO}."
        )

    usuario = {
        "email": email,
        "nome": nome,
        "id": user_info.get("id"),
        "autenticado_em": token_json.get("expires_in"),
    }
    session["usuario"] = usuario
    session.permanent = True
    return usuario


def usuario_logado() -> dict[str, Any] | None:
    """Retorna o usuário atualmente autenticado na sessão."""
    return session.get("usuario")


def logout() -> None:
    """Encerra a sessão corporativa."""
    session.pop("usuario", None)
    session.pop("oauth_state", None)
