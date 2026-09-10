# app/schemas/auth_schema.py
# Esquemas DTO (Data Transfer Objects) basados en Pydantic para el dominio de Autenticación
# Validan las peticiones HTTP de entrada y las respuestas JSON de salida

from typing import Optional
from pydantic import BaseModel, EmailStr

class JiraCredentialsPayload(BaseModel):
    """Esquema para la vinculación manual de credenciales de API Token de Jira."""
    jira_domain: str        # Dominio de Jira Cloud (ej: https://empresa.atlassian.net)
    jira_email: str         # Correo de la cuenta de Jira
    jira_api_token: str     # API Token generado en Atlassian Console

class UserResponse(BaseModel):
    """Esquema de respuesta seguro para devolver la información del perfil del usuario autenticado."""
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
        from_attributes = True # Habilita la conversión desde objetos ORM de SQLAlchemy

class JiraCredentialsResponse(BaseModel):
    """Esquema de respuesta para consultar el estado de vinculación del API Token del usuario."""
    jira_domain: str
    jira_email: str
    api_token_vinculado: bool
    has_token: bool
