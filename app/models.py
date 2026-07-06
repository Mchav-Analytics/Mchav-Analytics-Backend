from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Tabla intermedia de muchos a muchos para Sprints e Issues
issues_sprints = Table(
    "issues_sprints",
    Base.metadata,
    Column("id_jira", String(50), ForeignKey("issues.id_jira", ondelete="CASCADE"), primary_key=True),
    Column("id_sprint", String(50), ForeignKey("sprints.id_sprint", ondelete="CASCADE"), primary_key=True)
)

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
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rol = relationship("Role", back_populates="usuarios")

class Proyecto(Base):
    __tablename__ = "proyectos"

    id_proyecto = Column(String(50), primary_key=True)
    key_proyecto = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    estado = Column(String(50), default="Active")

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

class KpisHistoricos(Base):
    __tablename__ = "kpis_historicos"

    id_kpi = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    id_sprint = Column(String(50), ForeignKey("sprints.id_sprint", ondelete="SET NULL"), nullable=True)
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now())
    velocity_total_sp = Column(Numeric(10, 2), default=0.00)
    velocity_promedio_historico = Column(Numeric(10, 2), default=0.00)
    throughput_issues = Column(Integer, default=0)
    lead_time_promedio_dias = Column(Numeric(8, 2), default=0.00)
    cycle_time_promedio_dias = Column(Numeric(8, 2), default=0.00)

    proyecto = relationship("Proyecto", back_populates="kpis")
    sprint = relationship("Sprint", back_populates="kpis")

class LogsSincronizacion(Base):
    __tablename__ = "logs_sincronizacion"

    id_log = Column(Integer, primary_key=True, autoincrement=True)
    fecha_ejecucion = Column(DateTime(timezone=True), server_default=func.now())
    tipo_sincronizacion = Column(String(50), nullable=False)
    resultado = Column(String(20), nullable=False)
    tiempo_ejecucion_segundos = Column(Integer, nullable=False)
    issues_procesados = Column(Integer, default=0)
    detalle_error = Column(Text, nullable=True)
    ejecutado_por = Column(String(100), default="SYSTEM_WORKER")

class MapeoEstado(Base):
    __tablename__ = "mapeo_estados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    estado_jira = Column(String(50), nullable=False)
    estado_base = Column(String(20), nullable=False)
