# app/api/v1/controllers/auth_controller.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.database import get_db
from app.core.security import sign_session_id
from app.api.v1.deps import get_current_user_id  # 👈 Importamos la dependencia dual
from app.repositories import user_repo
from app.services import auth_service

router = APIRouter()

class JiraCredentialsPayload(BaseModel):
    jira_domain: str
    jira_email: str
    jira_api_token: str

def _get_authenticated_user(request: Request, credentials, db: Session):
    """Helper interno adaptado para extraer el usuario validando Bearer Token o Cookies."""
    user_id = get_current_user_id(request, credentials)
    user = user_repo.get(db, user_id)
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return user

@router.get(
    "/me",
    summary="Obtener usuario actual",
    description="Devuelve la información detallada del perfil, roles y estados de vinculación de Jira del usuario autenticado en la sesión actual o mediante un Bearer Token."
)
async def get_current_user_info(
    request: Request, 
    db: Session = Depends(get_db),
    user_id: int = Security(get_current_user_id)
):
    """Obtiene la información del usuario autenticado en la sesión actual o vía Bearer Token."""
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

@router.get(
    "/jira-credentials",
    summary="Consultar estado de credenciales de Jira",
    description="Retorna el dominio configurado, el correo electrónico y verifica si el usuario posee un API Token personal vinculado en el sistema."
)
async def get_jira_credentials(
    request: Request, 
    db: Session = Depends(get_db),
    user_id: int = Security(get_current_user_id)
):
    """Obtiene el estado y dominio de vinculación de credenciales del usuario."""
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    return {
        "jira_domain": user.jira_domain or "",
        "jira_email": user.jira_email or user.email or "",
        "api_token_vinculado": user.api_token_vinculado,
        "has_token": bool(user.jira_api_token)
    }

@router.post(
    "/jira-credentials",
    summary="Guardar y verificar credenciales de Jira",
    description="Prueba la conectividad contra la API de Jira utilizando el dominio, email y API Token provistos por el usuario, almacenándolos de forma segura si la validación es exitosa."
)
async def save_jira_credentials(
    payload: JiraCredentialsPayload, 
    request: Request, 
    db: Session = Depends(get_db),
    user_id: int = Security(get_current_user_id)
):
    """Prueba la conectividad con Jira y guarda el API Token personal del usuario."""
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    verified_data = await auth_service.verify_jira_api_credentials(
        domain=payload.jira_domain,
        email=payload.jira_email,
        token=payload.jira_api_token
    )
    
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

@router.get(
    "/login",
    summary="Iniciar sesión con Atlassian",
    description="Genera un token de estado CSRF único y redirige al usuario al servidor de autorización OAuth 2.0 de Atlassian para iniciar el flujo de autenticación 3LO."
)
def login():
    """Genera el estado CSRF y redirige a la pantalla de autorización OAuth 2.0 de Atlassian."""
    state = auth_service.generate_oauth_state()
    authorization_url = auth_service.build_jira_oauth_url(state)
    return RedirectResponse(url=authorization_url)

@router.get(
    "/callback",
    summary="Callback de autenticación OAuth 2.0",
    description="Endpoint de retorno configurado en Atlassian. Valida el estado CSRF, intercambia el código de autorización por el perfil del usuario, crea o actualiza la cuenta localmente y establece la cookie de sesión cifrada antes de redirigir al frontend."
)
async def callback(code: str, state: str, db: Session = Depends(get_db)):
    """Callback de OAuth 2.0 que procesa el código de Atlassian, crea la cookie de sesión y redirige."""
    if not auth_service.validate_oauth_state(state):
        raise HTTPException(
            status_code=400, 
            detail="Estado (State) inválido o expirado. Intente iniciar sesión nuevamente."
        )
    
    u_data = await auth_service.exchange_code_for_user_profile(code)
    
    user = user_repo.get_by_jira_account_id(db, u_data["jira_account_id"])
    if not user:
        user = user_repo.create(db, obj_in=u_data)
    else:
        user = user_repo.update(db, db_obj=user, obj_in=u_data)
        
    signed_session = sign_session_id(user.id_usuario)

    # 1. Creamos la redirección hacia el frontend con token token como fallback
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard?login=success&token={signed_session}", status_code=302)
    
    # 2. Inyectamos la cookie HTTP-Only en la respuesta de redirección
    redirect.set_cookie(
        key="session_id", 
        value=signed_session, 
        httponly=True, 
        samesite='lax',
        path='/'
    )
    
    return redirect

@router.post("/logout", summary="Cerrar sesión")
@router.get("/logout", summary="Cerrar sesión")
def logout():
    from fastapi.responses import JSONResponse
    res = JSONResponse(content={"status": "success", "message": "Sesión cerrada correctamente."})
    res.delete_cookie(key="session_id", path="/")
    return res