"""Endpoints de proyectos locales y sync."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security

from app.api.v1.controllers import projects_controller
from app.api.v1.deps import get_current_user, get_project_service, get_sync_service
from app.dtos.common import DataResponseDTO, PaginatedResponseDTO
from app.dtos.jira import SyncProjectRequestDTO, SyncProjectResponseDTO
from app.dtos.project import IssueDTO, ProjectDTO, SprintDTO
from app.models import User
from app.services.project_service import ProjectService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    response_model=PaginatedResponseDTO[ProjectDTO],
    summary="Listar proyectos locales",
)
def list_projects(
    current_user: Annotated[User, Security(get_current_user, scopes=["projects:read"])],
    service: ProjectService = Depends(get_project_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _ = current_user
    return projects_controller.list_projects(service, page, page_size)


@router.post(
    "/sync",
    response_model=DataResponseDTO[SyncProjectResponseDTO],
    summary="Sincronizar proyecto desde Jira (scope projects:sync)",
)
def sync_project(
    body: SyncProjectRequestDTO,
    current_user: Annotated[User, Security(get_current_user, scopes=["projects:sync"])],
    service: SyncService = Depends(get_sync_service),
):
    _ = current_user
    return projects_controller.sync_project(body, service)


@router.get(
    "/{project_id}",
    response_model=DataResponseDTO[ProjectDTO],
    summary="Obtener proyecto por id",
)
def get_project(
    project_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["projects:read"])],
    service: ProjectService = Depends(get_project_service),
):
    _ = current_user
    return projects_controller.get_project(project_id, service)


@router.get(
    "/{project_id}/sprints",
    response_model=DataResponseDTO[list[SprintDTO]],
    summary="Listar sprints de un proyecto",
)
def list_project_sprints(
    project_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["projects:read"])],
    service: ProjectService = Depends(get_project_service),
):
    _ = current_user
    return projects_controller.list_sprints(project_id, service)


@router.get(
    "/sprints/{sprint_id}/issues",
    response_model=DataResponseDTO[list[IssueDTO]],
    summary="Listar issues de un sprint",
)
def list_sprint_issues(
    sprint_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["projects:read"])],
    service: ProjectService = Depends(get_project_service),
):
    _ = current_user
    return projects_controller.list_issues(sprint_id, service)
