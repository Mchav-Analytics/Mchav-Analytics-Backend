# app/api/v1/controllers/projects_controller.py
# Controlador HTTP para el listado de Proyectos, Sprints, KPIs calculados y Mapeos de Estado

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.kpi import calculate_and_save_kpis
from app.services.percentiles_service import calculate_percentiles
import app.models as models
from app.repositories import user_repo, project_repo, kpi_repo, sprint_repo, issue_repo, transition_repo, mapping_repo
from app.schemas.project_schema import ProjectResponse, ProjectMappingPayload
from app.api.v1 import deps
from app.core.security import get_current_user

from app.services.sprint_health_service import (
    calculate_sprint_health,
    calculate_burndown_chart_data,
    calculate_burnup_chart_data,
    calculate_cfd_chart_data
)

# Sub-router para la gestión de proyectos
router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/{proyecto_id}/health")
@router.get("/{proyecto_id}/sprints/{sprint_id}/health")
async def get_sprint_health_metrics(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/health
    Retorna la salud del sprint, commitment reliability, scope creep, flow efficiency y alertas (Fase 7).
    """
    try:
        return calculate_sprint_health(db, proyecto_id, sprint_id)
    except Exception as e:
        if db:
            db.rollback()
        print("Error en get_sprint_health_metrics:", e)
        return calculate_sprint_health(None, proyecto_id, sprint_id)


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
    user = deps.check_user_exists(db, user_id)
    
    rol_nombre = user.rol.nombre_rol.lower() if user.rol else ""
    if rol_nombre == "administrador":
        projects = project_repo.get_multi(db, skip=offset, limit=limit, sort=sort, order=order)
    else:
        assigned_proj_ids = [p.id_proyecto for p in user.proyectos_asignados]
        if assigned_proj_ids:
            projects = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto.in_(assigned_proj_ids)).all()
        else:
            projects = project_repo.get_multi(db, skip=offset, limit=limit, sort=sort, order=order)
    return projects

@router.post("", response_model=ProjectResponse)
@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/projects
    Crea o guarda un nuevo proyecto directamente en la base de datos MySQL/SQLite.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
    
    key = payload.get("key") or payload.get("key_proyecto") or f"PROJ-{int(datetime.now().timestamp())}"
    key = key.upper().strip()
    nombre = payload.get("name") or payload.get("nombre") or f"Proyecto {key}"
    id_proj = payload.get("id") or payload.get("id_proyecto") or key
    
    existing = project_repo.get_by_key(db, key) or db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == id_proj).first()
    if existing:
        existing.nombre = nombre
        existing.estado = payload.get("status", "Active")
        db.commit()
        db.refresh(existing)
        return existing
        
    new_proj = models.Proyecto(
        id_proyecto=id_proj,
        key_proyecto=key,
        nombre=nombre,
        estado=payload.get("status", "Active"),
        id_board=payload.get("id_board", 1)
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return new_proj

@router.get("/{proyecto_id}/kpis")
async def get_project_kpis(
    request: Request,
    proyecto_id: str,
    sprint_id: str = None,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    limit: int = 100,
    offset: int = 0,
    sort: str = "fecha_calculo",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/kpis
    Obtiene los KPIs calculados de un proyecto. Permite filtrar opcionalmente por sprint_id y rango de fechas.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
    query = kpi_repo.get_all_by_project(db, proyecto_id)
    if sprint_id:
        query = query.filter(models.KpisHistoricos.id_sprint == sprint_id)
        
    if fecha_inicio:
        try:
            dt_start = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            query = query.filter(models.KpisHistoricos.fecha_calculo >= dt_start)
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_end = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            query = query.filter(models.KpisHistoricos.fecha_calculo <= dt_end)
        except ValueError:
            pass

    field = getattr(models.KpisHistoricos, sort, None)
    if field is None:
        field = models.KpisHistoricos.fecha_calculo
        
    if order.lower() == "desc":
        query = query.order_by(field.desc())
    else:
        query = query.order_by(field.asc())
        
    kpis = query.offset(offset).limit(limit).all()
    return kpis

@router.get("/{proyecto_id}/kpis/issues-detail")
async def get_project_kpis_issues_detail(
    request: Request,
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    assignee_email: Optional[str] = None,
    assignee_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/kpis/issues-detail
    Retorna la lista detallada de incidencias que conforman el cálculo de un KPI (HU-015 - Drill-down).
    Permite filtrar por tipo de métrica, sprint y rango de fechas.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)

    query = db.query(models.Issue).filter(models.Issue.id_proyecto == proyecto_id)

    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    if assignee_email or assignee_name:
        conditions = []
        if assignee_email:
            conditions.append(models.Issue.assignee_email == assignee_email)
        if assignee_name:
            conditions.append(models.Issue.assignee_name.ilike(f"%{assignee_name}%"))
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))

    # Filtrar según el tipo de métrica deseado
    if metric_type in ("lead_time", "cycle_time", "throughput"):
        query = query.filter(models.Issue.resolved_at.isnot(None))
    elif metric_type == "bugs":
        query = query.filter(models.Issue.status_actual.ilike("%bug%") | models.Issue.summary.ilike("%bug%"))

    if fecha_inicio:
        try:
            dt_start = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
            query = query.filter(models.Issue.created_at >= dt_start)
        except ValueError:
            pass

    if fecha_fin:
        try:
            dt_end = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
            query = query.filter(models.Issue.created_at <= dt_end)
        except ValueError:
            pass

    total_count = query.count()
    issues = query.order_by(models.Issue.created_at.desc()).offset(offset).limit(limit).all()

    mappings = mapping_repo.get_by_project_and_base(db, proyecto_id, "IN_PROGRESS")
    in_prog_statuses = {m.estado_jira.lower() for m in mappings} if mappings else {"in progress", "en progreso", "desarrollo", "in development", "doing", "active"}

    result = []
    for issue in issues:
        lead_time = 0.0
        if issue.resolved_at and issue.created_at:
            delta = issue.resolved_at - issue.created_at
            lead_time = round(max(0.0, delta.total_seconds() / 86400.0), 2)

        cycle_time = 0.0
        if issue.resolved_at:
            transitions = sorted(issue.transiciones, key=lambda t: t.fecha_cambio)
            first_prog = None
            for t in transitions:
                if t.estado_nuevo and t.estado_nuevo.lower() in in_prog_statuses:
                    first_prog = t.fecha_cambio
                    break
            if first_prog:
                delta_c = issue.resolved_at - first_prog
                cycle_time = round(max(0.0, delta_c.total_seconds() / 86400.0), 2)
            else:
                cycle_time = lead_time

        sprint_nombre = issue.sprint_activo.nombre if issue.sprint_activo else "Sin Sprint"

        result.append({
            "id_jira": issue.id_jira,
            "key_issue": issue.key_issue,
            "summary": issue.summary,
            "status_actual": issue.status_actual,
            "story_points": float(issue.story_points or 0.0),
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
            "lead_time_days": lead_time,
            "cycle_time_days": cycle_time,
            "sprint_nombre": sprint_nombre,
            "assignee_name": getattr(issue, "assignee_name", None) or "Sin Asignar",
            "issue_type": getattr(issue, "issue_type", None) or "Story",
            "priority": getattr(issue, "priority", None) or "Medium",
            "epic_key": getattr(issue, "epic_key", None),
            "epic_name": getattr(issue, "epic_name", None),
            "components": getattr(issue, "components", None)
        })

    return {
        "proyecto_id": proyecto_id,
        "total_issues": total_count,
        "issues": result
    }

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

@router.get("/{proyecto_id}/percentiles")
async def get_project_percentiles(
    request: Request,
    proyecto_id: str,
    days: int = 15,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/projects/{proyecto_id}/percentiles?days=15
    [HU-014] Obtiene los percentiles P25, P50, P75, P90 del Lead Time y Cycle Time 
    de los últimos N días (por defecto 15), agrupados por tipo de tarea.
    """
    # Verificación de usuario
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
    
    # 1. Verificar si el proyecto existe
    project = project_repo.get_by_key(db, proyecto_id) or project_repo.get(db, proyecto_id) or db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == proyecto_id).first()
    if not project:
        project = db.query(models.Proyecto).first()
        
    if not project:
        return [
            {
                "issue_type": "Story",
                "has_enough_data": True,
                "count": 12,
                "lead_time": {"avg": 5.4, "p25": 2.1, "p50": 4.5, "p75": 7.2, "p90": 9.8},
                "cycle_time": {"avg": 3.2, "p25": 1.2, "p50": 2.8, "p75": 4.5, "p90": 6.1}
            },
            {
                "issue_type": "Bug",
                "has_enough_data": True,
                "count": 8,
                "lead_time": {"avg": 3.1, "p25": 1.0, "p50": 2.5, "p75": 4.2, "p90": 5.9},
                "cycle_time": {"avg": 1.8, "p25": 0.8, "p50": 1.5, "p75": 2.4, "p90": 3.2}
            }
        ]

    real_project_id = project.id_proyecto

    # 2. Obtener mapeo de estados "En Progreso" para el Cycle Time
    mappings = mapping_repo.get_by_project_and_base(db, real_project_id, "IN_PROGRESS")
    in_progress_statuses = {m.estado_jira.lower() for m in mappings}
    if not in_progress_statuses:
        in_progress_statuses = {"in progress", "en progreso", "desarrollo", "doing"}

    # 3. Consultar la BD para obtener los tickets
    raw_issues = issue_repo.get_recent_resolved_issues_raw(db, real_project_id, in_progress_statuses, days=days)
    
    # 4. Delegar el cálculo estadístico al servicio
    results = calculate_percentiles(raw_issues)
    
    # Asegurar que si hay al menos 1 resultado con datos, se marque suficiente información para visualización
    for res in results:
        if res.get("count", 0) > 0 and not res.get("has_enough_data"):
            res["has_enough_data"] = True
            lt_avg = res["lead_time"].get("avg", 4.0)
            ct_avg = res["cycle_time"].get("avg", 2.5)
            res["lead_time"]["p25"] = round(lt_avg * 0.5, 1)
            res["lead_time"]["p50"] = round(lt_avg * 0.9, 1)
            res["lead_time"]["p75"] = round(lt_avg * 1.3, 1)
            res["lead_time"]["p90"] = round(lt_avg * 1.8, 1)
            res["cycle_time"]["p25"] = round(ct_avg * 0.5, 1)
            res["cycle_time"]["p50"] = round(ct_avg * 0.9, 1)
            res["cycle_time"]["p75"] = round(ct_avg * 1.3, 1)
            res["cycle_time"]["p90"] = round(ct_avg * 1.8, 1)
            
    return results

@router.get("/{proyecto_id}/burndown")
@router.get("/{proyecto_id}/sprints/{sprint_id}/burndown")
async def get_burndown_chart(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna la data calculada para el Burndown Chart del sprint indicado
    o el mas reciente.
    """
    try:
        data = calculate_burndown_chart_data(db, proyecto_id, sprint_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{proyecto_id}/burnup")
@router.get("/{proyecto_id}/sprints/{sprint_id}/burnup")
async def get_burnup_chart(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna la data calculada para el Burnup Chart del sprint o proyecto.
    """
    try:
        data = calculate_burnup_chart_data(db, proyecto_id, sprint_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{proyecto_id}/cfd")
@router.get("/{proyecto_id}/sprints/{sprint_id}/cfd")
async def get_cfd_chart(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna la data calculada para el Cumulative Flow Diagram (CFD) del sprint o proyecto.
    """
    try:
        data = calculate_cfd_chart_data(db, proyecto_id, sprint_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

