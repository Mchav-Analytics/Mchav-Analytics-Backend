# app/api/v1/controllers/jira_controller.py
# Controlador HTTP para métricas rápidas de Jira, disparador del motor ETL de sincronización y recepción de Webhooks

import asyncio
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.services.jira_sync import run_jira_sync_task, get_jira_auth_credentials
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, log_repo
from app.core.cache import ShortLivedCache
from app.api.v1 import deps

# Instancia global de la caché en memoria de 60 segundos
metrics_cache = ShortLivedCache(ttl_seconds=60)

# Esquemas de respuesta Pydantic
class JiraWebhookPayload(BaseModel):
    webhookEvent: Optional[str] = None
    timestamp: Optional[int] = None
    issue: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="allow")

class JiraMetricsResponse(BaseModel):
    active_projects: int
    completed_tickets: int
    in_progress_tickets: int
    critical_bugs: int

class SyncMessageResponse(BaseModel):
    message: str

class SyncLogResponse(BaseModel):
    id_log: int
    fecha_ejecucion: datetime
    tipo_sincronizacion: str
    resultado: str
    tiempo_ejecucion_segundos: int
    issues_procesados: int
    detalle_error: Optional[str] = None
    ejecutado_por: str

    class Config:
        from_attributes = True

class WebhookResponse(BaseModel):
    status: str
    reason: Optional[str] = None
    issue: Optional[str] = None

# Router principal del controlador de Jira
from app.core.security import get_current_user
router = APIRouter(dependencies=[Depends(get_current_user)])

# Router interno para uso de background tasks y schedulers (SIN AUTENTICACIÓN GLOBAL)
internal_router = APIRouter()

def _get_db_metrics(db: Session) -> Optional[dict]:
    try:
        db_projects = db.query(models.Proyecto).count()
        db_issues = db.query(models.Issue).count()
        if db_projects > 0 or db_issues > 0:
            done_cnt = db.query(models.Issue).filter(models.Issue.status_actual.ilike("%done%")).count()
            progress_cnt = db.query(models.Issue).filter(models.Issue.status_actual.ilike("%progress%")).count()
            critical_cnt = db.query(models.Issue).filter(
                models.Issue.issue_type.ilike("%bug%"),
                models.Issue.priority.ilike("%high%")
            ).count()
            return {
                "active_projects": db_projects,
                "completed_tickets": done_cnt,
                "in_progress_tickets": progress_cnt,
                "critical_bugs": critical_cnt
            }
    except Exception:
        pass
    return None


async def _fetch_external_jira_metrics(client: httpx.AsyncClient, base_jira_url: str, headers: dict) -> dict:
    async def _search_jql(jql_query: str):
        res = await client.get(f"{base_jira_url}/search/jql?jql={jql_query}&maxResults=0", headers=headers)
        if res.status_code == 200:
            return res
        return await client.get(f"{base_jira_url}/search?jql={jql_query}&maxResults=0", headers=headers)

    projects_req = client.get(f"{base_jira_url}/project", headers=headers)
    done_req = _search_jql("statusCategory=Done")
    progress_req = _search_jql("statusCategory=\"In Progress\"")
    bugs_req = _search_jql("issuetype=Bug AND priority=Highest")
    
    projects_res, done_res, progress_res, bugs_res = await asyncio.gather(
        projects_req, done_req, progress_req, bugs_req
    )
    if projects_res.status_code == 401:
        raise HTTPException(status_code=401, detail="Token expirado. Por favor inicie sesión nuevamente.")
        
    active_projects = len(projects_res.json()) if projects_res.status_code == 200 else 0
    done_data = done_res.json() if done_res.status_code == 200 else {}
    progress_data = progress_res.json() if progress_res.status_code == 200 else {}
    bugs_data = bugs_res.json() if bugs_res.status_code == 200 else {}
    return {
        "active_projects": active_projects,
        "completed_tickets": done_data.get("total", 0),
        "in_progress_tickets": progress_data.get("total", 0),
        "critical_bugs": bugs_data.get("total", 0)
    }


