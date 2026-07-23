import sys
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from app.repositories import user_repo, project_repo, kpi_repo, sprint_repo, issue_repo, transition_repo, mapping_repo
from app.schemas.project_schema import ProjectResponse, ProjectMappingPayload
from app.api.v1 import deps

router = APIRouter()

def _get_projects_module():
    return sys.modules.get('app.api.v1.endpoints.projects')

@router.get("", response_model=list[ProjectResponse])
@router.get("/", response_model=list[ProjectResponse])
async def get_projects(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    sort: str = "id_proyecto",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_project_repo = getattr(mod, 'project_repo', project_repo) if mod else project_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
    
    projects = active_project_repo.get_multi(db, skip=offset, limit=limit, sort=sort, order=order)
    return projects

@router.get("/{proyecto_id}/kpis")
async def get_project_kpis(
    proyecto_id: str,
    request: Request,
    sprint_id: str = None,
    limit: int = 100,
    offset: int = 0,
    sort: str = "fecha_calculo",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_kpi_repo = getattr(mod, 'kpi_repo', kpi_repo) if mod else kpi_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    query = active_kpi_repo.get_all_by_project(db, proyecto_id)
    if sprint_id:
        query = query.filter(models.KpisHistoricos.id_sprint == sprint_id)
        
    field = getattr(models.KpisHistoricos, sort, None)
    if field is None:
        field = models.KpisHistoricos.fecha_calculo
        
    if order.lower() == "desc":
        query = query.order_by(field.desc())
    else:
        query = query.order_by(field.asc())
        
    kpis = query.offset(offset).limit(limit).all()
    return kpis

@router.get("/{proyecto_id}/sprints")
async def get_project_sprints(
    proyecto_id: str,
    request: Request,
    limit: int = 100,
    offset: int = 0,
    sort: str = "fecha_inicio",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_sprint_repo = getattr(mod, 'sprint_repo', sprint_repo) if mod else sprint_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    sprints = active_sprint_repo.get_by_project(
        db,
        proyecto_id,
        skip=offset,
        limit=limit,
        sort=sort,
        order=order
    )
    return sprints

@router.get("/{proyecto_id}/statuses")
async def get_project_unique_statuses(proyecto_id: str, request: Request, db: Session = Depends(get_db)):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_issue_repo = getattr(mod, 'issue_repo', issue_repo) if mod else issue_repo
    active_transition_repo = getattr(mod, 'transition_repo', transition_repo) if mod else transition_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    statuses = active_issue_repo.get_distinct_statuses_by_project(db, proyecto_id)
    transitions_statuses_new = active_transition_repo.get_distinct_new_statuses_by_project(db, proyecto_id)
    transitions_statuses_prev = active_transition_repo.get_distinct_prev_statuses_by_project(db, proyecto_id)
    
    unique_statuses = set()
    for s in statuses:
        if s[0]: unique_statuses.add(s[0])
    for s in transitions_statuses_new:
        if s[0]: unique_statuses.add(s[0])
    for s in transitions_statuses_prev:
        if s[0]: unique_statuses.add(s[0])
        
    return sorted(list(unique_statuses))

@router.get("/{proyecto_id}/mappings")
async def get_project_mappings(proyecto_id: str, request: Request, db: Session = Depends(get_db)):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_mapping_repo = getattr(mod, 'mapping_repo', mapping_repo) if mod else mapping_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    mappings = active_mapping_repo.get_by_project(db, proyecto_id)
    return mappings

@router.post("/{proyecto_id}/mappings")
async def save_project_mappings(proyecto_id: str, mappings_data: list[dict], request: Request, db: Session = Depends(get_db)):
    mod = _get_projects_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_mapping_repo = getattr(mod, 'mapping_repo', mapping_repo) if mod else mapping_repo
    active_calc_fn = getattr(mod, 'calculate_and_save_kpis', calculate_and_save_kpis) if mod else calculate_and_save_kpis

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    active_mapping_repo.delete_by_project(db, proyecto_id)
    
    for item in mappings_data:
        active_mapping_repo.create(db, obj_in={
            "id_proyecto": proyecto_id,
            "estado_jira": item.get("estado_jira"),
            "estado_base": item.get("estado_base")
        })
        
    active_calc_fn(db, proyecto_id)
    
    return {"message": "Mapeo guardado y KPIs recalculados con éxito"}
