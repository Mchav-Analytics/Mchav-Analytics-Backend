# app/models/alerts.py
# Modelos ORM para Alertas del Sistema y Solicitudes de Ayuda de Desarrolladores (Fase 8)

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class AlertasSistema(Base):
    """
    Modelo ORM para almacenar alertas generadas automáticamente por el motor analítico (Fase 8).
    Tabla: 'alertas_sistema'
    """
    __tablename__ = "alertas_sistema"

    id_alerta = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), nullable=False, index=True)
    tipo_alerta = Column(String(50), nullable=False) # 'BLOCK_48H', 'WIP_EXCESSIVE', 'CYCLE_TIME_DEV', 'SCOPE_CREEP'
    severidad = Column(String(20), nullable=False, default="MEDIUM") # 'HIGH', 'MEDIUM', 'LOW'
    key_issue = Column(String(50), nullable=True)
    assignee_id = Column(String(100), nullable=True)
    assignee_name = Column(String(150), nullable=True)
    mensaje = Column(Text, nullable=False)
    recomendacion = Column(Text, nullable=True)
    atendida = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_atencion = Column(DateTime(timezone=True), nullable=True)

class SolicitudesAyudaDev(Base):
    """
    Modelo ORM para solicitudes de ayuda y escalamiento enviadas por desarrolladores o líderes técnicos.
    Tabla: 'solicitudes_ayuda_dev'
    """
    __tablename__ = "solicitudes_ayuda_dev"

    id_solicitud = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), nullable=False, index=True)
    solicitado_por_name = Column(String(150), nullable=False)
    solicitado_por_email = Column(String(150), nullable=False)
    rol_usuario = Column(String(50), default="DEVELOPER") # 'DEVELOPER', 'LEADER'
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=False)
    key_issue = Column(String(50), nullable=True)
    prioridad = Column(String(20), default="MEDIA") # 'ALTA', 'MEDIA', 'BAJA'
    estado = Column(String(30), default="PENDIENTE") # 'PENDIENTE', 'EN_ATENCION', 'RESUELTA'
    atendido_por_name = Column(String(150), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True), nullable=True)
