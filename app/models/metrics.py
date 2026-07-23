# app/models/metrics.py
# Modelos ORM de base de datos para el dominio de Métricas Históricas y Logs de Auditoría ETL

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class KpisHistoricos(Base):
    """
    Modelo ORM que almacena las capturas históricas de KPIs calculados por proyecto y por sprint.
    Tabla: 'kpis_historicos'
    Almacena Velocity, Throughput, Lead Time y Cycle Time.
    """
    __tablename__ = "kpis_historicos"

    id_kpi = Column(Integer, primary_key=True, autoincrement=True) # Clave primaria autonumerada
    id_proyecto = Column(String(50), ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    id_sprint = Column(String(50), ForeignKey("sprints.id_sprint", ondelete="SET NULL"), nullable=True) # None si son KPIs globales
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now()) # Estampa de tiempo del cálculo
    
    # Métricas calculadas
    velocity_total_sp = Column(Numeric(10, 2), default=0.00)          # Suma total de Story Points entregados
    velocity_promedio_historico = Column(Numeric(10, 2), default=0.00) # Promedio móvil histórico de velocidad
    throughput_issues = Column(Integer, default=0)                     # Número total de tickets completados
    lead_time_promedio_dias = Column(Numeric(8, 2), default=0.00)      # Promedio de días desde creación a resolución
    cycle_time_promedio_dias = Column(Numeric(8, 2), default=0.00)     # Promedio de días desde inicio de desarrollo a resolución

    # Relaciones ORM
    proyecto = relationship("Proyecto", back_populates="kpis")
    sprint = relationship("Sprint", back_populates="kpis")

class LogsSincronizacion(Base):
    """
    Modelo ORM para la auditoría inmutable de ejecuciones del motor de sincronización ETL.
    Tabla: 'logs_sincronizacion'
    """
    __tablename__ = "logs_sincronizacion"

    id_log = Column(Integer, primary_key=True, autoincrement=True) # Clave primaria autonumerada
    fecha_ejecucion = Column(DateTime(timezone=True), server_default=func.now()) # Fecha y hora de inicio
    tipo_sincronizacion = Column(String(50), nullable=False)      # Tipo de ejecucion ('MANUAL', 'AUTOMATIC', 'DELTA')
    resultado = Column(String(20), nullable=False)               # Resultado ('RUNNING', 'SUCCESS', 'ERROR')
    tiempo_ejecucion_segundos = Column(Integer, nullable=False)   # Duración total de la sincronización en segundos
    issues_procesados = Column(Integer, default=0)                # Cantidad total de tickets extraídos/actualizados
    detalle_error = Column(Text, nullable=True)                  # Traceback o mensaje en caso de falla
    ejecutado_por = Column(String(100), default="SYSTEM_WORKER")  # Usuario que disparó el proceso o tarea del sistema
