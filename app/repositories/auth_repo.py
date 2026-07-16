from sqlalchemy.orm import Session
from app.models.auth import User, Role
from app.repositories.base import CRUDBase

class CRUDUser(CRUDBase[User]):
    def get_by_jira_account_id(self, db: Session, jira_account_id: str):
        return db.query(User).filter(User.jira_account_id == jira_account_id).first()

class CRUDRole(CRUDBase[Role]):
    pass

user_repo = CRUDUser(User)
role_repo = CRUDRole(Role)
