# app/models/audit.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id_log = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), index=True, nullable=True)
    action_path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    description = Column(String(500), nullable=False)
    type = Column(String(50), default="SYSTEM", nullable=False)
