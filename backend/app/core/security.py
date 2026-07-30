"""Utilidades de seguridad: JWT, scopes y hash de contraseñas."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError, PyJWTError

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


def hash_password(plain_password: str) -> str:
    """Hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash bcrypt."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    scopes: list[str] | None = None,
    extra_claims: dict | None = None,
) -> str:
    """
    Emite un JWT Bearer.

    El claim ``scope`` es una cadena separada por espacios (especificación OAuth2),
    tal como recomienda la documentación de FastAPI.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload: dict = {
        "sub": subject,
        "exp": expire,
        "scope": " ".join(scopes or []),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except (InvalidTokenError, PyJWTError) as exc:
        raise ValueError("Token inválido o expirado") from exc


def scopes_from_payload(payload: dict) -> list[str]:
    scope_claim = payload.get("scope", "")
    if isinstance(scope_claim, list):
        return [str(item) for item in scope_claim]
    if not scope_claim:
        return []
    return [part for part in str(scope_claim).split(" ") if part]
