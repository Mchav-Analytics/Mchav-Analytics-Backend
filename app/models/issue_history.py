# app/models/issue_history.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class IssueHistory(Base):
    """
    Modelo ORM para el historial inmutable de cambios en los tickets de Jira (SCD2 / Event Sourcing).
    Tabla: 'issue_history'
    Guarda todos los eventos de cambio (puntos, estados, responsables) en una lnea de tiempo.
    """
    __tablename__ = "issue_history"

    id_evento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_jira = Column(String(50), nullable=False, index=True) # ID o Key del ticket (ej. PRJ-123)
    campo_modificado = Column(String(100), nullable=False)   # Ej. 'story_points', 'status', 'assignee'
    valor_anterior = Column(String(255), nullable=True)      # Valor previo al cambio
    valor_nuevo = Column(String(255), nullable=True)         # Nuevo valor asignado
    fecha_cambio = Column(DateTime, nullable=False, index=True) # Cundo ocurri este cambio en Jira
    fecha_sincronizacion = Column(DateTime, default=func.now()) # Cundo guardamos este registro
