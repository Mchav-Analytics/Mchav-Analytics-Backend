# app/core/security.py
# Módulo de seguridad criptográfica, generación de JWT (8 horas), cifrado Fernet y RBAC

import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    SecurityScopes,
)
import bcrypt
from sqlalchemy.orm import Session

from app.core.config import SESSION_SECRET_KEY, SESSION_COOKIE_NAME
from app.core.database import get_db
from app.models.auth import User

# Configuración de JWT
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# Generación de llave Fernet derivada de SESSION_SECRET_KEY para cifrado en reposo
_derived_key = hashlib.sha256(SESSION_SECRET_KEY).digest()
_fernet_key = base64.urlsafe_b64encode(_derived_key)
_cipher_suite = Fernet(_fernet_key)

def encrypt_jira_token(plain_token: str) -> str:
    """Cifra el API Token de Jira usando Fernet antes de persistirlo en la base de datos."""
    if not plain_token:
        return ""
    if plain_token.startswith("enc:"):
        return plain_token # Ya está cifrado
    encrypted_bytes = _cipher_suite.encrypt(plain_token.encode('utf-8'))
    return f"enc:{encrypted_bytes.decode('utf-8')}"

def decrypt_jira_token(encrypted_token: str) -> str:
    """Descifra el API Token de Jira si tiene el prefijo 'enc:'."""
    if not encrypted_token:
        return ""
    if not encrypted_token.startswith("enc:"):
        return encrypted_token # Si viene legacy en texto plano
    try:
        raw_cipher = encrypted_token[4:].encode('utf-8')
        decrypted_bytes = _cipher_suite.decrypt(raw_cipher)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error descifrando token: {e}")
        return encrypted_token

def create_jwt_token(user_id: int, role: Optional[str] = None) -> str:
    """
    Genera un Token JWT con expiración estricta de 8 horas (HU-001 - CA-02).
    """
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "role": role,
        "iat": now,
        "exp": expiration
    }
    secret = SESSION_SECRET_KEY.decode('utf-8') if isinstance(SESSION_SECRET_KEY, bytes) else str(SESSION_SECRET_KEY)
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt_token(token: str) -> Optional[int]:
    """
    Verifica un Token JWT firmado y retorna el id_usuario si es válido y no ha expirado.
    """
    if not token:
        return None
    try:
        secret = SESSION_SECRET_KEY.decode('utf-8') if isinstance(SESSION_SECRET_KEY, bytes) else str(SESSION_SECRET_KEY)
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id") or payload.get("sub")
        if user_id:
            return int(user_id)
    except (jwt.PyJWTError, ValueError):
        pass
    return None

def sign_session_id(user_id: int) -> str:
    """
    Genera un Token JWT de 8 horas para mantener compatibilidad con firmas de sesión.
    """
    return create_jwt_token(user_id)

def verify_session_id(signed_value: str) -> int | None:
    """
    Verifica la autenticidad e integridad de un token JWT o cookie de sesión HMAC legacy.
    """
    if not signed_value:
        return None
    # 1. Intentar validar como JWT de 8 horas
    jwt_user_id = verify_jwt_token(signed_value)
    if jwt_user_id is not None:
        return jwt_user_id

    # 2. Fallback a HMAC legacy ('user_id.signature_hex')
    try:
        user_id_str, signature = signed_value.split(".", 1)
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)
    except Exception:
        pass
    return None

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash almacenado (bcrypt)."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def hash_password(plain_password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Esquema OAuth2 tipo "Authorization Code"
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
        detail="No autenticado o token expirado. Por favor inicia sesión con tu cuenta corporativa.",
        headers={"WWW-Authenticate": authenticate_value},
    )

    signed_value = token or request.cookies.get(SESSION_COOKIE_NAME)

    user_id = verify_session_id(signed_value)

    print(f"User ID verificado: {user_id}")

    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id_usuario == user_id, User.activo.is_(True)).first()
    if user is None:
        raise credentials_exception

    if user.rol is None:
        from app.models.auth import Role
        default_role = db.query(Role).filter(Role.nombre_rol == "Administrador").first()
        if not default_role:
            default_role = db.query(Role).first()
        if default_role:
            user.id_rol = default_role.id_rol
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise credentials_exception

    user_scopes = user.rol.scopes_list
    for scope in security_scopes.scopes:
        if scope not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol '{user.rol.nombre_rol}' no tiene el permiso requerido: {scope}",
            )
    return user
