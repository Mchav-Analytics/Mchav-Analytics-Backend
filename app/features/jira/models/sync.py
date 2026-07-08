from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id_job = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, nullable=False)
    job_type = Column(String, nullable=False)
    frequency = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    logs = relationship("SyncLog", back_populates="job")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id_log = Column(Integer, primary_key=True, index=True)
    execution_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, nullable=False)
    duration_sec = Column(Integer, nullable=True)
    records_count = Column(Integer, default=0)
    message = Column(String, nullable=True)
    id_job = Column(Integer, ForeignKey("sync_jobs.id_job"), nullable=False)

    job = relationship("SyncJob", back_populates="logs")
