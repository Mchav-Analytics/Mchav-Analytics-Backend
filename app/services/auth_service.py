# app/services/auth_service.py
# Servicio de Lógica de Negocio para la Autenticación OAuth 2.0 y Verificación de Credenciales de Jira

import secrets
import asyncio
import base64
import urllib.parse
import httpx
from fastapi import HTTPException
from app.core.config import (
    CLIENT_ID, 
    CLIENT_SECRET, 
    CALLBACK_URL, 
    JIRA_DOMAIN, 
    JIRA_EMAIL, 
    JIRA_API_TOKEN
)

# Constantes de los endpoints oficiales de Atlassian OAuth 2.0
AUTHORIZATION_BASE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

# Estado temporal en memoria para la protección contra ataques de falsificación de peticiones (CSRF OAuth)
_oauth_states = set()

def generate_oauth_state() -> str:
    """Genera y almacena en memoria un token de estado único para prevenir ataques CSRF en el flujo OAuth."""
    state = secrets.token_urlsafe(16)
    _oauth_states.add(state)
    return state

def validate_oauth_state(state: str) -> bool:
    """Valida que el estado recibido coincida con uno generado previamente y lo consume inmediatamente."""
    if state in _oauth_states:
        _oauth_states.remove(state)
        return True
    return False

def build_jira_oauth_url(state: str) -> str:
    """Construye la URL parametrizada de autorización hacia el servidor OAuth 2.0 de Atlassian."""
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="JIRA_CLIENT_ID no está configurado en el sistema.")

    scopes = "read:jira-user read:jira-work offline_access"
    params = {
        "audience": "api.atlassian.com",
        "client_id": CLIENT_ID,
        "scope": scopes,
        "redirect_uri": CALLBACK_URL,
        "state": state,
        "response_type": "code",
        "prompt": "consent"
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"{AUTHORIZATION_BASE_URL}?{query_string}"

async def exchange_code_for_user_profile(code: str) -> dict:
    """
    Intercambia el código de autorización temporal por Tokens de acceso y refresco de Atlassian.
    Obtiene el sitio (cloudId) accesible y consulta el perfil del usuario (myself).
    Incluye lógica de reintentos ante Rate Limit (429) y fallback transparente a credenciales directas por API Token.
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URL
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Peticion POST para canjear el código por tokens
        token_res = await client.post(TOKEN_URL, json=data)
        if token_res.status_code != 200:
            error_details = token_res.text
            raise HTTPException(
                status_code=token_res.status_code, 
                detail=f"No se pudo obtener el token de Atlassian. Error: {error_details}"
            )

        tokens = token_res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        # Obtener la lista de sitios de Jira accesibles asociados al token
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resources_res = await client.get(RESOURCES_URL, headers=headers)

        if resources_res.status_code != 200:
            raise HTTPException(
                status_code=resources_res.status_code, 
                detail="No se pudieron obtener los recursos accesibles de Atlassian"
            )

        resources = resources_res.json()
        if not resources:
            raise HTTPException(status_code=400, detail="El usuario no tiene acceso a ningún sitio de Jira")

        cloud_id = resources[0]["id"] # Tomar el primer cloudId disponible

        # Obtener el perfil del usuario autenticado (/myself)
        profile = await _fetch_user_profile_with_fallback(client, cloud_id, headers)

        return {
            "jira_account_id": profile.get("accountId"),
            "email": profile.get("emailAddress"),
            "nombre": profile.get("displayName"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "cloud_id": cloud_id
        }

async def _fetch_user_profile_with_fallback(client: httpx.AsyncClient, cloud_id: str, headers: dict) -> dict:
    """Intenta consultar la API /myself con reintentos exponenciales. Si Atlassian responde 429 (Rate Limit), conmuta al API Token."""
    myself_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
    myself_res = None

    # Intentar hasta 3 veces con pausas si ocurre limitacion de frecuencia
    for attempt in range(3):
        myself_res = await client.get(myself_url, headers=headers)
        if myself_res.status_code == 200:
            return myself_res.json()
        elif myself_res.status_code == 429 and attempt < 2:
            print(f"[OAuth Callback Rate Limit 429] Reintentando obtener perfil en 2s (Intento {attempt + 1}/3)...")
            await asyncio.sleep(2.0)
        else:
            break

    # Fallback automático usando API Token si está configurado en el sistema
    if JIRA_DOMAIN and JIRA_EMAIL and JIRA_API_TOKEN:
        print("[OAuth Callback] Atlassian OAuth Proxy limitado (429). Usando API Token fallback para obtener perfil...")
        creds = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
        fallback_headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
        domain_url = JIRA_DOMAIN.rstrip('/')
        if not domain_url.startswith("http"):
            domain_url = f"https://{domain_url}"
            
        fallback_res = await client.get(f"{domain_url}/rest/api/3/myself", headers=fallback_headers)
        if fallback_res.status_code == 200:
            return fallback_res.json()

    error_msg = myself_res.text if myself_res else "Rate Limit 429"
    raise HTTPException(
        status_code=myself_res.status_code if myself_res else 400, 
        detail=f"No se pudo obtener el perfil de usuario de Jira: {error_msg}"
    )

async def verify_jira_api_credentials(domain: str, email: str, token: str) -> dict:
    """Prueba la conectividad enviando una petición de verificación Basic Auth al endpoint /myself de Jira Cloud."""
    domain_clean = domain.strip().rstrip('/')
    if not domain_clean.startswith("http://") and not domain_clean.startswith("https://"):
        domain_clean = f"https://{domain_clean}"

    email_clean = email.strip()
    token_clean = token.strip()

    if not domain_clean or not email_clean or not token_clean:
        raise HTTPException(
            status_code=400, 
            detail="Por favor completa todos los campos (Dominio, Correo y API Token)."
        )

    credentials = f"{email_clean}:{token_clean}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json"
    }
    test_url = f"{domain_clean}/rest/api/3/myself"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(test_url, headers=headers)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Jira rechazó las credenciales (HTTP {res.status_code}). Verifica tu dominio, correo y API Token."
                )
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo conectar al dominio {domain_clean}. Asegúrate de escribir la URL correctamente. Error: {str(e)}"
            )

    return {
        "jira_domain": domain_clean,
        "jira_email": email_clean,
        "jira_api_token": token_clean
    }
