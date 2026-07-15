"""Acceso a proyectos, sprints e issues persistidos en MCHAV."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.features.jira.models import Board, Issue, Project, Sprint


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def list_projects(self, page: int, page_size: int) -> tuple[list[Project], int]:
        query = self.db.query(Project).order_by(Project.project_name.asc())
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        return rows, total

    def get_project(self, project_id: int) -> Project:
        project = self.db.query(Project).filter(Project.id_project == project_id).first()
        if not project:
            raise NotFoundError("Proyecto no encontrado en MCHAV")
        return project

    def list_sprints(self, project_id: int) -> list[Sprint]:
        self.get_project(project_id)
        return (
            self.db.query(Sprint)
            .join(Board, Sprint.id_board == Board.id_board)
            .filter(Board.id_project == project_id)
            .order_by(Sprint.start_date.desc().nullslast())
            .all()
        )

    def list_issues(self, sprint_id: int) -> list[Issue]:
        return (
            self.db.query(Issue)
            .filter(Issue.id_sprint == sprint_id)
            .order_by(Issue.issue_key.asc())
            .all()
        )
