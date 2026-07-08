from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

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
