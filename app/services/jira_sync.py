import os
import time
import traceback
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
import app.models as models
from app.core.database import SessionLocal
from app.services.kpi import calculate_and_save_kpis

async def refresh_user_token(db: Session, user: models.User, client: httpx.AsyncClient):
    token_url = "https://auth.atlassian.com/oauth/token"
    client_id = os.getenv("JIRA_CLIENT_ID", "").strip()
    client_secret = os.getenv("JIRA_CLIENT_SECRET", "").strip()
    
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": user.refresh_token
    }
    
    res = await client.post(token_url, json=data)
    if res.status_code != 200:
        raise Exception(f"No se pudo refrescar el token de Jira. Atlassian devolvió: {res.text}")
        
    tokens = res.json()
    user.access_token = tokens.get("access_token")
    if tokens.get("refresh_token"):
        user.refresh_token = tokens.get("refresh_token")
    db.commit()
    db.refresh(user)

async def jira_request(client: httpx.AsyncClient, method: str, url: str, headers: dict, db: Session, user: models.User, **kwargs):
    res = await client.request(method, url, headers=headers, **kwargs)
    if res.status_code == 401:
        await refresh_user_token(db, user, client)
        headers["Authorization"] = f"Bearer {user.access_token}"
        res = await client.request(method, url, headers=headers, **kwargs)
    return res

async def get_jira_field_mappings(client: httpx.AsyncClient, base_url: str, headers: dict, db: Session, user: models.User) -> tuple[str, str]:
    url = f"{base_url}/field"
    res = await jira_request(client, "GET", url, headers, db, user)
    if res.status_code != 200:
        raise Exception(f"Error al obtener campos de Jira: {res.text}")
        
    fields = res.json()
    sp_field = None
    sprint_field = None
    
    for f in fields:
        name = f.get("name", "").lower()
        schema = f.get("schema", {}) or {}
        custom_type = schema.get("custom", "")
        
        if custom_type == "com.pyxis.greenhopper.jira:gh-sprint" or name == "sprint":
            sprint_field = f.get("id")
            
        if (custom_type == "com.atlassian.jira.plugin.system.customfieldtypes:float" and "story point" in name) or name == "story points" or name == "story point estimate":
            sp_field = f.get("id")
            
    if not sprint_field:
        sprint_field = "customfield_10020"
    if not sp_field:
        sp_field = "customfield_10016"
        
    return sprint_field, sp_field

async def sync_projects(client: httpx.AsyncClient, base_url: str, headers: dict, db: Session, user: models.User) -> list[models.Proyecto]:
    url = f"{base_url}/project"
    res = await jira_request(client, "GET", url, headers, db, user)
    if res.status_code != 200:
        raise Exception(f"Error al obtener proyectos de Jira: {res.text}")
        
    projects_data = res.json()
    synced_projects = []
    
    for p in projects_data:
        p_id = str(p.get("id"))
        p_key = p.get("key")
        p_name = p.get("name")
        p_status = "Active"
        
        db_project = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == p_id).first()
        if not db_project:
            db_project = models.Proyecto(id_proyecto=p_id, key_proyecto=p_key, nombre=p_name, estado=p_status)
            db.add(db_project)
        else:
            db_project.key_proyecto = p_key
            db_project.nombre = p_name
            db_project.estado = p_status
            
        synced_projects.append(db_project)
        
    db.commit()
    return synced_projects

async def sync_sprints(client: httpx.AsyncClient, agile_url: str, headers: dict, db: Session, user: models.User, projects: list[models.Proyecto]) -> dict[str, list[str]]:
    board_url = f"{agile_url}/board"
    res = await jira_request(client, "GET", board_url, headers, db, user)
    if res.status_code != 200:
        print(f"Agile Board endpoint failed or not available: {res.text}")
        return {}
        
    boards = res.json().get("values", [])
    project_ids = {p.id_proyecto for p in projects}
    sprint_projects = {}
    
    for board in boards:
        board_id = board.get("id")
        board_type = board.get("type")
        location = board.get("location", {}) or {}
        p_id = str(location.get("projectId"))
        
        if board_type != "scrum":
            continue
            
        if p_id in project_ids:
            sprint_req_url = f"{agile_url}/board/{board_id}/sprint"
            sprint_res = await jira_request(client, "GET", sprint_req_url, headers, db, user)
            if sprint_res.status_code != 200:
                continue
                
            sprints_data = sprint_res.json().get("values", [])
            for s in sprints_data:
                s_id = str(s.get("id"))
                s_name = s.get("name")
                s_state = s.get("state")
                
                def parse_date(date_str):
                    if not date_str:
                        return None
                    clean_str = date_str.replace("Z", "+00:00")
                    if "+" in clean_str and len(clean_str.split("+")[-1]) == 4:
                        clean_str = clean_str[:-2] + ":" + clean_str[-2:]
                    try:
                        return datetime.fromisoformat(clean_str)
                    except ValueError:
                        return None
                        
                start_date = parse_date(s.get("startDate"))
                end_date = parse_date(s.get("endDate"))
                complete_date = parse_date(s.get("completeDate"))
                
                db_sprint = db.query(models.Sprint).filter(models.Sprint.id_sprint == s_id).first()
                if not db_sprint:
                    db_sprint = models.Sprint(
                        id_sprint=s_id,
                        id_proyecto=p_id,
                        nombre=s_name,
                        estado=s_state,
                        fecha_inicio=start_date,
                        fecha_fin=end_date,
                        fecha_finalizacion=complete_date
                    )
                    db.add(db_sprint)
                else:
                    db_sprint.id_proyecto = p_id
                    db_sprint.nombre = s_name
                    db_sprint.estado = s_state
                    db_sprint.fecha_inicio = start_date
                    db_sprint.fecha_fin = end_date
                    db_sprint.fecha_finalizacion = complete_date
                    
                if s_id not in sprint_projects:
                    sprint_projects[s_id] = []
                sprint_projects[s_id].append(p_id)
                
    db.commit()
    return sprint_projects

