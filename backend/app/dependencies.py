from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.features.jira.models import User
from app.services.auth import decode_jwt_token
from app.services.jira import JiraService
from app.services.kpi import KpiService
from app.services.project import ProjectService
from app.services.sync import SyncService

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_jwt_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token inválido o expirado") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(User).filter(User.id_user == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def require_role(role_name: str):
    def _require(user: User = Depends(get_current_user)) -> User:
        if not getattr(user, "role", None) or user.role.name != role_name:
            raise HTTPException(status_code=403, detail="Permiso denegado")
        return user

    return _require


def get_jira_service() -> JiraService:
    return JiraService()


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def get_kpi_service(db: Session = Depends(get_db)) -> KpiService:
    return KpiService(db)


def get_sync_service(
    db: Session = Depends(get_db),
    jira: JiraService = Depends(get_jira_service),
) -> SyncService:
    return SyncService(db=db, jira=jira)
