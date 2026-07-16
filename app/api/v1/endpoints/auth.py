import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import CLIENT_ID, CLIENT_SECRET, CALLBACK_URL, FRONTEND_URL
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
        "cloud_id": user.cloud_id
    }

@router.get("/login")
def login():
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="JIRA_CLIENT_ID no configurado")

    state = secrets.token_urlsafe(16)
    oauth_states.add(state)
    
    scopes = "read:jira-user read:jira-work read:board-scope:jira-software read:sprint:jira-software offline_access"
    
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
    
    async with httpx.AsyncClient() as client:
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
        
        # 2.5 Obtener datos del perfil de usuario de Jira (myself)
        myself_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
        myself_res = await client.get(myself_url, headers=headers)
        if myself_res.status_code != 200:
            raise HTTPException(status_code=myself_res.status_code, detail=f"No se pudo obtener el perfil de usuario de Jira: {myself_res.text}")
            
        profile = myself_res.json()
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
