from typing import Optional
from pydantic import BaseModel, EmailStr

class JiraCredentialsPayload(BaseModel):
    jira_domain: str
    jira_email: str
    jira_api_token: str

class UserResponse(BaseModel):
    id_usuario: int
    email: str
    nombre: Optional[str] = None
    id_rol: Optional[int] = None
    rol: Optional[str] = None
    activo: bool
    jira_account_id: Optional[str] = None
    cloud_id: Optional[str] = None
    jira_domain: Optional[str] = None
    jira_email: Optional[str] = None
    api_token_vinculado: bool = False

    class Config:
        from_attributes = True

class JiraCredentialsResponse(BaseModel):
    jira_domain: str
    jira_email: str
    api_token_vinculado: bool
    has_token: bool
