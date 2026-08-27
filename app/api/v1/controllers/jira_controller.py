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

@router.get(
    "/metrics", 
    response_model=JiraMetricsResponse,
    summary="Obtener métricas rápidas con JQL"
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
    
    base_jira_url, headers = get_jira_auth_credentials(db, user)
    cache_key = f"metrics:{user.id_usuario}"
    
    # 1. Verificar si existen métricas cacheadas no expiradas
    cached_data = metrics_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 2. Consultar en paralelo mediante httpx y asyncio.gather
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
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
            
            result_data = {
                "active_projects": active_projects,
                "completed_tickets": done_data.get("total", 0),
                "in_progress_tickets": progress_data.get("total", 0),
                "critical_bugs": bugs_data.get("total", 0)
            }
            
            # Guardar en caché por 60 segundos
            metrics_cache.set(cache_key, result_data)
            return result_data
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/sync",
    response_model=SyncMessageResponse,
    summary="Ejecutar motor ETL de Sincronización"
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
    
    if log_repo.has_running_sync(db):
        if wait:
            # Esperar activamente hasta 15 segundos a que la sincronización en curso termine
            for _ in range(30):
                await asyncio.sleep(0.5)
                if not log_repo.has_running_sync(db):
                    return {"message": "Sincronización completada con éxito"}
            return {"message": "Sincronización en curso"}
        raise HTTPException(
            status_code=400,
            detail="Ya existe una sincronización en proceso de ejecución. Por favor espera a que finalice antes de iniciar una nueva."
        )
        
    if wait:
        try:
            from app.services.jira_sync_service import async_run_jira_sync
            await async_run_jira_sync(user.id_usuario, tipo_sincronizacion="AUTO_VIEW")
            return {"message": "Sincronización completada con éxito"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error durante la sincronización: {str(e)}")

    # Encolar la tarea asíncrona de sincronización
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
        
    issue_id = str(issue_data.get("id"))
    issue_key = issue_data.get("key")
    fields = issue_data.get("fields", {}) or {}
    project_data = fields.get("project", {}) or {}
    project_id = str(project_data.get("id"))
    
    db_project = project_repo.get(db, project_id)
    if not db_project:
        return {"status": "ignored", "reason": f"project {project_id} not synced"}
        
    summary = fields.get("summary", "")
    status_actual = fields.get("status", {}).get("name", "Unknown")
    
    def parse_iso(date_str):
        if not date_str:
            return None
        clean_str = date_str.replace("Z", "+00:00")
        if "+" in clean_str and len(clean_str.split("+")[-1]) == 4:
            clean_str = clean_str[:-2] + ":" + clean_str[-2:]
        try:
            return datetime.fromisoformat(clean_str)
        except ValueError:
            return None
            
    created_at = parse_iso(fields.get("created"))
    resolved_at = parse_iso(fields.get("resolutiondate"))
    
    db_issue = issue_repo.get_by_key(db, issue_key)
    
    # Extraer campos adicionales (asignado, tipo, prioridad, SP) para que el frontend pueda filtrar
    assignee_obj = fields.get("assignee") or {}
    assignee_id = assignee_obj.get("accountId") or "UNASSIGNED"
    assignee_name = assignee_obj.get("displayName") or ("Sin Asignar" if assignee_id == "UNASSIGNED" else "Usuario Jira")
    assignee_email = assignee_obj.get("emailAddress") or ""

    itype_obj = fields.get("issuetype") or {}
    issue_type = itype_obj.get("name", "Story")

    priority_obj = fields.get("priority") or {}
    priority = priority_obj.get("name", "Medium")

    sp_val = fields.get("customfield_10028") or fields.get("customfield_10016") or fields.get("customfield_10026") or fields.get("storypoints") or fields.get("customfield_10020")
    if isinstance(sp_val, (int, float)):
        story_pts = float(sp_val)
    elif isinstance(sp_val, str):
        try:
            story_pts = float(sp_val)
        except ValueError:
            story_pts = 0.0
    else:
        story_pts = 0.0

    i_data = {
        "key_ticket": issue_key,
        "id_proyecto": db_project.id_proyecto,
        "resumen": summary,
        "estado": status_actual,
        "fecha_creacion": created_at,
        "fecha_fin": resolved_at,
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "assignee_email": assignee_email,
        "issue_type": issue_type,
        "priority": priority,
        "story_points": story_pts
    }
    
    if not db_issue:
        db_issue = issue_repo.create(db, obj_in=i_data)
    else:
        db_issue = issue_repo.update(db, db_obj=db_issue, obj_in=i_data)
        
    # Recalcular métricas tras el cambio recibido por Webhook
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
    summary="Consultar transiciones disponibles de una issue en Jira Cloud"
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

@router.post(
    "/issues/{issue_key}/transitions",
    summary="Ejecutar cambio real de estado de una issue en Jira Cloud"
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
        # 1. Obtener transiciones disponibles para validar (con auto-refresh)
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
        except Exception as err:
            raise HTTPException(status_code=502, detail=f"No fue posible comunicarse con Jira. {str(err)}")
            
        available = data.get("transitions", [])
        
        target_t_id = payload.transition_id
        target_name = payload.target_status
        
        chosen_transition = None
        if target_t_id:
            chosen_transition = next((t for t in available if str(t.get("id")) == str(target_t_id)), None)
        elif target_name:
            norm_target = target_name.strip().lower()
            # Mapeo de sinónimos comunes
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
                    chosen_transition = t
                    break
        
        if not chosen_transition:
            if target_t_id:
                chosen_transition = {"id": target_t_id, "name": target_name or "Transición"}
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
        
        # 2. Ejecutar la transición en Jira Cloud
        try:
            await JiraDatasource.execute_issue_transition(client, base_jira_url, headers, issue_key, trans_id_to_exec)
        except Exception as exec_err:
            raise HTTPException(status_code=502, detail=f"Jira rechazó la transición: {str(exec_err)}")
        
        # 3. Consultar la issue en Jira para confirmar el nuevo estado
        try:
            issue_details = await JiraDatasource.fetch_issue_details(client, base_jira_url, headers, issue_key)
            updated_status = issue_details.get("fields", {}).get("status", {}).get("name", "Actualizado")
        except Exception:
            updated_status = chosen_transition.get("to", {}).get("name") or chosen_transition.get("name") or "Actualizado"
            
        # 4. Actualizar la base de datos local
        db_issue = issue_repo.get_by_key(db, issue_key)
        if db_issue:
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
                    
        return {
            "success": True,
            "issue_key": issue_key,
            "status": updated_status,
            "message": f"Estado de {issue_key} actualizado a '{updated_status}' en Jira Cloud."
        }

transition_issue = execute_issue_transition