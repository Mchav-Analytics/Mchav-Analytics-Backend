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
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/jira/sync
    Lanza el proceso de sincronización completa ETL como una tarea en segundo plano (BackgroundTask) no bloqueante.
    """
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)
        
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
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/jira/sync/logs
    Obtiene los registros de auditoría de sincronizaciones anteriores con paginación.
    """
    user_id = deps.get_current_user_id(request)
    deps.check_user_exists(db, user_id)
        
    logs = log_repo.get_recent(db, skip=offset, limit=limit)
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
    i_data = {
        "key_ticket": issue_key,
        "id_proyecto": db_project.id_proyecto,
        "resumen": summary,
        "estado": status_actual,
        "fecha_creacion": created_at,
        "fecha_fin": resolved_at
    }
    
    if not db_issue:
        db_issue = issue_repo.create(db, obj_in=i_data)
    else:
        db_issue = issue_repo.update(db, db_obj=db_issue, obj_in=i_data)
        
    # Recalcular métricas tras el cambio recibido por Webhook
    calculate_and_save_kpis(db, db_project.id_proyecto)
    
    return {"status": "success", "issue": issue_key}