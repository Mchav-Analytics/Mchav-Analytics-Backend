from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user, get_project_service, get_sync_service, require_role
from app.schemas.common import DataResponse, PaginatedMeta, PaginatedResponse
from app.schemas.jira import SyncProjectRequest, SyncProjectResponse
from app.schemas.project import IssueOut, ProjectOut, SprintOut
from app.services.project import ProjectService
from app.services.sync import SyncService

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectOut])
def listar_proyectos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ProjectService = Depends(get_project_service),
    _current_user=Depends(get_current_user),
):
    rows, total = service.list_projects(page=page, page_size=page_size)
    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, page_size=page_size),
    )


@router.post("/sync", response_model=DataResponse[SyncProjectResponse])
def sincronizar_proyecto(
    body: SyncProjectRequest,
    service: SyncService = Depends(get_sync_service),
    _admin=Depends(require_role("Administrador")),
):
    result = service.sync_project(body.project_key)
    return DataResponse(data=SyncProjectResponse(**result))


@router.get("/{project_id}", response_model=DataResponse[ProjectOut])
def obtener_proyecto(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    _current_user=Depends(get_current_user),
):
    return DataResponse(data=service.get_project(project_id))


@router.get("/{project_id}/sprints", response_model=DataResponse[list[SprintOut]])
def listar_sprints_proyecto(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    _current_user=Depends(get_current_user),
):
    return DataResponse(data=service.list_sprints(project_id))


@router.get("/sprints/{sprint_id}/issues", response_model=DataResponse[list[IssueOut]])
def listar_issues_sprint(
    sprint_id: int,
    service: ProjectService = Depends(get_project_service),
    _current_user=Depends(get_current_user),
):
    return DataResponse(data=service.list_issues(sprint_id))
