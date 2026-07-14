from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id_role = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=False)

    role = relationship("Role", back_populates="users")
    project_members = relationship("ProjectMember", back_populates="user")
    oauth_token = relationship("OAuthToken", back_populates="user", uselist=False)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id_token = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    id_user = Column(Integer, ForeignKey("users.id_user"), nullable=False, unique=True)

    user = relationship("User", back_populates="oauth_token")
