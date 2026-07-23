import sys
import asyncio
import httpx
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.jira_sync import run_jira_sync, get_jira_auth_credentials
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, log_repo
from app.core.cache import ShortLivedCache
from app.api.v1 import deps

metrics_cache = ShortLivedCache(ttl_seconds=60)

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

router = APIRouter()

def _get_jira_module():
    return sys.modules.get('app.api.v1.endpoints.jira')

@router.get(
    "/metrics", 
    response_model=JiraMetricsResponse,
    summary="Obtener métricas rápidas con JQL"
)
async def get_jira_metrics(request: Request, db: Session = Depends(get_db)):
    mod = _get_jira_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_cache = getattr(mod, 'metrics_cache', metrics_cache) if mod else metrics_cache

    user_id = get_user_fn(request)
    user = check_user_fn(db, user_id)
    
    base_jira_url, headers = get_jira_auth_credentials(db, user)
    cache_key = f"metrics:{user.id_usuario}"
    cached_data = active_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            projects_req = client.get(f"{base_jira_url}/project", headers=headers)
            done_req = client.get(f"{base_jira_url}/search?jql=statusCategory=Done&maxResults=0", headers=headers)
            progress_req = client.get(f"{base_jira_url}/search?jql=statusCategory=\"In Progress\"&maxResults=0", headers=headers)
            bugs_req = client.get(f"{base_jira_url}/search?jql=issuetype=Bug AND priority=Highest&maxResults=0", headers=headers)
            
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
            
            active_cache.set(cache_key, result_data)
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
async def trigger_jira_sync(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    mod = _get_jira_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists

    user_id = get_user_fn(request)
    user = check_user_fn(db, user_id)
        
    background_tasks.add_task(run_jira_sync, user.id_usuario, db)
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
    mod = _get_jira_module()
    get_user_fn = getattr(mod, 'get_current_user_id', deps.get_current_user_id) if mod else deps.get_current_user_id
    check_user_fn = getattr(mod, 'check_user_exists', deps.check_user_exists) if mod else deps.check_user_exists
    active_log_repo = getattr(mod, 'log_repo', log_repo) if mod else log_repo

    user_id = get_user_fn(request)
    check_user_fn(db, user_id)
        
    logs = active_log_repo.get_recent(db, skip=offset, limit=limit)
    return logs

@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Recibir Webhooks de Jira"
)
async def jira_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    issue_data = payload.get("issue", {})
    
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
        
    calculate_and_save_kpis(db, db_project.id_proyecto)
    
    return {"status": "success", "issue": issue_key}
