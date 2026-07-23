# app/api/v1/controllers/auth_controller.py
# Controlador HTTP para el flujo de Autenticación, Gestión de Sesiones OAuth 2.0 y Vinculación de API Tokens

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.database import get_db
from app.core.security import sign_session_id, verify_session_id
from app.repositories import user_repo
from app.services import auth_service
from app.schemas.auth_schema import JiraCredentialsPayload, UserResponse, JiraCredentialsResponse

# Instanciar el sub-router para los endpoints de autenticación
router = APIRouter()

def _get_authenticated_user(request: Request, db: Session):
    """Helper interno para extraer y validar la sesión activa desde las cookies HTTP."""
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    GET /api/auth/me
    Devuelve la información detallada del perfil del usuario autenticado en la sesión activa.
    """
    user = _get_authenticated_user(request, db)
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

@router.get("/jira-credentials", response_model=JiraCredentialsResponse)
async def get_jira_credentials(request: Request, db: Session = Depends(get_db)):
    """
    GET /api/auth/jira-credentials
    Obtiene el estado actual y dominio de la vinculación del API Token del usuario.
    """
    user = _get_authenticated_user(request, db)
    return {
        "jira_domain": user.jira_domain or "",
        "jira_email": user.jira_email or user.email or "",
        "api_token_vinculado": user.api_token_vinculado,
        "has_token": bool(user.jira_api_token)
    }

@router.post("/jira-credentials")
async def save_jira_credentials(payload: JiraCredentialsPayload, request: Request, db: Session = Depends(get_db)):
    """
    POST /api/auth/jira-credentials
    Prueba la conectividad con el servidor de Jira enviado y guarda el API Token verificado en el perfil del usuario.
    """
    user = _get_authenticated_user(request, db)
    
    # Probar conectividad enviando peticion de prueba a /myself
    verified_data = await auth_service.verify_jira_api_credentials(
        domain=payload.jira_domain,
        email=payload.jira_email,
        token=payload.jira_api_token
    )
    
    # Persistir credenciales verificadas en base de datos
    user_repo.update(db, db_obj=user, obj_in={
        "jira_domain": verified_data["jira_domain"],
        "jira_email": verified_data["jira_email"],
        "jira_api_token": verified_data["jira_api_token"],
        "api_token_vinculado": True
    })
    
    return {
        "status": "success",
        "message": "Credenciales de API Token de Jira vinculadas y verificadas con éxito."
    }

@router.get("/login")
def login():
    """
    GET /api/auth/login
    Genera un token de estado CSRF y redirige al usuario a la pantalla de autorización OAuth 2.0 de Atlassian.
    """
    state = auth_service.generate_oauth_state()
    authorization_url = auth_service.build_jira_oauth_url(state)
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def callback(code: str, state: str, response: Response, db: Session = Depends(get_db)):
    """
    GET /api/auth/callback
    Endpoint receptor del Callback de OAuth 2.0. Canjea el código por tokens de acceso, crea/actualiza
    el usuario en la base de datos local y establece la cookie firmada 'session_id'.
    """
    if not auth_service.validate_oauth_state(state):
        raise HTTPException(
            status_code=400, 
            detail="Estado (State) inválido o expirado. Intente iniciar sesión nuevamente."
        )
    
    # Canjear código por información del perfil y tokens
    u_data = await auth_service.exchange_code_for_user_profile(code)
    
    user = user_repo.get_by_jira_account_id(db, u_data["jira_account_id"])
    if not user:
        user = user_repo.create(db, obj_in=u_data)
    else:
        user = user_repo.update(db, db_obj=user, obj_in=u_data)
        
    # Redirigir al dashboard con la cookie firmada HMAC
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard?login=success")
    signed_session = sign_session_id(user.id_usuario)
    redirect.set_cookie(
        key="session_id", 
        value=signed_session, 
        httponly=True, 
        samesite='lax', 
        max_age=3600*24
    )
    return redirect
