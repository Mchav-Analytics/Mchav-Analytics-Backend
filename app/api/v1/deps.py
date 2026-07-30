from fastapi import HTTPException, Request, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_session_id
from app.repositories import user_repo

security_scheme = HTTPBearer(auto_error=False)

def get_current_user_id(request: Request, credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> int:
    """
    Dependencia que extrae y valida el token ya sea desde la cabecera Authorization (Bearer)
    o desde la cookie firmada 'session_id'.
    """
    signed_session = None
    
    # 1. Intentar obtener el token desde la cabecera Authorization (Bearer)
    if credentials:
        signed_session = credentials.credentials
    
    # 2. Si no viene en la cabecera, buscar en las cookies (compatibilidad)
    if not signed_session:
        signed_session = request.cookies.get("session_id")
        
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
        
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
        
    return user_id

def check_user_exists(db: Session, user_id: int):
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user