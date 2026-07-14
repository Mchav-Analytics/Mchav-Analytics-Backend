# app/services/auth.py
"""
Servicio de autenticación OAuth 2.0 (3LO) con Atlassian/Jira.

Cubre:
- HU-001 (Inicio de sesión / CA-01 a CA-05)
- Emisión de JWT interno (expiración 8h)
- Persistencia y refresco del token de Jira (tabla oauth_tokens)
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.jira.models import User, OAuthToken

# --------------------------------------------------------------------------
# Configuración centralizada (ver app.core.config y .env.example)
# --------------------------------------------------------------------------
JIRA_CLIENT_ID = settings.JIRA_CLIENT_ID
JIRA_CLIENT_SECRET = settings.JIRA_CLIENT_SECRET
JIRA_REDIRECT_URI = settings.JIRA_REDIRECT_URI

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8  # CA-02 HU-001: expiración máxima de 8 horas

ALLOWED_EMAIL_DOMAIN = settings.ALLOWED_EMAIL_DOMAIN  # CA-05 HU-001

AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
USERINFO_URL = "https://api.atlassian.com/me"

# NOTA: revisa en tu app de Atlassian Developer Console si usas "scopes clásicos"
# o "scopes granulares" y ajusta esta lista según corresponda.
JIRA_SCOPES = "read:jira-work read:jira-user read:me offline_access"


# --------------------------------------------------------------------------
# 1. Construcción de la URL de autorización
# --------------------------------------------------------------------------
def build_authorization_url(state: str) -> str:
    """Construye la URL hacia la que se redirige al usuario (CA-01 HU-001)."""
    params = {
        "audience": "api.atlassian.com",
        "client_id": JIRA_CLIENT_ID,
        "scope": JIRA_SCOPES,
        "redirect_uri": JIRA_REDIRECT_URI,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


# --------------------------------------------------------------------------
# 2. Intercambio de code / refresh de tokens con Atlassian
# --------------------------------------------------------------------------
async def exchange_code_for_token(code: str) -> dict:
    """Intercambia el 'code' recibido en el callback por access/refresh token."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": JIRA_CLIENT_ID,
        "client_secret": JIRA_CLIENT_SECRET,
        "code": code,
        "redirect_uri": JIRA_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(TOKEN_URL, json=payload)

    if response.status_code != 200:
        raise Exception(f"Error al intercambiar code por token: {response.text}")
    return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Renueva el access_token cuando expiró, usando el refresh_token guardado."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": JIRA_CLIENT_ID,
        "client_secret": JIRA_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(TOKEN_URL, json=payload)

    if response.status_code != 200:
        raise Exception(f"Error al refrescar el token: {response.text}")
    return response.json()


async def get_atlassian_user_info(access_token: str) -> dict:
    """Obtiene el perfil (nombre, email) del usuario autenticado en Atlassian."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(USERINFO_URL, headers=headers)

    if response.status_code != 200:
        raise Exception(f"No se pudo obtener el perfil del usuario: {response.text}")
    return response.json()


# --------------------------------------------------------------------------
# 3. JWT interno del sistema
# --------------------------------------------------------------------------
def create_jwt_token(user: User) -> str:
    """Genera el JWT que el frontend usará para llamar al resto de la API."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user.id_user),
        "email": user.email,
        "role": user.role.name,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Token inválido o expirado")


# --------------------------------------------------------------------------
# 4. Validación de usuario local (CA-03, CA-04, CA-05 HU-001)
# --------------------------------------------------------------------------
def get_or_validate_local_user(db: Session, email: str) -> User:
    """
    El sistema NO crea usuarios automáticamente: deben existir previamente
    (dados de alta por el Administrador, HU-003). Aquí solo se valida:
      - dominio corporativo
      - existencia
      - estado activo
    """
    if not email or not email.lower().endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
        raise PermissionError("El correo no pertenece a la organización.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise PermissionError("Usuario no registrado. Contacte al administrador.")
    if user.status != "active":
        raise PermissionError("Usuario deshabilitado. Contacte al administrador.")
    return user


# --------------------------------------------------------------------------
# 5. Persistencia del token de Jira (tabla oauth_tokens)
# --------------------------------------------------------------------------
def save_or_update_oauth_token(db: Session, user: User, token_data: dict) -> OAuthToken:
    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    oauth_token = db.query(OAuthToken).filter(OAuthToken.id_user == user.id_user).first()
    if oauth_token:
        oauth_token.access_token = token_data["access_token"]
        # Atlassian a veces no reenvía un refresh_token nuevo; conserva el anterior si falta.
        oauth_token.refresh_token = token_data.get("refresh_token", oauth_token.refresh_token)
        oauth_token.expires_at = expires_at
    else:
        oauth_token = OAuthToken(
            id_user=user.id_user,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_at=expires_at,
        )
        db.add(oauth_token)

    db.commit()
    db.refresh(oauth_token)
    return oauth_token


# NOTA DE ARQUITECTURA:
# El token OAuth de Atlassian que se guarda arriba (oauth_tokens) es el que
# identificó al usuario en el login (HU-001). Las consultas reales a Jira
# (proyectos, JQL, KPIs) NO usan este token individual: usan la conexión
# única por API Token que configura el Administrador (HU-006, ver
# app/services/jira.py -> JiraService). Si en el futuro necesitas que cada
# usuario consulte Jira con sus propios permisos (en vez del token admin),
# entonces sí se reutilizaría este refresh_token con una función como
# get_valid_jira_token(db, user) -> access_token.