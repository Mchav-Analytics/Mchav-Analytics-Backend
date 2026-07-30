"""State OAuth firmado (CSRF stateless).

No depende de cookie de sesión ni de memoria del proceso, así funciona
aunque uvicorn recargue o Swagger no conserve la cookie.
"""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

_MAX_AGE_SECONDS = 600
_serializer = URLSafeTimedSerializer(
    secret_key=settings.SESSION_SECRET_KEY,
    salt="mchav-oauth-state",
)


def create_oauth_state() -> str:
    return _serializer.dumps({"purpose": "oauth_login"})


def verify_oauth_state(state: str) -> bool:
    try:
        data = _serializer.loads(state, max_age=_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and data.get("purpose") == "oauth_login"
