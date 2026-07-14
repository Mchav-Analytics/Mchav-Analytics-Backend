from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.features.jira.models import Issue, Project, Sprint
from app.schemas.common import DataResponse, PaginatedMeta, PaginatedResponse
from app.schemas.jira import SyncProjectRequest, SyncProjectResponse
from app.schemas.project import IssueOut, ProjectOut, SprintOut
from app.services.jira import JiraService
from app.services.sync import SyncService

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse[ProjectOut])
async def listar_proyectos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    query = db.query(Project).order_by(Project.project_name.asc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        data=rows,
        meta=PaginatedMeta(total=total, page=page, page_size=page_size),
    )


@router.get("/{project_id}", response_model=DataResponse[ProjectOut])
async def obtener_proyecto(
    project_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id_project == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado en MCHAV")
    return DataResponse(data=project)


@router.get("/{project_id}/sprints", response_model=DataResponse[list[SprintOut]])
async def listar_sprints_proyecto(
    project_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    from app.features.jira.models import Board

    sprints = (
        db.query(Sprint)
        .join(Board, Sprint.id_board == Board.id_board)
        .filter(Board.id_project == project_id)
        .order_by(Sprint.start_date.desc().nullslast())
        .all()
    )
    return DataResponse(data=sprints)


@router.get("/sprints/{sprint_id}/issues", response_model=DataResponse[list[IssueOut]])
async def listar_issues_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    issues = db.query(Issue).filter(Issue.id_sprint == sprint_id).order_by(Issue.issue_key.asc()).all()
    return DataResponse(data=issues)


@router.post(
    "/sync",
    response_model=DataResponse[SyncProjectResponse],
    dependencies=[Depends(require_role("Administrador"))],
)
async def sincronizar_proyecto(body: SyncProjectRequest, db: Session = Depends(get_db)):
    service = SyncService(db=db, jira=JiraService())
    try:
        result = service.sync_project(body.project_key)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DataResponse(data=SyncProjectResponse(**result))
