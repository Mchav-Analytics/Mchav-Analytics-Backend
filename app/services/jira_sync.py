import os
import time
import traceback
import httpx
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
import app.models as models
from app.core.database import SessionLocal
from app.services.kpi import calculate_and_save_kpis
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, log_repo

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
    user_repo.update(db, db_obj=user, obj_in={
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token") or user.refresh_token
    })

async def jira_request(client: httpx.AsyncClient, method: str, url: str, headers: dict, db: Session, user: models.User, **kwargs):
    max_retries = 3
    retry_delay = 15.0  # Incrementamos la base a 15 segundos para dar suficiente margen de recuperación
    for attempt in range(max_retries + 1):
        res = await client.request(method, url, headers=headers, **kwargs)
        
        # 1. Si es 401, refrescar token e intentar de nuevo una vez
        if res.status_code == 401:
            await refresh_user_token(db, user, client)
            headers["Authorization"] = f"Bearer {user.access_token}"
            res = await client.request(method, url, headers=headers, **kwargs)
            return res
            
        # 2. Si es 429 (Rate Limit), esperar e intentar de nuevo con backoff
        if res.status_code == 429 and attempt < max_retries:
            retry_after = res.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else retry_delay * (1.5 ** attempt)
            except ValueError:
                delay = retry_delay * (1.5 ** attempt)
            
            # Si el tiempo de espera sugerido es demasiado alto (más de 60 segundos), abortamos la petición
            if delay > 60.0:
                print(f"[Rate Limit] Atlassian sugirió una espera muy larga ({delay}s). Abortando petición de inmediato.")
                return res
            
            print(f"[Rate Limit] Atlassian nos limitó el flujo (429). Reintentando en {delay} segundos (Intento {attempt + 1}/{max_retries})...")
            await asyncio.sleep(delay)
            continue
            
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
        
        db_project = project_repo.get(db, p_id)
        
        p_data = {
            "id_proyecto": p_id,
            "key_proyecto": p_key,
            "nombre": p_name,
            "estado": p_status
        }
        
        if not db_project:
            db_project = project_repo.create(db, obj_in=p_data)
        else:
            db_project = project_repo.update(db, db_obj=db_project, obj_in=p_data)
            
        synced_projects.append(db_project)
        
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
                
                db_sprint = sprint_repo.get(db, s_id)
                s_data = {
                    "id_sprint": s_id,
                    "id_proyecto": p_id,
                    "nombre": s_name,
                    "estado": s_state,
                    "fecha_inicio": start_date,
                    "fecha_fin": end_date,
                    "fecha_finalizacion": complete_date
                }
                
                if not db_sprint:
                    sprint_repo.create(db, obj_in=s_data)
                else:
                    sprint_repo.update(db, db_obj=db_sprint, obj_in=s_data)
                    
                if s_id not in sprint_projects:
                    sprint_projects[s_id] = []
                sprint_projects[s_id].append(p_id)
                
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
        page_token = None
        max_results = 50
        
        while True:
            jql = f"project = '{project.key_proyecto}'"
            fields_to_request = f"summary,status,created,resolutiondate,key,{sprint_field_id},{sp_field_id}"
            token_param = f"&nextPageToken={page_token}" if page_token else ""
            url = f"{base_url}/search/jql?jql={jql}&expand=changelog&maxResults={max_results}&fields={fields_to_request}{token_param}"
            
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
                            # Si el sprint no existe en la base de datos, lo creamos dinámicamente con los datos devueltos en el issue
                            sprint_exists = sprint_repo.get(db, s_id)
                            if not sprint_exists:
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
                                        
                                sprint_repo.create(db, obj_in={
                                    "id_sprint": s_id,
                                    "id_proyecto": project.id_proyecto,
                                    "nombre": s_raw.get("name") or f"Sprint {s_id}",
                                    "estado": s_raw.get("state") or "closed",
                                    "fecha_inicio": parse_date(s_raw.get("startDate")),
                                    "fecha_fin": parse_date(s_raw.get("endDate")),
                                    "fecha_finalizacion": parse_date(s_raw.get("completeDate"))
                                })
                            associated_sprint_ids.append(s_id)
                            if s_raw.get("state") == "active":
                                active_sprint_id = s_id
                    if not active_sprint_id and associated_sprint_ids:
                        active_sprint_id = associated_sprint_ids[-1]
                elif isinstance(sprints_raw, dict):
                    s_id = str(sprints_raw.get("id"))
                    sprint_exists = sprint_repo.get(db, s_id)
                    if not sprint_exists:
                        sprint_repo.create(db, obj_in={
                            "id_sprint": s_id,
                            "id_proyecto": project.id_proyecto,
                            "nombre": sprints_raw.get("name") or f"Sprint {s_id}",
                            "estado": sprints_raw.get("state") or "closed",
                            "fecha_inicio": None,
                            "fecha_fin": None,
                            "fecha_finalizacion": None
                        })
                    active_sprint_id = s_id
                    associated_sprint_ids.append(active_sprint_id)
                
                if active_sprint_id:
                    sprint_exists = sprint_repo.get(db, active_sprint_id)
                    if not sprint_exists:
                        active_sprint_id = None
                        
                db_issue = issue_repo.get(db, issue_id)
                
                i_data = {
                    "id_jira": issue_id,
                    "key_issue": issue_key,
                    "id_proyecto": project.id_proyecto,
                    "id_sprint": active_sprint_id,
                    "summary": summary,
                    "status_actual": status_actual,
                    "story_points": story_points,
                    "created_at": created_at,
                    "resolved_at": resolved_at
                }
                
                if not db_issue:
                    db_issue = issue_repo.create(db, obj_in=i_data)
                else:
                    db_issue = issue_repo.update(db, db_obj=db_issue, obj_in=i_data)
                
                # Sincronizar relación muchos a muchos
                db_issue.sprints.clear()
                for s_id in associated_sprint_ids:
                    sprint_obj = sprint_repo.get(db, s_id)
                    if sprint_obj:
                        db_issue.sprints.append(sprint_obj)
                db.commit() # commit relations
                        
                # Sincronizar transiciones de estado
                transition_repo.delete_by_issue(db, issue_id)
                
                changelog = issue_data.get("changelog", {}) or {}
                histories = changelog.get("histories", []) or []
                
                for history in histories:
                    history_date = parse_iso(history.get("created"))
                    items = history.get("items", []) or []
                    for item in items:
                        if item.get("field") == "status":
                            estado_anterior = item.get("fromString")
                            estado_nuevo = item.get("toString")
                            
                            transition_repo.create(db, obj_in={
                                "id_jira": issue_id,
                                "estado_anterior": estado_anterior,
                                "estado_nuevo": estado_nuevo,
                                "fecha_cambio": history_date
                            })
                            
                total_processed += 1
                
            is_last = search_data.get("isLast", True)
            page_token = search_data.get("nextPageToken")
            
            if is_last or not page_token:
                break
            await asyncio.sleep(0.3)  # Evitar saturar el API de Jira con peticiones continuas (429)
            
    return total_processed

