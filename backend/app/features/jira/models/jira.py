from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Sprint(Base):
    __tablename__ = "sprints"

    id_sprint = Column(Integer, primary_key=True, index=True)
    jira_sprint_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    state = Column(String, nullable=False)
    id_board = Column(Integer, ForeignKey("boards.id_board"), nullable=False)

    board = relationship("Board", back_populates="sprints")
    issues = relationship("Issue", back_populates="sprint")
    kpis = relationship("KpiHistory", back_populates="sprint")


class Issue(Base):
    __tablename__ = "issues"

    id_issue = Column(Integer, primary_key=True, index=True)
    jira_issue_id = Column(String, unique=True, nullable=False, index=True)
    issue_key = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    status = Column(String, nullable=False)
    assignee = Column(String, nullable=True)
    story_points = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    id_type = Column(Integer, ForeignKey("issue_types.id_type"), nullable=False)
    id_sprint = Column(Integer, ForeignKey("sprints.id_sprint"), nullable=True)

    sprint = relationship("Sprint", back_populates="issues")
    changelogs = relationship("StateChangelog", back_populates="issue")
    issue_type = relationship("IssueType", back_populates="issues")


class StateChangelog(Base):
    __tablename__ = "state_changelogs"

    id_changelog = Column(Integer, primary_key=True, index=True)
    status_from = Column(String, nullable=False)
    status_to = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False)
    id_issue = Column(Integer, ForeignKey("issues.id_issue"), nullable=False)

    issue = relationship("Issue", back_populates="changelogs")


class IssueType(Base):
    __tablename__ = "issue_types"

    id_type = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    issues = relationship("Issue", back_populates="issue_type")
