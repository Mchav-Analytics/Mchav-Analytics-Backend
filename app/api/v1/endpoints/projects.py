from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_session_id
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from app.repositories import user_repo, project_repo, kpi_repo, sprint_repo, issue_repo, transition_repo, mapping_repo

router = APIRouter()

def get_current_user_id(request: Request) -> int:
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
        
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user_id

def check_user_exists(db: Session, user_id: int):
    user = user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

@router.get("")
@router.get("/")
async def get_projects(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    sort: str = "id_proyecto",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
    
    projects = project_repo.get_multi(db, skip=offset, limit=limit, sort=sort, order=order)
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
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    query = kpi_repo.get_all_by_project(db, proyecto_id)
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
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    sprints = sprint_repo.get_by_project(
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
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    statuses = issue_repo.get_distinct_statuses_by_project(db, proyecto_id)
    transitions_statuses_new = transition_repo.get_distinct_new_statuses_by_project(db, proyecto_id)
    transitions_statuses_prev = transition_repo.get_distinct_prev_statuses_by_project(db, proyecto_id)
    
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
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    mappings = mapping_repo.get_by_project(db, proyecto_id)
    return mappings

@router.post("/{proyecto_id}/mappings")
async def save_project_mappings(proyecto_id: str, mappings_data: list[dict], request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    mapping_repo.delete_by_project(db, proyecto_id)
    
    for item in mappings_data:
        mapping_repo.create(db, obj_in={
            "id_proyecto": proyecto_id,
            "estado_jira": item.get("estado_jira"),
            "estado_base": item.get("estado_base")
        })
        
    calculate_and_save_kpis(db, proyecto_id)
    
    return {"message": "Mapeo guardado y KPIs recalculados con éxito"}
