from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
import httpx

from app.core.database import get_db
from app.core.security import verify_session_id
from app.services.jira_sync import run_jira_sync_task
from app.services.kpi import calculate_and_save_kpis
import app.models as models
from pydantic import BaseModel
from typing import List, Optional

class JiraMetricsResponse(BaseModel):
    """Métricas generales obtenidas en vivo desde Jira."""
    active_projects: int
    completed_tickets: int
    in_progress_tickets: int
    critical_bugs: int

class SyncMessageResponse(BaseModel):
    """Respuesta de inicio de sincronización ETL."""
    message: str

class SyncLogResponse(BaseModel):
    """Registro de ejecución de sincronización ETL."""
    id_log: int
    id_usuario: int
    fecha_ejecucion: datetime
    resultado: str
    detalles: Optional[str] = None

    class Config:
        from_attributes = True

class WebhookResponse(BaseModel):
    """Respuesta del Webhook de Jira."""
    status: str
    reason: Optional[str] = None
    issue: Optional[str] = None

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
    user = db.query(models.User).filter(models.User.id_usuario == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

@router.get(
    "/metrics", 
    response_model=JiraMetricsResponse,
    summary="Obtener métricas rápidas con JQL",
    description="""
    Realiza 3 consultas **JQL** a Jira para obtener totales rápidos en tiempo real:
    * `statusCategory=Done`
    * `statusCategory="In Progress"`
    * `issuetype=Bug AND priority=Highest`
    """
)
async def get_jira_metrics(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = check_user_exists(db, user_id)
        
    base_jira_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
    headers = {
        "Authorization": f"Bearer {user.access_token}",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Hacemos las 4 peticiones en paralelo para mayor rapidez
            projects_req = client.get(f"{base_jira_url}/project", headers=headers)
            done_req = client.get(f"{base_jira_url}/search?jql=statusCategory=Done&maxResults=0", headers=headers)
            progress_req = client.get(f"{base_jira_url}/search?jql=statusCategory=\"In Progress\"&maxResults=0", headers=headers)
            bugs_req = client.get(f"{base_jira_url}/search?jql=issuetype=Bug AND priority=Highest&maxResults=0", headers=headers)
            
            projects_res, done_res, progress_res, bugs_res = await asyncio.gather(
                projects_req, done_req, progress_req, bugs_req
            )
            
            # Verificamos si los tokens expiraron (401).
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
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/sync",
    response_model=SyncMessageResponse,
    summary="Ejecutar motor ETL de Sincronización",
    description="""
    Arranca el proceso pesado (Background Task) para descargar toda la historia de tickets a nuestra base de datos PostgreSQL.
    * **JQL Principal:** `project='{LLAVE_DEL_PROYECTO}'`
    * Utiliza el parámetro `expand=changelog` para traer el historial minuto a minuto de cada ticket.
    """
)
async def trigger_jira_sync(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = check_user_exists(db, user_id)
        
    background_tasks.add_task(run_jira_sync_task, user.id_usuario)
    return {"message": "Sincronización iniciada en segundo plano"}

@router.get(
    "/sync/logs",
    response_model=List[SyncLogResponse],
    summary="Obtener historial de Sincronizaciones (Auditoría ETL)",
    description="Lee la tabla local de PostgreSQL para retornar el estado de las últimas tareas de sincronización (RUNNING, SUCCESS, FAILED)."
)
async def get_sync_logs(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    logs = db.query(models.LogsSincronizacion).order_by(models.LogsSincronizacion.fecha_ejecucion.desc()).limit(20).all()
    return logs

@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Recibir Webhooks de Jira",
    description="Endpoint pasivo que espera a que Jira le envíe un Payload JSON cada vez que se crea, edita o mueve un ticket. Actualiza los KPIs en tiempo real."
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
    
    db_project = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == project_id).first()
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
    
    story_points = 0.0
    sprints_raw = None
    
    for key, value in fields.items():
        if key.startswith("customfield_"):
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict) and "sprint" in str(value[0].get("self", "")).lower():
                sprints_raw = value
            elif isinstance(value, dict) and "sprint" in str(value.get("self", "")).lower():
                sprints_raw = value
            elif isinstance(value, (int, float)):
                story_points = float(value)
                
    active_sprint_id = None
    associated_sprint_ids = []
    
    if isinstance(sprints_raw, list):
        for s_raw in sprints_raw:
            if isinstance(s_raw, dict):
                s_id = str(s_raw.get("id"))
                associated_sprint_ids.append(s_id)
                if s_raw.get("state") == "active":
                    active_sprint_id = s_id
        if not active_sprint_id and associated_sprint_ids:
            active_sprint_id = associated_sprint_ids[-1]
    elif isinstance(sprints_raw, dict):
        active_sprint_id = str(sprints_raw.get("id"))
        associated_sprint_ids.append(active_sprint_id)
        
    if active_sprint_id:
        sprint_exists = db.query(models.Sprint).filter(models.Sprint.id_sprint == active_sprint_id).first()
        if not sprint_exists:
            sprint_exists = models.Sprint(
                id_sprint=active_sprint_id,
                id_proyecto=project_id,
                nombre=sprints_raw.get("name") if isinstance(sprints_raw, dict) else "Sprint Sincronizado",
                estado=sprints_raw.get("state") if isinstance(sprints_raw, dict) else "active"
            )
            db.add(sprint_exists)
            
    db_issue = db.query(models.Issue).filter(models.Issue.id_jira == issue_id).first()
    if not db_issue:
        db_issue = models.Issue(
            id_jira=issue_id,
            key_issue=issue_key,
            id_proyecto=project_id,
            id_sprint=active_sprint_id,
            summary=summary,
            status_actual=status_actual,
            story_points=story_points,
            created_at=created_at,
            resolved_at=resolved_at
        )
        db.add(db_issue)
    else:
        db_issue.key_issue = issue_key
        db_issue.id_sprint = active_sprint_id
        db_issue.summary = summary
        db_issue.status_actual = status_actual
        if story_points > 0:
            db_issue.story_points = story_points
        db_issue.created_at = created_at
        db_issue.resolved_at = resolved_at
        
    db_issue.sprints.clear()
    for s_id in associated_sprint_ids:
        sprint_obj = db.query(models.Sprint).filter(models.Sprint.id_sprint == s_id).first()
        if sprint_obj:
            db_issue.sprints.append(sprint_obj)
            
    db.query(models.TransicionEstadoIssue).filter(models.TransicionEstadoIssue.id_jira == issue_id).delete()
    
    changelog = payload.get("changelog", {}) or {}
    histories = changelog.get("histories", []) or []
    
    for history in histories:
        history_date = parse_iso(history.get("created"))
        items = history.get("items", []) or []
        for item in items:
            if item.get("field") == "status":
                estado_anterior = item.get("fromString")
                estado_nuevo = item.get("toString")
                
                db_transition = models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior=estado_anterior,
                    estado_nuevo=estado_nuevo,
                    fecha_cambio=history_date
                )
                db.add(db_transition)
                
    db.commit()
    
    calculate_and_save_kpis(db, project_id)
    
    return {"status": "success", "issue": issue_key}
