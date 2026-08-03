# app/api/v1/controllers/projects_controller.py
# Controlador HTTP para el listado de Proyectos, Sprints, KPIs calculados y Mapeos de Estado

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from app.repositories import user_repo, project_repo, kpi_repo, sprint_repo, issue_repo, transition_repo, mapping_repo
from app.schemas.project_schema import ProjectResponse, ProjectMappingPayload
from app.api.v1 import deps

# Sub-router para la gestión de proyectos
router = APIRouter()

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
    """
    GET /api/v1/projects
    Lista los proyectos sincronizados en el sistema con soporte completo de paginación y ordenamiento.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
    
    projects = project_repo.get_multi(db, skip=offset, limit=limit, sort=sort, order=order)
    return projects

@router.get("/{proyecto_id}/kpis")
async def get_project_kpis(
    request: Request,
    proyecto_id: str,
    sprint_id: str = None,
    limit: int = 100,
    offset: int = 0,
    sort: str = "fecha_calculo",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/kpis
    Obtiene los KPIs calculados de un proyecto. Permite filtrar opcionalmente por sprint_id.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
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
    request: Request,
    proyecto_id: str,
    limit: int = 100,
    offset: int = 0,
    sort: str = "fecha_inicio",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/sprints
    Obtiene la lista de sprints pertenecientes al proyecto con paginación y ordenamiento.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
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
async def get_project_unique_statuses(
    request: Request,
    proyecto_id: str, 
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/statuses
    Obtiene el conjunto único de nombres de estado encontrados en las tareas y transiciones del proyecto.
    Útil para construir las listas desplegables en la interfaz de configuración de mapeos.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
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
async def get_project_mappings(
    request: Request,
    proyecto_id: str, 
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/mappings
    Obtiene las reglas de mapeo de estado activas para el proyecto.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
    mappings = mapping_repo.get_by_project(db, proyecto_id)
    return mappings

@router.post("/{proyecto_id}/mappings")
async def save_project_mappings(
    request: Request,
    proyecto_id: str, 
    mappings_data: list[dict], 
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/projects/{proyecto_id}/mappings
    Reemplaza las reglas de mapeo de estado de un proyecto y dispara de inmediato el recalculado completo de KPIs.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
    # Eliminar configuraciones previas del proyecto
    mapping_repo.delete_by_project(db, proyecto_id)
    
    # Insertar los nuevos mapeos recibidos
    for item in mappings_data:
        mapping_repo.create(db, obj_in={
            "id_proyecto": proyecto_id,
            "estado_jira": item.get("estado_jira"),
            "estado_base": item.get("estado_base")
        })
        
    # Recalcular métricas aplicando los nuevos criterios de estado
    calculate_and_save_kpis(db, proyecto_id)
    
    return {"message": "Mapeo guardado y KPIs recalculados con éxito"}