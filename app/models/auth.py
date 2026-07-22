from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id_rol = Column(Integer, primary_key=True, autoincrement=True)
    nombre_rol = Column(String(50), unique=True, nullable=False)

    usuarios = relationship("User", back_populates="rol")

class User(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(150), unique=True, nullable=True)
    nombre = Column(String(150), nullable=True)
    id_rol = Column(Integer, ForeignKey("roles.id_rol", ondelete="RESTRICT"), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    # Identificador único de Jira
    jira_account_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # Tokens de autenticación
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    
    # El cloudId del workspace de Jira al que el usuario tiene acceso
    cloud_id = Column(String(100), nullable=True)
    
    # Credenciales de API Token de Jira para extracción directa (Basic Auth)
    jira_domain = Column(String(255), nullable=True)
    jira_email = Column(String(150), nullable=True)
    jira_api_token = Column(Text, nullable=True)
    api_token_vinculado = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rol = relationship("Role", back_populates="usuarios")
