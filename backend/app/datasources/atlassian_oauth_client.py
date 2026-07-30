"""Cliente HTTP de OAuth 2.0 (3LO) con Atlassian — solo infraestructura."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalAuthError

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
USERINFO_URL = "https://api.atlassian.com/me"
JIRA_SCOPES = "read:jira-work read:jira-user read:me offline_access"


class AtlassianOAuthClient:
    """Implementación concreta de AtlassianOAuthGateway."""

    def build_authorization_url(self, state: str) -> str:
        params = {
            "audience": "api.atlassian.com",
            "client_id": settings.JIRA_CLIENT_ID,
            "scope": JIRA_SCOPES,
            "redirect_uri": settings.JIRA_REDIRECT_URI,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        return f"{AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.JIRA_CLIENT_ID,
            "client_secret": settings.JIRA_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.JIRA_REDIRECT_URI,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(TOKEN_URL, json=payload)

        if response.status_code != 200:
            raise ExternalAuthError(
                f"Error al intercambiar code por token: {response.text}"
            )
        return response.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.JIRA_CLIENT_ID,
            "client_secret": settings.JIRA_CLIENT_SECRET,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(TOKEN_URL, json=payload)

        if response.status_code != 200:
            raise ExternalAuthError(f"Error al refrescar el token: {response.text}")
        return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(USERINFO_URL, headers=headers)

        if response.status_code != 200:
            raise ExternalAuthError(
                f"No se pudo obtener el perfil del usuario: {response.text}"
            )
        return response.json()
