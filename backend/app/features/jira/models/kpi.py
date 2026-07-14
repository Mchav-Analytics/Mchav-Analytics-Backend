from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class KpiType(Base):
    __tablename__ = "kpi_types"

    id_kpi_type = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    unit = Column(String, nullable=False)

    history = relationship("KpiHistory", back_populates="kpi_type")


class KpiHistory(Base):
    __tablename__ = "kpi_history"

    id_kpi = Column(Integer, primary_key=True, index=True)
    metric_value = Column(Float, nullable=False)
    calc_date = Column(DateTime(timezone=True), server_default=func.now())
    id_sprint = Column(Integer, ForeignKey("sprints.id_sprint"), nullable=False)
    id_kpi_type = Column(Integer, ForeignKey("kpi_types.id_kpi_type"), nullable=False)

    sprint = relationship("Sprint", back_populates="kpis")
    kpi_type = relationship("KpiType", back_populates="history")
