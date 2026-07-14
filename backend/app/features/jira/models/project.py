from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id_project = Column(Integer, primary_key=True, index=True)
    jira_project_id = Column(String, unique=True, nullable=False, index=True)
    project_key = Column(String, unique=True, nullable=False)
    project_name = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    boards = relationship("Board", back_populates="project")
    members = relationship("ProjectMember", back_populates="project")


class Board(Base):
    __tablename__ = "boards"

    id_board = Column(Integer, primary_key=True, index=True)
    jira_board_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    id_project = Column(Integer, ForeignKey("projects.id_project"), nullable=False)

    project = relationship("Project", back_populates="boards")
    sprints = relationship("Sprint", back_populates="board")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id_project_member = Column(Integer, primary_key=True, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    id_user = Column(Integer, ForeignKey("users.id_user"), nullable=False)
    id_project = Column(Integer, ForeignKey("projects.id_project"), nullable=False)

    user = relationship("User", back_populates="project_members")
    project = relationship("Project", back_populates="members")
