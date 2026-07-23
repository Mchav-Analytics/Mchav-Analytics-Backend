from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

# Tabla intermedia de muchos a muchos para Sprints e Issues
issues_sprints = Table(
    "issues_sprints",
    Base.metadata,
    Column("id_jira", String(50), ForeignKey("issues.id_jira", ondelete="CASCADE"), primary_key=True),
    Column("id_sprint", String(50), ForeignKey("sprints.id_sprint", ondelete="CASCADE"), primary_key=True)
)

class Proyecto(Base):
    __tablename__ = "proyectos"

    id_proyecto = Column(String(50), primary_key=True)
    key_proyecto = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    estado = Column(String(50), default="Active")
    id_board = Column(Integer, nullable=True)

    sprints = relationship("Sprint", back_populates="proyecto", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="proyecto", cascade="all, delete-orphan")
    kpis = relationship("KpisHistoricos", back_populates="proyecto", cascade="all, delete-orphan")
    mappings = relationship("MapeoEstado", cascade="all, delete-orphan")

class Sprint(Base):
    __tablename__ = "sprints"

    id_sprint = Column(String(50), primary_key=True)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)
    estado = Column(String(50), nullable=False)
    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    fecha_finalizacion = Column(DateTime(timezone=True), nullable=True)

    proyecto = relationship("Proyecto", back_populates="sprints")
    issues_activos = relationship("Issue", back_populates="sprint_activo")
    issues = relationship("Issue", secondary=issues_sprints, back_populates="sprints")
    kpis = relationship("KpisHistoricos", back_populates="sprint")

class Issue(Base):
    __tablename__ = "issues"

    id_jira = Column(String(50), primary_key=True)
    key_issue = Column(String(30), unique=True, nullable=False)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    id_sprint = Column(String(50), ForeignKey("sprints.id_sprint", ondelete="SET NULL"), nullable=True)
    summary = Column(Text, nullable=False)
    status_actual = Column(String(50), nullable=False)
    story_points = Column(Numeric(5, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    proyecto = relationship("Proyecto", back_populates="issues")
    sprint_activo = relationship("Sprint", back_populates="issues_activos")
    sprints = relationship("Sprint", secondary=issues_sprints, back_populates="issues")
    transiciones = relationship("TransicionEstadoIssue", back_populates="issue", cascade="all, delete-orphan")

class TransicionEstadoIssue(Base):
    __tablename__ = "transiciones_estado_issue"

    id_transicion = Column(Integer, primary_key=True, autoincrement=True)
    id_jira = Column(String(50), ForeignKey("issues.id_jira", ondelete="CASCADE"), nullable=False)
    estado_anterior = Column(String(50), nullable=True)
    estado_nuevo = Column(String(50), nullable=False)
    fecha_cambio = Column(DateTime(timezone=True), nullable=False)

    issue = relationship("Issue", back_populates="transiciones")

class MapeoEstado(Base):
    __tablename__ = "mapeo_estados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    estado_jira = Column(String(50), nullable=False)
    estado_base = Column(String(20), nullable=False)
