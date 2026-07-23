# app/models/jira.py
# Modelos ORM de base de datos para el dominio de entidades de Jira (Proyectos, Sprints, Issues, Transiciones y Mapeos)

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

# Tabla intermedia de asociación muchos-a-muchos (N:M) entre Issues y Sprints
# Permite rastrear todos los sprints en los que ha participado un ticket a lo largo de su ciclo de vida
issues_sprints = Table(
    "issues_sprints",
    Base.metadata,
    Column("id_jira", String(50), ForeignKey("issues.id_jira", ondelete="CASCADE"), primary_key=True),
    Column("id_sprint", String(50), ForeignKey("sprints.id_sprint", ondelete="CASCADE"), primary_key=True)
)

class Proyecto(Base):
    """
    Modelo ORM que representa un Proyecto sincronizado desde Jira Cloud.
    Tabla: 'proyectos'
    """
    __tablename__ = "proyectos"

    id_proyecto = Column(String(50), primary_key=True)      # ID numérico o hash otorgado por Jira
    key_proyecto = Column(String(20), unique=True, nullable=False) # Clave corta del proyecto (ej: 'MCHAV', 'ASD')
    nombre = Column(String(100), nullable=False)            # Nombre descriptivo del proyecto
    estado = Column(String(50), default="Active")           # Estado operativo del proyecto ('Active', 'Archived')
    id_board = Column(Integer, nullable=True)               # ID del tablero principal asignado en Jira Agile

    # Relaciones ORM descendentes con cascada de eliminación
    sprints = relationship("Sprint", back_populates="proyecto", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="proyecto", cascade="all, delete-orphan")
    kpis = relationship("KpisHistoricos", back_populates="proyecto", cascade="all, delete-orphan")
    mappings = relationship("MapeoEstado", cascade="all, delete-orphan")

class Sprint(Base):
    """
    Modelo ORM que representa un Sprint de un tablero Scrum de Jira.
    Tabla: 'sprints'
    """
    __tablename__ = "sprints"

    id_sprint = Column(String(50), primary_key=True)        # ID numérico de Jira para el Sprint
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)            # Nombre asignado al Sprint (ej: 'Sprint 1 - Backend')
    estado = Column(String(50), nullable=False)             # Estado del Sprint ('active', 'future', 'closed')
    fecha_inicio = Column(DateTime(timezone=True), nullable=True) # Fecha planificada de inicio
    fecha_fin = Column(DateTime(timezone=True), nullable=True)    # Fecha planificada de cierre
    fecha_finalizacion = Column(DateTime(timezone=True), nullable=True) # Fecha real en que el Sprint fue cerrado

    # Relaciones ORM
    proyecto = relationship("Proyecto", back_populates="sprints")
    issues_activos = relationship("Issue", back_populates="sprint_activo")
    issues = relationship("Issue", secondary=issues_sprints, back_populates="sprints")
    kpis = relationship("KpisHistoricos", back_populates="sprint")

class Issue(Base):
    """
    Modelo ORM que representa un Ticket / Tarea / Historia / Bug de Jira.
    Tabla: 'issues'
    """
    __tablename__ = "issues"

    id_jira = Column(String(50), primary_key=True)          # ID numérico único asignado por Jira
    key_issue = Column(String(30), unique=True, nullable=False) # Clave alfanumérica del ticket (ej: 'MCHAV-42')
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    id_sprint = Column(String(50), ForeignKey("sprints.id_sprint", ondelete="SET NULL"), nullable=True) # Sprint actual
    summary = Column(Text, nullable=False)                  # Título o resumen principal de la tarea
    status_actual = Column(String(50), nullable=False)      # Estado en que se encuentra el ticket en Jira
    story_points = Column(Numeric(5, 2), default=0.00)     # Puntos de historia (Story Points) asignados
    created_at = Column(DateTime(timezone=True), nullable=False) # Fecha exacta de creación del ticket
    resolved_at = Column(DateTime(timezone=True), nullable=True) # Fecha exacta en que pasó a estado finalizado

    # Relaciones ORM
    proyecto = relationship("Proyecto", back_populates="issues")
    sprint_activo = relationship("Sprint", back_populates="issues_activos")
    sprints = relationship("Sprint", secondary=issues_sprints, back_populates="issues")
    transiciones = relationship("TransicionEstadoIssue", back_populates="issue", cascade="all, delete-orphan")

class TransicionEstadoIssue(Base):
    """
    Modelo ORM que almacena el historial inmutable de cambios de estado de cada ticket.
    Tabla: 'transiciones_estado_issue'
    Esencial para el cálculo preciso del Cycle Time y Lead Time.
    """
    __tablename__ = "transiciones_estado_issue"

    id_transicion = Column(Integer, primary_key=True, autoincrement=True) # Clave primaria autonumerada
    id_jira = Column(String(50), ForeignKey("issues.id_jira", ondelete="CASCADE"), nullable=False)
    estado_anterior = Column(String(50), nullable=True)     # Estado de origen de la transición (ej: 'To Do')
    estado_nuevo = Column(String(50), nullable=False)       # Estado de destino de la transición (ej: 'In Progress')
    fecha_cambio = Column(DateTime(timezone=True), nullable=False) # Estampa de tiempo exacta de la transición

    # Relación inversa hacia el ticket correspondiente
    issue = relationship("Issue", back_populates="transiciones")

class MapeoEstado(Base):
    """
    Modelo ORM que almacena la configuración de mapeo de estados de Jira a estados base del sistema.
    Tabla: 'mapeo_estados'
    Permite homogenizar diferentes nombres de flujo (ej: 'En Desarrollo', 'Doing' -> 'IN_PROGRESS').
    """
    __tablename__ = "mapeo_estados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    estado_jira = Column(String(50), nullable=False)       # Nombre del estado tal cual viene de Jira
    estado_base = Column(String(20), nullable=False)       # Categoria base ('TODO', 'IN_PROGRESS', 'DONE')
