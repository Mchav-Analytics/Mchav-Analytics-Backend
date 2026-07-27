# app/core/security.py
# Módulo de seguridad criptográfica y gestión de sesiones mediante firmas HMAC SHA-256

import hmac
import hashlib
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2AuthorizationCodeBearer, SecurityScopes
from sqlalchemy.orm import Session

from app.core.config import SESSION_SECRET_KEY, SESSION_COOKIE_NAME
from app.core.database import get_db
from app.models.auth import User

def sign_session_id(user_id: int) -> str:
    """
    Firma un ID de usuario utilizando HMAC con la llave secreta del sistema (SESSION_SECRET_KEY).
    Produce un valor legible de la forma 'user_id.signature_hex' para almacenar en cookies HTTP-Only.
    """
    user_id_str = str(user_id)  # Convertir el ID de usuario a texto
    # Generar firma HMAC con algoritmo SHA-256
    signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
    return f"{user_id_str}.{signature}"  # Concatenar ID con la firma resultante

def verify_session_id(signed_value: str) -> int | None:
    """
    Verifica la autenticidad e integridad de la cookie de sesión firmada.
    Utiliza comparación en tiempo constante (hmac.compare_digest) para evitar ataques de tiempo (Timing Attacks).
    Retorna el user_id como entero si la firma es válida, o None si ha sido alterada o es inválida.
    """
    if not signed_value:
        return None  # Retornar None si no hay valor de sesión
    try:
        # Separar el ID de usuario de la firma criptográfica por el punto delimitador
        user_id_str, signature = signed_value.split(".", 1)
        # Recalcular la firma esperada usando la llave secreta
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        # Comparación segura de la firma recibida contra la calculada
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)  # Retornar el ID del usuario verificado
    except Exception:
        pass  # Capturar cualquier error de parseo o formato incorrecto
    return None  # Retornar None si la validación falla

# Esquema OAuth2 tipo "Authorization Code", igual al que ya usás para loguear
# contra Atlassian. auto_error=False porque el token real NO viaja por header
# Authorization: la identidad se valida por la cookie de sesión (ver abajo).
# Este esquema existe para que FastAPI genere el securityScheme + scopes en
# el OpenAPI, y así Swagger muestre el checklist de permisos por endpoint.
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

def get_current_user(
    security_scopes: SecurityScopes,
    request: Request,
    db: Session = Depends(get_db),
    token_header: Optional[str] = Depends(oauth2_scheme),
) -> User:
    # --- AUDITORÍA DE COOKIES Y HEADERS ---
    print("--- DEBUG AUTENTICACIÓN ---")
    print(f"Cookies recibidas en request: {request.cookies}")
    print(f"Cookie specific ({SESSION_COOKIE_NAME}): {request.cookies.get(SESSION_COOKIE_NAME)}")
    print(f"Token en header Authorization: {token_header}")
    # -------------------------------------

    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado. Iniciá sesión con tu cuenta de Jira.",
        headers={"WWW-Authenticate": authenticate_value},
    )

    signed_value = token_header if token_header else request.cookies.get(SESSION_COOKIE_NAME)

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