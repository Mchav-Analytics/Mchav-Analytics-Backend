# app/core/security.py
# Módulo de seguridad criptográfica y gestión de sesiones mediante firmas HMAC SHA-256

import hmac
import hashlib
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,  # NUEVO
    SecurityScopes,
)
from passlib.context import CryptContext  # NUEVO
from sqlalchemy.orm import Session

from app.core.config import SESSION_SECRET_KEY, SESSION_COOKIE_NAME
from app.core.database import get_db
from app.models.auth import User

def sign_session_id(user_id: int) -> str:
    """
    Firma un ID de usuario utilizando HMAC con la llave secreta del sistema (SESSION_SECRET_KEY).
    Produce un valor legible de la forma 'user_id.signature_hex' para almacenar en cookies HTTP-Only.
    """
    user_id_str = str(user_id)
    signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
    return f"{user_id_str}.{signature}"

def verify_session_id(signed_value: str) -> int | None:
    """
    Verifica la autenticidad e integridad de la cookie de sesión firmada.
    """
    if not signed_value:
        return None
    try:
        user_id_str, signature = signed_value.split(".", 1)
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)
    except Exception:
        pass
    return None

# NUEVO: contexto de hashing para contraseñas locales (Password Flow)
import bcrypt

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash almacenado (bcrypt)."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def hash_password(plain_password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Esquema OAuth2 tipo "Authorization Code" para el flujo real de Atlassian.
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://auth.atlassian.com/authorize",
    tokenUrl="https://auth.atlassian.com/oauth/token",
    scopes={
        "jira:read": "Leer datos de Jira (issues, boards, proyectos).",
        "jira:sync": "Disparar sincronizaciones de datos con Jira.",
        "projects:write": "Crear o modificar proyectos.",
        "admin": "Acceso administrativo completo.",
    },
    auto_error=False,
)

# NUEVO: esquema de Password Flow, 100% local — no habla con Atlassian.
# Aparece como una opción de login en el popup "Available authorizations" de Swagger.
oauth2_password_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False,
    scopes={
        "jira:read": "Leer datos de Jira (issues, boards, proyectos).",
        "jira:sync": "Disparar sincronizaciones de datos con Jira.",
        "projects:write": "Crear o modificar proyectos.",
        "admin": "Acceso administrativo completo.",
    }
)

def get_current_user(
    security_scopes: SecurityScopes,
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_password_scheme),
) -> User:
    print("--- DEBUG AUTENTICACIÓN ---")
    print(f"Cookies recibidas en request: {request.cookies}")
    print(f"Cookie specific ({SESSION_COOKIE_NAME}): {request.cookies.get(SESSION_COOKIE_NAME)}")
    print(f"Token en header Authorization: {token}")

    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Iniciá sesión con tu cuenta de Jira o con tu usuario local.",
        headers={"WWW-Authenticate": authenticate_value},
    )

    # NUEVO: se acepta el token que venga primero disponible, sin importar el origen
    # (Atlassian OAuth2 o Password Flow local); si no hay ninguno, se cae a la cookie de sesión.
    signed_value = token or request.cookies.get(SESSION_COOKIE_NAME)

    user_id = verify_session_id(signed_value)
    print(f"User ID verificado por HMAC: {user_id}")

    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id_usuario == user_id, User.activo.is_(True)).first()
    if user is None or user.rol is None:
        raise credentials_exception

    user_scopes = user.rol.scopes_list
    for scope in security_scopes.scopes:
        if scope not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol '{user.rol.nombre_rol}' no tiene el permiso: {scope}",
            )
    return user