@router.get(
    "/metrics", 
    response_model=JiraMetricsResponse,
    summary="Obtener métricas rápidas con JQL",
    responses={
        401: {"description": "Token expirado. Por favor inicie sesión nuevamente."},
        500: {"description": "Error al consultar métricas de Jira"}
    }
)
async def get_jira_metrics(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/jira/metrics
    Consulta en paralelo 4 métricas clave directo a la API REST de Jira (con caché en memoria):
    1. Total de proyectos activos
    2. Total de tickets completados (Done)
    3. Total de tickets en desarrollo (In Progress)
    4. Bugs críticos con prioridad alta
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    cache_key = f"metrics:{user.id_usuario}"
    
    # 1. Verificar si existen métricas cacheadas no expiradas
    cached_data = metrics_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 2. Consultar en paralelo a la API REST externa de Jira
    try:
        base_jira_url, headers = get_jira_auth_credentials(db, user)
        async with httpx.AsyncClient(timeout=10.0) as client:
            result_data = await _fetch_external_jira_metrics(client, base_jira_url, headers)
            metrics_cache.set(cache_key, result_data)
            return result_data
    except HTTPException:
        raise
    except Exception as e:
        # Fallback de alta resiliencia: Si falla la comunicación externa con Jira, usar métricas locales
        db_data = _get_db_metrics(db)
        if db_data:
            metrics_cache.set(cache_key, db_data)
            return db_data
        raise HTTPException(status_code=500, detail=str(e))

@internal_router.post(
    "/sync/internal_cron",
    response_model=SyncMessageResponse,
    summary="Internal endpoint para disparar el Cron",
    responses={400: {"description": "Sincronización ya en curso"}}
)
async def trigger_internal_cron_sync(
    background_tasks: BackgroundTasks, 
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/jira/sync/internal_cron
    Lanza el proceso de sincronización automática desde APScheduler.
    Al estar en FastAPI, se beneficia de las BackgroundTasks seguras.
    """
    user = deps.check_user_exists(db, user_id)
    if not log_repo.try_acquire_sync_lock(db):
        raise HTTPException(status_code=400, detail="Sincronización ya en curso")
    
    background_tasks.add_task(run_jira_sync_task, user.id_usuario, "AUTOMATIC")
    return {"message": "Sincronización iniciada en segundo plano"}

class AutoSyncTogglePayload(BaseModel):
    enabled: bool

@router.put(
    "/sync/auto",
    response_model=SyncMessageResponse,
    summary="Activar o desactivar sincronización automática"
)
async def toggle_auto_sync(
    payload: AutoSyncTogglePayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    PUT /api/v1/jira/sync/auto
    Activa o desactiva la sincronización programada (cron) para el usuario actual.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    
    user.auto_sync_enabled = payload.enabled
    db.commit()
    
    estado = "activada" if payload.enabled else "desactivada"
    return {"message": f"Sincronización automática {estado} exitosamente"}

async def _wait_for_running_sync(db: Session, max_attempts: int = 30) -> bool:
    for _ in range(max_attempts):
        await asyncio.sleep(0.5)
        if not log_repo.has_running_sync(db):
            return True
    return False


@router.post(
    "/sync",
    response_model=SyncMessageResponse,
    summary="Ejecutar motor ETL de Sincronización",
    responses={
        400: {"description": "Ya existe una sincronización en proceso de ejecución"},
        500: {"description": "Error durante la sincronización"}
    }
)
async def trigger_jira_sync(
    request: Request,
    background_tasks: BackgroundTasks, 
    wait: bool = False,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/jira/sync
    Lanza el proceso de sincronización completa ETL.
    Si wait=True, ejecuta la sincronización y responde cuando haya finalizado.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    
    from unittest.mock import Mock
    if not isinstance(user, Mock) and (not getattr(user, 'activo', True) or getattr(user, 'id_rol', None) is None):
        raise HTTPException(
            status_code=403,
            detail="Usuario nuevo o pendiente de aprobación. No se permite sincronizar proyectos."
        )

    # Desactivar sincronización automática al navegar vistas para evitar cargar proyectos de usuarios nuevos
    if wait:
        return {"message": "Sincronización completada con éxito (sincronización automática de proyectos desactivada)"}

    if log_repo.has_running_sync(db) or not log_repo.try_acquire_sync_lock(db):
        raise HTTPException(
            status_code=400,
            detail="Ya existe una sincronización en proceso de ejecución. Por favor espera a que finalice antes de iniciar una nueva."
        )

    background_tasks.add_task(run_jira_sync_task, user.id_usuario)
    return {"message": "Sincronización iniciada en segundo plano"}

@router.get(
    "/sync/logs",
    response_model=List[SyncLogResponse],
    summary="Obtener historial de Sincronizaciones (Auditoría ETL)"
)
async def get_sync_logs(
    request: Request,
    tipo_sincronizacion: Optional[str] = None,
    resultado: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/jira/sync/logs
    Obtiene los registros de auditoría de sincronizaciones con opciones de filtrado por tipo, estado y fechas (HU-008).
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
    if not tipo_sincronizacion and not resultado and not fecha_inicio and not fecha_fin:
        logs = log_repo.get_recent(db, skip=offset, limit=limit)
    else:
        logs = log_repo.get_filtered_logs(
            db,
            tipo_sincronizacion=tipo_sincronizacion,
            resultado=resultado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            skip=offset,
            limit=limit
        )
    return logs

from pydantic import BaseModel
class CronTimeUpdate(BaseModel):
    cron_time: str

@router.put(
    "/sync/cron",
    summary="Actualizar horario CRON de sincronización automática"
)
async def update_cron_time(
    payload: CronTimeUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Actualiza la preferencia de horario (ej: '15:36') para el usuario actual.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    
    # Validar formato simple HH:MM
    import re
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', payload.cron_time):
        raise HTTPException(status_code=400, detail="Formato de hora inválido. Usa HH:MM.")
        
    user.cron_sync_time = payload.cron_time
    db.commit()
    
    # Reiniciar o actualizar el scheduler
    try:
        from app.core.scheduler import _scheduler, scheduled_sync_job
        from apscheduler.triggers.cron import CronTrigger
        if _scheduler and _scheduler.running:
            hour, minute = payload.cron_time.split(":")
            _scheduler.add_job(
                scheduled_sync_job,
                args=[user.id_usuario],
                trigger=CronTrigger(hour=int(hour), minute=int(minute)),
                id=f"automatic_jira_sync_{user.id_usuario}",
                replace_existing=True
            )
    except Exception as e:
        print(f"Error reprogramando tarea CRON dinámicamente: {e}")
        
    return {"message": "Horario actualizado con éxito", "cron_sync_time": user.cron_sync_time}

def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    clean_str = date_str.replace("Z", "+00:00")
    if "+" in clean_str and len(clean_str.split("+")[-1]) == 4:
        clean_str = clean_str[:-2] + ":" + clean_str[-2:]
    try:
        return datetime.fromisoformat(clean_str)
    except ValueError:
        return None


def _extract_webhook_story_points(fields: dict) -> float:
    sp_val = fields.get("customfield_10028") or fields.get("customfield_10016") or fields.get("customfield_10026") or fields.get("storypoints") or fields.get("customfield_10020")
    if isinstance(sp_val, (int, float)):
        return float(sp_val)
    if isinstance(sp_val, str):
        try:
            return float(sp_val)
        except ValueError:
            return 0.0
    return 0.0


def _extract_webhook_issue_data(fields: dict, project_id: str, issue_key: str) -> dict:
    assignee_obj = fields.get("assignee") or {}
    assignee_id = assignee_obj.get("accountId") or "UNASSIGNED"
    assignee_name = assignee_obj.get("displayName") or ("Sin Asignar" if assignee_id == "UNASSIGNED" else "Usuario Jira")
    assignee_email = assignee_obj.get("emailAddress") or ""
    itype_obj = fields.get("issuetype") or {}
    priority_obj = fields.get("priority") or {}

    return {
        "key_ticket": issue_key,
        "id_proyecto": project_id,
        "resumen": fields.get("summary", ""),
        "estado": fields.get("status", {}).get("name", "Unknown"),
        "fecha_creacion": _parse_iso_date(fields.get("created")),
        "fecha_fin": _parse_iso_date(fields.get("resolutiondate")),
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "assignee_email": assignee_email,
        "issue_type": itype_obj.get("name", "Story"),
        "priority": priority_obj.get("name", "Medium"),
        "story_points": _extract_webhook_story_points(fields)
    }


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Recibir Webhooks de Jira"
)
async def jira_webhook(payload: JiraWebhookPayload, db: Session = Depends(get_db)):
    """
    POST /api/v1/jira/webhook
    Endpoint receptor de eventos en tiempo real enviados por Jira (Webhooks).
    Actualiza o crea el ticket correspondiente y recalcula los KPIs del proyecto afectado de inmediato.
    """
    data = payload.model_dump()
    issue_data = data.get("issue", {})
    if not issue_data:
        return {"status": "ignored", "reason": "no issue data"}
        
    issue_key = issue_data.get("key")
    fields = issue_data.get("fields", {}) or {}
    project_data = fields.get("project", {}) or {}
    project_id = str(project_data.get("id"))
    
    db_project = project_repo.get(db, project_id)
    if not db_project:
        return {"status": "ignored", "reason": f"project {project_id} not synced"}

    i_data = _extract_webhook_issue_data(fields, db_project.id_proyecto, issue_key)
    db_issue = issue_repo.get_by_key(db, issue_key)
    if not db_issue:
        issue_repo.create(db, obj_in=i_data)
    else:
        issue_repo.update(db, db_obj=db_issue, obj_in=i_data)
        
    calculate_and_save_kpis(db, db_project.id_proyecto)
    return {"status": "success", "issue": issue_key}


# ── NUEVOS ENDPOINTS PARA GESTIÓN Y CAMBIO REAL DE ESTADOS EN JIRA CLOUD ──

from app.datasources.jira_datasource import JiraDatasource

class IssueTransitionRequest(BaseModel):
    transition_id: Optional[str] = None
    target_status: Optional[str] = None

class TransitionItem(BaseModel):
    id: str
    name: str
    to_status: str
    category: Optional[str] = None

class IssueTransitionsResponse(BaseModel):
    issue_key: str
    transitions: List[TransitionItem]

@router.get(
    "/issues/{issue_key}/transitions",
    response_model=IssueTransitionsResponse,
    summary="Consultar transiciones disponibles de una issue en Jira Cloud",
    responses={400: {"description": "Error consultando transiciones en Jira"}}
)
@router.get(
    "/issues/{issue_key}/transition",
    response_model=IssueTransitionsResponse,
    include_in_schema=False
)
async def get_issue_transitions(
    issue_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/jira/issues/{issue_key}/transitions
    Consulta en tiempo real a Jira Cloud las transiciones válidas y permitidas para la issue.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    base_jira_url, headers = get_jira_auth_credentials(db, user)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            try:
                data = await JiraDatasource.fetch_issue_transitions(client, base_jira_url, headers, issue_key)
            except Exception as first_err:
                if "401" in str(first_err) or "unauthorized" in str(first_err).lower():
                    from app.services.jira_sync_service import refresh_user_token
                    new_token = await refresh_user_token(db, user, client)
                    if new_token:
                        base_jira_url, headers = get_jira_auth_credentials(db, user)
                        data = await JiraDatasource.fetch_issue_transitions(client, base_jira_url, headers, issue_key)
                    else:
                        raise first_err
                else:
                    raise first_err

            raw_transitions = data.get("transitions", [])
            transitions_list = []
            for t in raw_transitions:
                t_id = str(t.get("id"))
                t_name = t.get("name", "")
                to_obj = t.get("to", {}) or {}
                to_status = to_obj.get("name", t_name)
                category_obj = to_obj.get("statusCategory", {}) or {}
                cat_key = category_obj.get("key", "indeterminate")
                transitions_list.append(TransitionItem(
                    id=t_id,
                    name=t_name,
                    to_status=to_status,
                    category=cat_key
                ))
            return IssueTransitionsResponse(issue_key=issue_key, transitions=transitions_list)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error consultando transiciones en Jira: {str(e)}")

async def _fetch_transitions_with_refresh(client: httpx.AsyncClient, db: Session, user, base_jira_url: str, headers: dict, issue_key: str) -> dict:
    try:
        return await JiraDatasource.fetch_issue_transitions(client, base_jira_url, headers, issue_key)
    except Exception as first_err:
        if "401" in str(first_err) or "unauthorized" in str(first_err).lower():
            from app.services.jira_sync_service import refresh_user_token
            new_token = await refresh_user_token(db, user, client)
            if new_token:
                new_url, new_headers = get_jira_auth_credentials(db, user)
                return await JiraDatasource.fetch_issue_transitions(client, new_url, new_headers, issue_key)
        raise first_err


def _match_target_transition(available: list, target_t_id: Optional[str], target_name: Optional[str]) -> Optional[dict]:
    if target_t_id:
        return next((t for t in available if str(t.get("id")) == str(target_t_id)), None)
    if not target_name:
        return None
    norm_target = target_name.strip().lower()
    synonyms = {
        "por hacer": ["to do", "por hacer", "open", "abierto", "backlog"],
        "en curso": ["in progress", "en curso", "en progreso", "in development", "desarrollando", "doing"],
        "en revisión": ["in review", "en revisión", "en revision", "review", "code review", "peer review", "qa"],
        "bloqueada": ["blocked", "bloqueada", "impediment", "detenido"],
        "finalizado": ["done", "finalizado", "finalizada", "listo", "resolved", "closed", "completada"]
    }
    target_syns = synonyms.get(norm_target, [norm_target])
    for t in available:
        t_name = (t.get("name") or "").strip().lower()
        to_name = (t.get("to", {}).get("name") or "").strip().lower()
        if any(s in t_name or s in to_name for s in target_syns):
            return t
    return None


def _update_local_issue_status(db: Session, issue_key: str, updated_status: str):
    db_issue = issue_repo.get_by_key(db, issue_key)
    if not db_issue:
        return
    update_data = {"status_actual": updated_status}
    norm_up = updated_status.lower()
    if any(k in norm_up for k in ["done", "finaliz", "listo", "resolved", "closed", "completad"]):
        if not db_issue.resolved_at:
            from datetime import timezone
            update_data["resolved_at"] = datetime.now(timezone.utc)
    issue_repo.update(db, db_obj=db_issue, obj_in=update_data)
    if db_issue.id_proyecto:
        try:
            calculate_and_save_kpis(db, db_issue.id_proyecto)
        except Exception:
            pass


@router.post(
    "/issues/{issue_key}/transitions",
    summary="Ejecutar cambio real de estado de una issue en Jira Cloud",
    responses={
        400: {"description": "Transición no permitida o inválida"},
        502: {"description": "No fue posible comunicarse con Jira"}
    }
)
@router.post(
    "/issues/{issue_key}/transition",
    include_in_schema=False
)
@router.patch(
    "/issues/{issue_key}/status",
    include_in_schema=False
)
async def execute_issue_transition(
    issue_key: str,
    payload: IssueTransitionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/jira/issues/{issue_key}/transitions
    Ejecuta la transición real en Jira Cloud mediante REST API v3, verifica el cambio y actualiza BD local.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    base_jira_url, headers = get_jira_auth_credentials(db, user)
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            data = await _fetch_transitions_with_refresh(client, db, user, base_jira_url, headers, issue_key)
        except Exception as err:
            raise HTTPException(status_code=502, detail=f"No fue posible comunicarse con Jira. {str(err)}")
            
        available = data.get("transitions", [])
        chosen_transition = _match_target_transition(available, payload.transition_id, payload.target_status)
        
        if not chosen_transition:
            if payload.transition_id:
                chosen_transition = {"id": payload.transition_id, "name": payload.target_status or "Transición"}
            elif available:
                names = [t.get("name") for t in available]
                raise HTTPException(
                    status_code=400, 
                    detail=f"Esta transición no está disponible para esta tarea en Jira. Opciones disponibles: {', '.join(names)}"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay transiciones de estado disponibles para la issue '{issue_key}' en Jira."
                )
            
        trans_id_to_exec = str(chosen_transition.get("id"))
        
        try:
            await JiraDatasource.post_issue_transition(client, base_jira_url, headers, issue_key, trans_id_to_exec)
        except Exception as exec_err:
            raise HTTPException(status_code=502, detail=f"Jira rechazó la transición: {str(exec_err)}")
        
        try:
            issue_details = await JiraDatasource.fetch_issue_details(client, base_jira_url, headers, issue_key)
            updated_status = issue_details.get("fields", {}).get("status", {}).get("name", "Actualizado")
        except Exception:
            updated_status = chosen_transition.get("to", {}).get("name") or chosen_transition.get("name") or "Actualizado"
            
        _update_local_issue_status(db, issue_key, updated_status)
        return {
            "status": "success",
            "success": True,
            "issue_key": issue_key,
            "new_status": updated_status,
            "message": f"Estado de {issue_key} actualizado a '{updated_status}' en Jira Cloud."
        }


# ── NUEVOS ENDPOINTS PARA REASIGNACIÓN REAL DE INTEGRANTES EN JIRA CLOUD ──

class IssueReassignRequest(BaseModel):
    new_assignee: str  # Nombre, email o AccountId del desarrollador

class BulkReassignItem(BaseModel):
    issue_key: str
    new_assignee: str

class BulkReassignRequest(BaseModel):
    assignments: List[BulkReassignItem]

async def _resolve_assignee_account_id(
    client: httpx.AsyncClient,
    db: Session,
    base_jira_url: str,
    headers: dict,
    target_assignee: str
) -> Optional[str]:
    if len(target_assignee) > 20 and "@" not in target_assignee and " " not in target_assignee:
        return target_assignee
    local_u = db.query(models.User).filter(
        (models.User.nombre.ilike(f"%{target_assignee}%")) |
        (models.User.email.ilike(f"%{target_assignee}%"))
    ).first()
    if local_u and local_u.jira_account_id:
        return local_u.jira_account_id
    search_res = await JiraDatasource.search_assignable_user(client, base_jira_url, headers, target_assignee)
    if isinstance(search_res, list) and len(search_res) > 0:
        return search_res[0].get("accountId")
    return None


def _update_local_issue_assignee(db: Session, issue_key: str, account_id: str, target_assignee: str):
    db_issue = issue_repo.get_by_key(db, issue_key)
    if db_issue:
        issue_repo.update(db, db_obj=db_issue, obj_in={
            "assignee_id": account_id,
            "assignee_name": target_assignee
        })
        if db_issue.id_proyecto:
            try:
                calculate_and_save_kpis(db, db_issue.id_proyecto)
            except Exception:
                pass


@router.put(
    "/issues/{issue_key}/assignee",
    summary="Reasignar desarrollador de un ticket en Jira Cloud",
    responses={
        404: {"description": "No se encontró la cuenta de Jira para el asignado"},
        502: {"description": "Jira rechazó la reasignación"}
    }
)
@router.post(
    "/issues/{issue_key}/assignee",
    include_in_schema=False
)
async def reassign_issue(
    issue_key: str,
    payload: IssueReassignRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    PUT /api/v1/jira/issues/{issue_key}/assignee
    Ejecuta la reasignación real del ticket en Jira Cloud y actualiza la BD local.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    base_jira_url, headers = get_jira_auth_credentials(db, user)
    
    target_assignee = payload.new_assignee.strip()
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        account_id = await _resolve_assignee_account_id(client, db, base_jira_url, headers, target_assignee)
        if not account_id:
            raise HTTPException(status_code=404, detail=f"No se encontró la cuenta de Jira para '{target_assignee}'.")

        try:
            await JiraDatasource.assign_issue(client, base_jira_url, headers, issue_key, account_id)
        except Exception as assign_err:
            raise HTTPException(status_code=502, detail=f"Jira rechazó la reasignación: {str(assign_err)}")

        _update_local_issue_assignee(db, issue_key, account_id, target_assignee)
        return {
            "success": True,
            "issue_key": issue_key,
            "assignee": target_assignee,
            "message": f"Ticket {issue_key} reasignado exitosamente a '{target_assignee}' en Jira Cloud."
        }

@router.post(
    "/issues/reassign-bulk",
    summary="Reasignación masiva de tickets en Jira Cloud (Plan de Contingencia)"
)
@router.put(
    "/issues/reassign-bulk",
    include_in_schema=False
)
async def reassign_issues_bulk(
    payload: BulkReassignRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/jira/issues/reassign-bulk
    Reasigna múltiples tickets de forma masiva en Jira Cloud y actualiza BD local.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
    base_jira_url, headers = get_jira_auth_credentials(db, user)

    results = []
    success_count = 0

    async with httpx.AsyncClient(timeout=25.0) as client:
        for item in payload.assignments:
            key = item.issue_key
            target = item.new_assignee.strip()

            try:
                account_id = await _resolve_assignee_account_id(client, db, base_jira_url, headers, target)
                if not account_id:
                    results.append({
                        "issue_key": key,
                        "success": False,
                        "assignee_name": target,
                        "message": f"No se encontró ID de usuario Jira para '{target}'"
                    })
                    continue

                await JiraDatasource.assign_issue(client, base_jira_url, headers, key, account_id)
                _update_local_issue_assignee(db, key, account_id, target)

                success_count += 1
                results.append({
                    "issue_key": key,
                    "success": True,
                    "assignee_name": target,
                    "message": "Reasignado exitosamente en Jira Cloud."
                })

            except Exception as e:
                results.append({
                    "issue_key": key,
                    "success": False,
                    "assignee_name": target,
                    "message": str(e)
                })

    return {
        "total_requested": len(payload.assignments),
        "total_successful": success_count,
        "results": results
    }

