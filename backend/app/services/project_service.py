"""Casos de uso de proyectos locales."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models import Issue, Project, Sprint
from app.repositories import ProjectRepository


class ProjectService:
    def __init__(self, db: Session):
        self.uow = UnitOfWork(db)
        self.projects = ProjectRepository(db)

    def list_projects(self, page: int, page_size: int) -> tuple[list[Project], int]:
        return self.projects.list(page, page_size)

    def get_project(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise NotFoundError("Proyecto no encontrado en MCHAV")
        return project

    def list_sprints(self, project_id: int) -> list[Sprint]:
        self.get_project(project_id)
        return self.projects.list_sprints(project_id)

    def list_issues(self, sprint_id: int) -> list[Issue]:
        return self.projects.list_issues(sprint_id)
