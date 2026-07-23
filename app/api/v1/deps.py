from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_session_id
from app.repositories import user_repo

def get_current_user_id(request: Request) -> int:
    """Extrae y verifica la sesion del usuario autenticado desde las cookies HTTP."""
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user_id

def check_user_exists(db: Session, user_id: int):
    """Verifica la existencia del usuario en la base de datos."""
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user
