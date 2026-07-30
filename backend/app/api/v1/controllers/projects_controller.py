"""Controlador de proyectos locales y sincronización."""

from __future__ import annotations

from app.dtos.common import DataResponseDTO, PaginatedMetaDTO, PaginatedResponseDTO
from app.dtos.jira import SyncProjectRequestDTO, SyncProjectResponseDTO
from app.dtos.project import IssueDTO, ProjectDTO, SprintDTO
from app.services.project_service import ProjectService
from app.services.sync_service import SyncService


def list_projects(
    service: ProjectService, page: int, page_size: int
) -> PaginatedResponseDTO[ProjectDTO]:
    rows, total = service.list_projects(page=page, page_size=page_size)
    return PaginatedResponseDTO(
        data=rows,
        meta=PaginatedMetaDTO(total=total, page=page, page_size=page_size),
    )


def sync_project(
    body: SyncProjectRequestDTO, service: SyncService
) -> DataResponseDTO[SyncProjectResponseDTO]:
    result = service.sync_project(body.project_key)
    return DataResponseDTO(data=SyncProjectResponseDTO(**result))


def get_project(
    project_id: int, service: ProjectService
) -> DataResponseDTO[ProjectDTO]:
    return DataResponseDTO(data=service.get_project(project_id))


def list_sprints(
    project_id: int, service: ProjectService
) -> DataResponseDTO[list[SprintDTO]]:
    return DataResponseDTO(data=service.list_sprints(project_id))


def list_issues(
    sprint_id: int, service: ProjectService
) -> DataResponseDTO[list[IssueDTO]]:
    return DataResponseDTO(data=service.list_issues(sprint_id))
