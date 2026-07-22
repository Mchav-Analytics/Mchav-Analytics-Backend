import secrets
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import CLIENT_ID, CLIENT_SECRET, CALLBACK_URL, FRONTEND_URL, JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN
from app.core.database import get_db
from app.core.security import sign_session_id, verify_session_id
import app.models as models
from app.repositories import user_repo

router = APIRouter()

# URLs de Atlassian
AUTHORIZATION_BASE_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

# Diccionario temporal para guardar el estado (CSRF protection)
oauth_states = set()

@router.get("/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
        
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
        
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    rol_nombre = user.rol.nombre_rol if user.rol else None
    
    return {
        "id_usuario": user.id_usuario,
        "email": user.email,
        "nombre": user.nombre,
        "id_rol": user.id_rol,
        "rol": rol_nombre,
        "activo": user.activo,
        "jira_account_id": user.jira_account_id,
        "cloud_id": user.cloud_id,
        "jira_domain": user.jira_domain,
        "jira_email": user.jira_email,
        "api_token_vinculado": user.api_token_vinculado
    }

from pydantic import BaseModel
class JiraCredentialsPayload(BaseModel):
    jira_domain: str
    jira_email: str
    jira_api_token: str

@router.get("/jira-credentials")
async def get_jira_credentials(request: Request, db: Session = Depends(get_db)):
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    return {
        "jira_domain": user.jira_domain or "",
        "jira_email": user.jira_email or user.email or "",
        "api_token_vinculado": user.api_token_vinculado,
        "has_token": bool(user.jira_api_token)
    }

@router.post("/jira-credentials")
async def save_jira_credentials(payload: JiraCredentialsPayload, request: Request, db: Session = Depends(get_db)):
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    domain = payload.jira_domain.strip().rstrip('/')
    if not domain.startswith("http://") and not domain.startswith("https://"):
        domain = f"https://{domain}"
    email = payload.jira_email.strip()
    token = payload.jira_api_token.strip()
    
    if not domain or not email or not token:
        raise HTTPException(status_code=400, detail="Por favor completa todos los campos (Dominio, Correo y API Token).")
        
    # Verificar las credenciales probando una petición ligera a Jira (/rest/api/3/myself)
    import base64
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json"
    }
    test_url = f"{domain}/rest/api/3/myself"
    
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
                detail=f"No se pudo conectar al dominio {domain}. Asegúrate de escribir la URL correctamente. Error: {str(e)}"
            )
            
    # Si la verificación es exitosa, guardar en PostgreSQL
    user_repo.update(db, db_obj=user, obj_in={
        "jira_domain": domain,
        "jira_email": email,
        "jira_api_token": token,
        "api_token_vinculado": True
    })
    
    return {
        "status": "success",
        "message": "Credenciales de API Token de Jira vinculadas y verificadas con éxito."
    }

@router.get("/login")
def login():
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="JIRA_CLIENT_ID no configurado")

    state = secrets.token_urlsafe(16)
    oauth_states.add(state)
    
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
    
    import urllib.parse
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    authorization_url = f"{AUTHORIZATION_BASE_URL}?{query_string}"
    
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def callback(code: str, state: str, response: Response, db: Session = Depends(get_db)):
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Estado (State) inválido o expirado. Intente iniciar sesión nuevamente.")
    oauth_states.remove(state)
    
    # 1. Intercambiar código por Access Token
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URL
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        token_res = await client.post(TOKEN_URL, json=data)
        if token_res.status_code != 200:
            error_details = token_res.text
            print("Error details:", error_details)
            raise HTTPException(status_code=token_res.status_code, detail=f"No se pudo obtener el token de Atlassian. Error: {error_details}")
            
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        
        # 2. Obtener el cloudId del usuario
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resources_res = await client.get(RESOURCES_URL, headers=headers)
        
        if resources_res.status_code != 200:
            raise HTTPException(status_code=resources_res.status_code, detail="No se pudieron obtener los recursos accesibles de Atlassian")
            
        resources = resources_res.json()
        if not resources:
            raise HTTPException(status_code=400, detail="El usuario no tiene acceso a ningún sitio de Jira")
            
        cloud_id = resources[0]["id"]
        
        # 2.5 Obtener datos del perfil de usuario de Jira (myself) con reintentos y fallback
        profile = None
        myself_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
        myself_res = None
        
        for attempt in range(3):
            myself_res = await client.get(myself_url, headers=headers)
            if myself_res.status_code == 200:
                profile = myself_res.json()
                break
            elif myself_res.status_code == 429 and attempt < 2:
                print(f"[OAuth Callback Rate Limit 429] Reintentando obtener perfil en 2s (Intento {attempt + 1}/3)...")
                await asyncio.sleep(2.0)
            else:
                break
                
        if not profile and JIRA_DOMAIN and JIRA_EMAIL and JIRA_API_TOKEN:
            print("[OAuth Callback] Atlassian OAuth Proxy limitado (429). Usando API Token fallback para obtener perfil...")
            import base64
            creds = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
            fallback_headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
            domain_url = JIRA_DOMAIN.rstrip('/')
            if not domain_url.startswith("http"):
                domain_url = f"https://{domain_url}"
            fallback_res = await client.get(f"{domain_url}/rest/api/3/myself", headers=fallback_headers)
            if fallback_res.status_code == 200:
                profile = fallback_res.json()

        if not profile:
            error_msg = myself_res.text if myself_res else "Rate Limit 429"
            raise HTTPException(status_code=myself_res.status_code if myself_res else 400, detail=f"No se pudo obtener el perfil de usuario de Jira: {error_msg}")
            
        jira_account_id = profile.get("accountId")
        email = profile.get("emailAddress")
        nombre = profile.get("displayName")
        
        # 3. Guardar/Actualizar en PostgreSQL buscando por el accountId único
        user = user_repo.get_by_jira_account_id(db, jira_account_id)
        
        u_data = {
            "jira_account_id": jira_account_id,
            "email": email,
            "nombre": nombre,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "cloud_id": cloud_id
        }
        
        if not user:
            user = user_repo.create(db, obj_in=u_data)
        else:
            user = user_repo.update(db, db_obj=user, obj_in=u_data)
            
        # 4. Redirigir al frontend y setear cookie firmada
        redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard?login=success")
        signed_session = sign_session_id(user.id_usuario)
        redirect.set_cookie(key="session_id", value=signed_session, httponly=True, samesite='lax', max_age=3600*24)
        
        return redirect
