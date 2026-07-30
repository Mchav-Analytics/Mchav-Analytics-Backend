"""Puerto de salida hacia Atlassian OAuth (3LO)."""

from __future__ import annotations

from typing import Protocol


class AtlassianOAuthGateway(Protocol):
    """Contrato del cliente OAuth Atlassian (sin lógica de negocio)."""

    def build_authorization_url(self, state: str) -> str: ...

    async def exchange_code(self, code: str) -> dict: ...

    async def refresh_token(self, refresh_token: str) -> dict: ...

    async def get_user_info(self, access_token: str) -> dict: ...
