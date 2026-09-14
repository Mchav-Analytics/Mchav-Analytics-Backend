# app/repositories/auth_repo.py
# Repositorios especificos para el dominio de Autenticación (User y Role)

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.auth import User, Role
from app.repositories.base import CRUDBase

class CRUDUser(CRUDBase[User]):
    """Repositorio especializado para operaciones sobre la entidad User."""
    
    def get_by_jira_account_id(self, db: Session, jira_account_id: str):
        """Busca y retorna un usuario registrado mediante su identificador único de cuenta de Jira (accountId)."""
        return db.query(User).filter(User.jira_account_id == jira_account_id).first()

    def get_by_email(self, db: Session, email: str):
        """Busca y retorna un usuario registrado mediante su correo electrónico (búsqueda insensible a mayúsculas/minúsculas)."""
        if not email:
            return None
        return db.query(User).filter(func.lower(User.email) == func.lower(email.strip())).first()

class CRUDRole(CRUDBase[Role]):
    """Repositorio especializado para operaciones sobre la entidad Role."""
    pass

# Instancias singleton exportables
user_repo = CRUDUser(User)
role_repo = CRUDRole(Role)
