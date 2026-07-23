# app/api/v1/deps.py
# Módulo de Inyección de Dependencias de FastAPI para autenticación, verificación de sesión y validación de usuarios

from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_session_id
from app.repositories import user_repo

def get_current_user_id(request: Request) -> int:
    """
    Dependencia que extrae y valida la cookie de sesión firmada 'session_id'.
    Verifica la firma criptográfica HMAC SHA-256. Lanza HTTP 401 si no está autenticado o expiro.
    """
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user_id

def check_user_exists(db: Session, user_id: int):
    """
    Dependencia que verifica la existencia real del usuario en la base de datos local.
    Lanza HTTP 401 si el registro fue eliminado o no existe.
    """
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user
