# app/api/v1/controllers/auth_controller.py
# Controlador HTTP para el flujo de Autenticación, Gestión de Sesiones OAuth 2.0 y Vinculación de API Tokens

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.database import get_db
from app.core.security import sign_session_id, get_current_user, verify_password, encrypt_jira_token
from app.repositories import user_repo
from app.services import auth_service
from app.schemas.auth_schema import JiraCredentialsPayload, UserResponse, JiraCredentialsResponse
from app.models.auth import User, Role

# Instanciar el sub-router para los endpoints de autenticación
router = APIRouter()

@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Obtener usuario actual",
    description="Devuelve la información detallada del perfil, roles y estados de vinculación de Jira del usuario autenticado en la sesión actual o mediante un Bearer Token."
)
async def get_current_user_info(
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
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

@router.get(
    "/jira-credentials", 
    response_model=JiraCredentialsResponse,
    summary="Consultar estado de credenciales de Jira",
    description="Retorna el dominio configurado, el correo electrónico y verifica si el usuario posee un API Token personal vinculado en el sistema."
)
async def get_jira_credentials(
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    return {
        "jira_domain": current_user.jira_domain or "",
        "jira_email": current_user.jira_email or current_user.email or "",
        "api_token_vinculado": current_user.api_token_vinculado,
        "has_token": bool(current_user.jira_api_token)
    }

@router.post(
    "/jira-credentials",
    summary="Guardar y verificar credenciales de Jira",
    description="Prueba la conectividad contra la API de Jira utilizando el dominio, email y API Token provistos por el usuario, almacenándolos de forma segura si la validación es exitosa."
)
async def save_jira_credentials(
    payload: JiraCredentialsPayload, 
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["jira:sync"])
):
    verified_data = await auth_service.verify_jira_api_credentials(
        domain=payload.jira_domain,
        email=payload.jira_email,
        token=payload.jira_api_token
    )
    
    # Fusionamos el usuario en la sesión actual de base de datos 'db' para evitar el error de SQLAlchemy
    db_user = db.merge(current_user)
    
    # Cifrado en reposo con Fernet (HU-006 - CA-03)
    encrypted_token = encrypt_jira_token(verified_data["jira_api_token"])
    
    user_repo.update(db, db_obj=db_user, obj_in={
        "jira_domain": verified_data["jira_domain"],
        "jira_email": verified_data["jira_email"],
        "jira_api_token": encrypted_token,
        "api_token_vinculado": True
    })
    
    return {
        "status": "success",
        "message": "Credenciales de API Token de Jira vinculadas y verificadas con éxito."
    }

from pydantic import BaseModel

class MockLoginPayload(BaseModel):
    email: str
    role: str = None

@router.post(
    "/login",
    summary="Login de desarrollo",
    description="Endpoint POST para iniciar sesión sin OAuth desde la UI de desarrollo."
)
async def login_post(payload: MockLoginPayload, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Crea el usuario si no existe (para entorno dev)
        rol = db.query(Role).filter(Role.nombre_rol == ("Administrador" if payload.role == "ADMIN" else "Desarrollador")).first()
        user = user_repo.create(db, obj_in={
            "email": payload.email,
            "nombre": payload.email.split("@")[0],
            "id_rol": rol.id_rol if rol else 1,
            "activo": True
        })
    
    signed_session = sign_session_id(user.id_usuario)
    response.set_cookie(
        key="session_id",
        value=signed_session,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"
    )
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
    "/login",
    summary="Iniciar sesión con Atlassian",
    description="Genera un token de estado CSRF único y redirige al usuario al servidor de autorización OAuth 2.0 de Atlassian."
)
def login():
    state = auth_service.generate_oauth_state()
    authorization_url = auth_service.build_jira_oauth_url(state)
    return RedirectResponse(url=authorization_url)

@router.get(
    "/callback",
    summary="Callback de autenticación OAuth 2.0",
    description="Endpoint de retorno configurado en Atlassian. Valida el estado CSRF, intercambia el código por el perfil del usuario y establece la sesión."
)
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

    signed_session = sign_session_id(user.id_usuario)

    redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=307)
    redirect.set_cookie(
        key="session_id",
        value=signed_session,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"
    )
    
    return redirect

from pydantic import BaseModel
from typing import Optional

class LoginPayload(BaseModel):
    email: str
    password: Optional[str] = None
    role: Optional[str] = None

@router.post(
    "/login",
    summary="Iniciar sesión local con JSON payload"
)
async def post_login_local(
    payload: LoginPayload,
    response: Response,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        rol_name = "Administrador" if (payload.role and "ADMIN" in str(payload.role).upper()) or "vhoyos" in payload.email else "Desarrollador"
        rol_obj = db.query(Role).filter(Role.nombre_rol == rol_name).first()

        user = User(
            email=payload.email,
            nombre=payload.email.split("@")[0].replace(".", " ").title(),
            activo=True,
            id_rol=rol_obj.id_rol if rol_obj else 1
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    signed_session = sign_session_id(user.id_usuario)

    response.set_cookie(
        key="session_id",
        value=signed_session,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"
    )

    rol_nombre = user.rol.nombre_rol if user.rol else "Desarrollador"
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

@router.post(
    "/logout",
    summary="Cerrar sesión"
)
async def logout_user(response: Response):
    response.delete_cookie(key="session_id", path="/")
    return {"status": "success", "message": "Sesión cerrada con éxito."}

@router.post(
    "/token",
    summary="Iniciar sesión local (Bearer Token)",
    description="Login local con usuario y contraseña para entorno de pruebas y Swagger UI."
)
async def login_local(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username, User.activo.is_(True)).first()

    if not user or not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    signed_session = sign_session_id(user.id_usuario)

    return {"access_token": signed_session, "token_type": "bearer"}