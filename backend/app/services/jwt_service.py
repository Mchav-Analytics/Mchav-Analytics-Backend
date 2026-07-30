"""Emisión y decodificación del JWT interno (OAuth + local)."""

from __future__ import annotations

from app.core.scopes import scopes_for_role
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    create_access_token,
    decode_access_token,
    scopes_from_payload,
)
from app.models import User

ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_HOURS * 3600


class JwtService:
    @staticmethod
    def create_for_user(user: User) -> str:
        return create_access_token(
            subject=str(user.id_user),
            scopes=scopes_for_role(user.role.name),
            extra_claims={"email": user.email, "role": user.role.name},
        )

    @staticmethod
    def build_auth_response(user: User) -> dict:
        scopes = scopes_for_role(user.role.name)
        return {
            "access_token": JwtService.create_for_user(user),
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
            "scopes": scopes,
            "user": {
                "id_user": user.id_user,
                "email": user.email,
                "full_name": user.full_name,
                "status": user.status,
                "role": user.role.name,
            },
        }

    @staticmethod
    def decode(token: str) -> dict:
        return decode_access_token(token)

    @staticmethod
    def scopes_from_token(token: str) -> list[str]:
        return scopes_from_payload(JwtService.decode(token))
