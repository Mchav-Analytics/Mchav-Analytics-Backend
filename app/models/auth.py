# app/models/auth.py
# Modelos ORM de base de datos para el dominio de Autenticación, Roles y Usuarios

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Role(Base):
    """
    Modelo ORM que representa un Rol de usuario en el sistema.
    Tabla: 'roles'
    """
    __tablename__ = "roles"

    # Clave primaria autonumerada del rol
    id_rol = Column(Integer, primary_key=True, autoincrement=True)
    
    # Nombre del rol (ejemplo: 'Administrador', 'Analista', 'Líder de Proyecto')
    nombre_rol = Column(String(50), unique=True, nullable=False)

    # Relación uno-a-muchos con el modelo User
    usuarios = relationship("User", back_populates="rol")

class User(Base):
    """
    Modelo ORM que representa un Usuario del sistema MCHAV Analytics.
    Tabla: 'usuarios'
    Almacena datos del usuario, tokens de acceso OAuth 2.0 y credenciales de API Token de Jira.
    """
    __tablename__ = "usuarios"

    # Clave primaria e identificador interno del usuario en la base de datos
    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Correo electrónico principal del usuario
    email = Column(String(150), unique=True, nullable=True)
    
    # Nombre completo o de pantalla del usuario
    nombre = Column(String(150), nullable=True)
    
    # Clave foránea al rol del usuario en la tabla 'roles'
    id_rol = Column(Integer, ForeignKey("roles.id_rol", ondelete="RESTRICT"), nullable=True)
    
    # Estado del usuario (True: Activo, False: Inactivo/Bloqueado)
    activo = Column(Boolean, nullable=False, default=True)

    # Identificador único de cuenta de Jira Atlassian (AccountId)
    jira_account_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # Tokens de autenticación OAuth 2.0 de Atlassian Jira
    access_token = Column(Text, nullable=True)     # Token de acceso temporal
    refresh_token = Column(Text, nullable=True)    # Token de refresco para obtener nuevos access_tokens
    
    # Identificador del sitio/workspace de Jira Atlassian (cloudId)
    cloud_id = Column(String(100), nullable=True)
    
    # Credenciales personales de API Token de Jira (Fallback de autenticación directa Basic Auth)
    jira_domain = Column(String(255), nullable=True)   # Dominio de Jira (ej: https://empresa.atlassian.net)
    jira_email = Column(String(150), nullable=True)    # Correo de la cuenta de Jira
    jira_api_token = Column(Text, nullable=True)       # API Token cifrado/almacenado
    api_token_vinculado = Column(Boolean, nullable=False, default=False)  # Indica si las credenciales fueron verificadas

    # Estampas de tiempo automáticas de creación y última actualización
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relación inversa muchos-a-uno hacia la tabla de roles
    rol = relationship("Role", back_populates="usuarios")