async def run_jira_sync(user_id: int, db: Session):
    start_time = time.time()
    user = user_repo.get(db, user_id)
    if not user:
        print(f"Sync failed: User with ID {user_id} not found")
        return
        
    base_jira_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
    agile_jira_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/agile/1.0"
    
    headers = {
        "Authorization": f"Bearer {user.access_token}",
        "Accept": "application/json"
    }
    
    # Crear de inmediato un registro de auditoría con estado RUNNING para evitar condiciones de carrera en el frontend
    db_log = log_repo.create(db, obj_in={
        "tipo_sincronizacion": "FULL_SYNC",
        "resultado": "RUNNING",
        "tiempo_ejecucion_segundos": 0,
        "issues_procesados": 0,
        "detalle_error": None,
        "ejecutado_por": user.nombre or f"User {user.id_usuario}"
    })
    
    issues_processed = 0
    resultado = "SUCCESS"
    detalle_error = None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            sprint_field_id, sp_field_id = await get_jira_field_mappings(client, base_jira_url, headers, db, user)
            projects = await sync_projects(client, base_jira_url, headers, db, user)
            # Sincronización de sprints por API de Agile omitida para evitar errores 401 de scope.
            # Los sprints se gestionan y crean dinámicamente a partir de los issues.
                
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
    
    # Actualizar el registro de auditoría con el resultado final
    log_repo.update(db, db_obj=db_log, obj_in={
        "resultado": resultado,
        "tiempo_ejecucion_segundos": elapsed_time,
        "issues_procesados": issues_processed,
        "detalle_error": detalle_error[:2000] if detalle_error else None
    })

async def run_jira_sync_task(user_id: int):
    db = SessionLocal()
    try:
        await run_jira_sync(user_id, db)
    finally:
        db.close()
