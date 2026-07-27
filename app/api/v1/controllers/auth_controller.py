# app/api/v1/controllers/auth_controller.py
# Controlador HTTP para el flujo de Autenticación, Gestión de Sesiones OAuth 2.0 y Vinculación de API Tokens

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.database import get_db
from app.core.security import sign_session_id, get_current_user
from app.repositories import user_repo
from app.services import auth_service
from app.schemas.auth_schema import JiraCredentialsPayload, UserResponse, JiraCredentialsResponse
from app.models.auth import User

# Instanciar el sub-router para los endpoints de autenticación
router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    """
    GET /api/auth/me
    Devuelve la información detallada del perfil del usuario autenticado exigiendo el scope 'jira:read'.
    """
    rol_nombre = current_user.rol.nombre_rol if current_user.rol else None
    
    return {
        "id_usuario": current_user.id_usuario,
        "email": current_user.email,
        "nombre": current_user.nombre,
        "id_rol": current_user.id_rol,
        "rol": rol_nombre,
        "activo": current_user.activo,
        "jira_account_id": current_user.jira_account_id,
        "cloud_id": current_user.cloud_id,
        "jira_domain": current_user.jira_domain,
        "jira_email": current_user.jira_email,
        "api_token_vinculado": current_user.api_token_vinculado
    }

@router.get("/jira-credentials", response_model=JiraCredentialsResponse)
async def get_jira_credentials(
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    """
    GET /api/auth/jira-credentials
    Obtiene el estado actual y dominio de la vinculación del API Token del usuario.
    """
    return {
        "jira_domain": current_user.jira_domain or "",
        "jira_email": current_user.jira_email or current_user.email or "",
        "api_token_vinculado": current_user.api_token_vinculado,
        "has_token": bool(current_user.jira_api_token)
    }

@router.post("/jira-credentials")
async def save_jira_credentials(
    payload: JiraCredentialsPayload, 
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["jira:sync"])
):
    """
    POST /api/auth/jira-credentials
    Prueba la conectividad con el servidor de Jira enviado y guarda el API Token verificado.
    """
    # Probar conectividad enviando peticion de prueba a /myself
    verified_data = await auth_service.verify_jira_api_credentials(
        domain=payload.jira_domain,
        email=payload.jira_email,
        token=payload.jira_api_token
    )
    
    # Persistir credenciales verificadas en base de datos
    user_repo.update(db, db_obj=current_user, obj_in={
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
    if not auth_service.validate_oauth_state(state):
        raise HTTPException(
            status_code=400, 
            detail="Estado (State) inválido o expirado. Intente iniciar sesión nuevamente."
        )
    
    u_data = await auth_service.exchange_code_for_user_profile(code)
    
    user = user_repo.get_by_jira_account_id(db, u_data["jira_account_id"])
    if not user:
        rol_default = db.query(Role).filter(Role.nombre_rol == "Administrador").first()
        if rol_default:
            u_data["id_rol"] = rol_default.id_rol
        user = user_repo.create(db, obj_in=u_data)
    else:
        user = user_repo.update(db, db_obj=user, obj_in=u_data)

    # Generar el token firmado con el ID real del usuario de la BD
    signed_session = sign_session_id(user.id_usuario)

    # Redirigir al dashboard del frontend limpio
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=307)
    
    # Asignar la cookie HTTP-Only de manera segura directamente en la respuesta
    redirect.set_cookie(
        key="session_id",
        value=signed_session,
        httponly=True,
        secure=False,  # Ponlo en True si usas HTTPS en producción
        samesite="lax",
        path="/"
    )
    
    return redirect