async def sync_issues_and_transitions(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    db: Session,
    user: models.User,
    projects: list[models.Proyecto],
    sprint_field_id: str,
    sp_field_id: str
) -> int:
    total_processed = 0
    
    for project in projects:
        start_at = 0
        max_results = 50
        
        while True:
            jql = f"project = '{project.key_proyecto}'"
            fields_to_request = f"summary,status,created,resolutiondate,key,{sprint_field_id},{sp_field_id}"
            url = f"{base_url}/search/jql?jql={jql}&expand=changelog&startAt={start_at}&maxResults={max_results}&fields={fields_to_request}"
            
            res = await jira_request(client, "GET", url, headers, db, user)
            if res.status_code != 200:
                raise Exception(f"Error al buscar issues para el proyecto {project.key_proyecto}: {res.text}")
                
            search_data = res.json()
            issues_list = search_data.get("issues", [])
            
            if not issues_list:
                break
                
            for issue_data in issues_list:
                issue_id = str(issue_data.get("id"))
                issue_key = issue_data.get("key")
                fields = issue_data.get("fields", {}) or {}
                
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
                
                story_points = fields.get(sp_field_id, 0.0)
                if story_points is None:
                    story_points = 0.0
                else:
                    try:
                        story_points = float(story_points)
                    except ValueError:
                        story_points = 0.0
                        
                sprints_raw = fields.get(sprint_field_id)
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
                        active_sprint_id = None
                        
                db_issue = db.query(models.Issue).filter(models.Issue.id_jira == issue_id).first()
                if not db_issue:
                    db_issue = models.Issue(
                        id_jira=issue_id,
                        key_issue=issue_key,
                        id_proyecto=project.id_proyecto,
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
                    db_issue.id_proyecto = project.id_proyecto
                    db_issue.id_sprint = active_sprint_id
                    db_issue.summary = summary
                    db_issue.status_actual = status_actual
                    db_issue.story_points = story_points
                    db_issue.created_at = created_at
                    db_issue.resolved_at = resolved_at
                
                # Sincronizar relación muchos a muchos
                db_issue.sprints.clear()
                for s_id in associated_sprint_ids:
                    sprint_obj = db.query(models.Sprint).filter(models.Sprint.id_sprint == s_id).first()
                    if sprint_obj:
                        db_issue.sprints.append(sprint_obj)
                        
                # Sincronizar transiciones de estado
                db.query(models.TransicionEstadoIssue).filter(models.TransicionEstadoIssue.id_jira == issue_id).delete()
                
                changelog = issue_data.get("changelog", {}) or {}
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
                            
                total_processed += 1
                
            db.commit()
            
            if len(issues_list) < max_results:
                break
            start_at += max_results
            
    return total_processed

async def run_jira_sync(user_id: int, db: Session):
    start_time = time.time()
    user = db.query(models.User).filter(models.User.id_usuario == user_id).first()
    if not user:
        print(f"Sync failed: User with ID {user_id} not found")
        return
        
    base_jira_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
    agile_jira_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/agile/1.0"
    
    headers = {
        "Authorization": f"Bearer {user.access_token}",
        "Accept": "application/json"
    }
    
    issues_processed = 0
    resultado = "SUCCESS"
    detalle_error = None
    
    async with httpx.AsyncClient() as client:
        try:
            sprint_field_id, sp_field_id = await get_jira_field_mappings(client, base_jira_url, headers, db, user)
            projects = await sync_projects(client, base_jira_url, headers, db, user)
            await sync_sprints(client, agile_jira_url, headers, db, user, projects)
            issues_processed = await sync_issues_and_transitions(
                client, base_jira_url, headers, db, user, projects, sprint_field_id, sp_field_id
            )
            
            # Calcular KPIs locales para cada proyecto sincronizado
            for p in projects:
                calculate_and_save_kpis(db, p.id_proyecto)
                
        except Exception as e:
            resultado = "ERROR"
            detalle_error = f"{str(e)}\n{traceback.format_exc()}"
            print(f"Sync error: {detalle_error}")
            
    elapsed_time = int(time.time() - start_time)
    
    log_entry = models.LogsSincronizacion(
        tipo_sincronizacion="FULL_SYNC",
        resultado=resultado,
        tiempo_ejecucion_segundos=elapsed_time,
        issues_procesados=issues_processed,
        detalle_error=detalle_error[:2000] if detalle_error else None,
        ejecutado_por=user.nombre or f"User {user.id_usuario}"
    )
    db.add(log_entry)
    db.commit()

async def run_jira_sync_task(user_id: int):
    db = SessionLocal()
    try:
        await run_jira_sync(user_id, db)
    finally:
        db.close()
