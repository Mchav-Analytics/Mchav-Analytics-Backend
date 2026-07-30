"""Casos de uso de autenticación OAuth (orquestación, sin HTTP directo)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.datasources.atlassian_oauth_client import AtlassianOAuthClient
from app.db.unit_of_work import UnitOfWork
from app.models import User
from app.ports.oauth_gateway import AtlassianOAuthGateway
from app.repositories import OAuthTokenRepository, UserRepository
from app.services.jwt_service import JwtService


class OAuthAuthService:
    def __init__(
        self,
        db: Session | None = None,
        oauth_client: AtlassianOAuthGateway | None = None,
    ):
        self.uow = UnitOfWork(db) if db is not None else None
        self.users = UserRepository(db) if db is not None else None
        self.tokens = OAuthTokenRepository(db) if db is not None else None
        self.oauth = oauth_client or AtlassianOAuthClient()

    def build_authorization_url(self, state: str) -> str:
        return self.oauth.build_authorization_url(state)

    def get_or_validate_user(self, email: str) -> User:
        if self.users is None:
            raise RuntimeError("OAuthAuthService requiere sesión de base de datos")

        if not email:
            raise ForbiddenError("No se pudo obtener el email de Atlassian.")

        normalized = email.strip().lower()
        domain = settings.ALLOWED_EMAIL_DOMAIN.lower()
        if not normalized.endswith(f"@{domain}"):
            raise ForbiddenError(
                f"El correo no pertenece a la organización ({email}). "
                f"Dominio permitido: @{settings.ALLOWED_EMAIL_DOMAIN}"
            )

        user = self.users.get_by_email(normalized)
        if not user:
            raise ForbiddenError(
                f"Usuario no registrado ({email}). Contacte al administrador."
            )
        if user.status != "active":
            raise ForbiddenError(
                f"Usuario deshabilitado ({email}). Contacte al administrador."
            )
        return user

    def save_token(self, user: User, token_data: dict):
        if self.tokens is None:
            raise RuntimeError("OAuthAuthService requiere sesión de base de datos")

        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return self.tokens.upsert(
            user_id=user.id_user,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_at=expires_at,
        )

    async def complete_login(self, code: str) -> dict:
        if self.uow is None:
            raise RuntimeError("OAuthAuthService requiere sesión de base de datos")

        token_data = await self.oauth.exchange_code(code)
        profile = await self.oauth.get_user_info(token_data["access_token"])
        user = self.get_or_validate_user(profile.get("email"))
        self.save_token(user, token_data)
        return JwtService.build_auth_response(user)
