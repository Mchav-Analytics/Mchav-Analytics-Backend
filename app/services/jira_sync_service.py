# app/services/jira_sync_service.py
# Motor ETL (Extract, Transform, Load) completo para la sincronización asíncrona de datos desde Jira Cloud
# Descarga proyectos, tableros, sprints, tickets y transiciones; gestiona logs de auditoría e invoca el cálculo de KPIs

import os
import re
import time
import traceback
import httpx
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

import app.models as models
from app.core.database import SessionLocal
from app.services.kpi import calculate_and_save_kpis
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, log_repo
from app.datasources.jira_datasource import JiraDatasource

def get_jira_auth_credentials(db: Session, user: models.User) -> tuple[str, dict]:
    """Delegador que obtiene la URL base y encabezados de autorización llamando a JiraDatasource."""
    return JiraDatasource.get_auth_credentials(db, user)

async def refresh_user_token(db: Session, user: models.User, client: httpx.AsyncClient):
    """Intercambia el refresh_token almacenado por un nuevo access_token cuando el previo expira."""
    token_url = "https://auth.atlassian.com/oauth/token"
    client_id = os.getenv("JIRA_CLIENT_ID", "").strip()
    client_secret = os.getenv("JIRA_CLIENT_SECRET", "").strip()
    
    if not user.refresh_token:
        return
        
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": user.refresh_token
    }
    
    res = await client.post(token_url, json=data)
    if res.status_code == 200:
        tokens = res.json()
        user_repo.update(db, db_obj=user, obj_in={
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token", user.refresh_token)
        })
        print(f"[OAuth] Token actualizado para el usuario {user.id_usuario}")

async def sync_projects(client: httpx.AsyncClient, base_jira_url: str, headers: dict, db: Session, user: models.User):
    """
    EXTRACCIÓN Y CARGA DE PROYECTOS:
    Consulta los proyectos visibles en Jira y actualiza la tabla 'proyectos' en la BD local.
    """
    projects_data = await JiraDatasource.fetch_projects(client, base_jira_url, headers)
    
    synced_projects = []
    for proj in projects_data:
        key = proj.get("key")
        name = proj.get("name")
        jira_id = str(proj.get("id"))
        
        project = project_repo.get_by_key(db, key)
        if not project:
            project = project_repo.create(db, obj_in={
                "id_proyecto": jira_id,
                "key_proyecto": key,
                "nombre": name
            })
        else:
            project = project_repo.update(db, db_obj=project, obj_in={
                "nombre": name
            })
            
        synced_projects.append(project)
        
    return synced_projects

async def sync_issues_for_project(
    client: httpx.AsyncClient, 
    base_jira_url: str, 
    base_agile_url: str, 
    headers: dict, 
    db: Session, 
    project: models.Proyecto
):
    """
    EXTRACCIÓN Y CARGA DE SPRINTS, TICKETS Y HISTORIAL DE TRANSICIONES:
    1. Filtra tableros pertenecientes estrictamente al proyecto (validación location.projectKey) para evitar fuga entre proyectos.
    2. Descarga todos los Sprints (activos, futuros y cerrados) con sus fechas.
    3. Descarga masiva de tickets mediante JQL paginado con expansión de changelog.
    4. Persiste el historial inmutable de cambios de estado para cada ticket.
    """
    jql = f"project = '{project.key_proyecto}' ORDER BY created ASC"
    start_at = 0
    max_results = 100
    total_processed = 0
    
    # 1. Obtener tableros y sprints del proyecto
    try:
        boards_data = await JiraDatasource.fetch_boards_for_project(client, base_agile_url, headers, project.key_proyecto)
        boards = boards_data.get("values", [])
        
        for b in boards:
            b_id = b.get("id")
            if not b_id:
                continue
                
            # Validar pertenencia del tablero
            loc = b.get("location", {}) or {}
            loc_key = loc.get("projectKey")
            if loc_key and loc_key.upper() != project.key_proyecto.upper():
                print(f"[Sync] Omitiendo tablero {b_id} ({b.get('name')}) porque pertenece a {loc_key} y no a {project.key_proyecto}")
                continue

            sprints_data = await JiraDatasource.fetch_board_sprints(client, base_agile_url, headers, b_id)
            for spr in sprints_data.get("values", []):
                sprint_id_str = str(spr.get("id"))
                nombre = spr.get("name")
                estado = spr.get("state")
                
                f_inicio = spr.get("startDate")
                f_fin = spr.get("endDate")
                f_complete = spr.get("completeDate")
                
                dt_inicio = datetime.fromisoformat(f_inicio.replace("Z", "+00:00")) if f_inicio else None
                dt_fin = datetime.fromisoformat(f_fin.replace("Z", "+00:00")) if f_fin else None
                dt_complete = datetime.fromisoformat(f_complete.replace("Z", "+00:00")) if f_complete else None
                
                existing_sprint = sprint_repo.get_by_id_sprint(db, sprint_id_str)
                s_data = {
                    "id_sprint": sprint_id_str,
                    "id_proyecto": project.id_proyecto,
                    "nombre": nombre,
                    "estado": estado,
                    "fecha_inicio": dt_inicio,
                    "fecha_fin": dt_fin,
                    "fecha_finalizacion": dt_complete
                }
                if not existing_sprint:
                    sprint_repo.create(db, obj_in=s_data)
                elif existing_sprint.id_proyecto == project.id_proyecto:
                    sprint_repo.update(db, db_obj=existing_sprint, obj_in=s_data)
    except Exception as e:
        print(f"Advertencia obteniendo tableros y sprints para {project.key_proyecto}: {e}")

    next_page_token = None
    
    # 2. Descargar tickets via JQL y cargarlos en BD
    while True:
        data = await JiraDatasource.fetch_issues_jql(
            client, base_jira_url, headers, jql, start_at=start_at, max_results=max_results, next_page_token=next_page_token
        )
        
        issues = data.get("issues", [])
        if not issues:
            break
            
        for issue_data in issues:
            issue_id = str(issue_data.get("id"))
            issue_key = issue_data.get("key")
            fields = issue_data.get("fields", {})
            
            summary = fields.get("summary")
            status_obj = fields.get("status", {})
            estado = status_obj.get("name")
            
            created_str = fields.get("created")
            updated_str = fields.get("updated")
            
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.now(timezone.utc)
            updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(timezone.utc)
            
            # Extraer Sprint(s) asignados al ticket
            all_issue_sprints = []
            sprint_field = fields.get("sprint") or fields.get("customfield_10020")
            if sprint_field:
                sprint_list = sprint_field if isinstance(sprint_field, list) else [sprint_field]
                for s_item in sprint_list:
                    s_id = None
                    s_name = None
                    s_state = "CLOSED"
                    if isinstance(s_item, dict):
                        s_id = str(s_item.get("id"))
                        s_name = s_item.get("name")
                        s_state = s_item.get("state", "CLOSED")
                    elif isinstance(s_item, str) and "id=" in s_item:
                        m_id = re.search(r'id=(\d+)', s_item)
                        if m_id:
                            s_id = m_id.group(1)
                        m_name = re.search(r'name=([^,]+)', s_item)
                        if m_name:
                            s_name = m_name.group(1)
                    
                    if s_id:
                        all_issue_sprints.append(s_id)
                        ex_sp = sprint_repo.get_by_id_sprint(db, s_id)
                        if not ex_sp:
                            try:
                                sprint_repo.create(db, obj_in={
                                    "id_sprint": s_id,
                                    "id_proyecto": project.id_proyecto,
                                    "nombre": s_name or f"Sprint {s_id}",
                                    "estado": s_state
                                })
                            except Exception as sp_err:
                                db.rollback()

            sprint_id = all_issue_sprints[-1] if all_issue_sprints else None

            fecha_fin = None
            if status_obj.get("statusCategory", {}).get("key") == "done":
                fecha_fin = updated_at

            # Extraer campos de asignación, tipo, prioridad y Story Points
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

            # Extraer Épica contenedora
            parent_obj = fields.get("parent") or {}
            epic_field = fields.get("epic") or fields.get("customfield_10014") or {}
            epic_key = None
            epic_name = None
            if isinstance(parent_obj, dict) and parent_obj.get("key"):
                epic_key = parent_obj.get("key")
                epic_name = parent_obj.get("fields", {}).get("summary") or parent_obj.get("summary")
            elif isinstance(epic_field, dict):
                epic_key = epic_field.get("key")
                epic_name = epic_field.get("name") or epic_field.get("summary")
            elif isinstance(epic_field, str):
                epic_key = epic_field

            # Extraer Componentes
            comps_list = fields.get("components") or []
            comp_names = [c.get("name") for c in comps_list if isinstance(c, dict) and c.get("name")]
            components_str = ", ".join(comp_names) if comp_names else None

            db_issue = issue_repo.get_by_key(db, issue_key)
            i_data = {
                "id_jira": issue_id,
                "key_issue": issue_key,
                "id_proyecto": project.id_proyecto,
                "summary": summary or "",
                "status_actual": estado or "Unknown",
                "story_points": story_pts,
                "created_at": created_at,
                "resolved_at": fecha_fin,
                "id_sprint": sprint_id,
                "assignee_id": assignee_id,
                "assignee_name": assignee_name,
                "assignee_email": assignee_email,
                "issue_type": issue_type,
                "priority": priority,
                "epic_key": epic_key,
                "epic_name": epic_name,
                "components": components_str
            }
            
            if not db_issue:
                db_issue = issue_repo.create(db, obj_in=i_data)
            else:
                db_issue = issue_repo.update(db, db_obj=db_issue, obj_in=i_data)
                
            # Extraer e insertar el historial de cambios de estado (changelog)
            try:
                changelog_data = issue_data.get("changelog", {}) or {}
                histories = changelog_data.get("histories") or changelog_data.get("values")
                if histories is None:
                    changelog = await JiraDatasource.fetch_issue_changelog(client, base_jira_url, headers, issue_key)
                    histories = changelog.get("values", [])
                
                for history in histories:
                    created_t = history.get("created")
                    t_date = datetime.fromisoformat(created_t.replace("Z", "+00:00")) if created_t else datetime.now(timezone.utc)
                    
                    for item in history.get("items", []):
                        if item.get("field") == "status":
                            from_status = item.get("fromString")
                            to_status = item.get("toString")
                            
                            existing_trans = transition_repo.get_existing(db, db_issue.id_jira, t_date, from_status, to_status)
                            if not existing_trans:
                                transition_repo.create(db, obj_in={
                                    "id_jira": db_issue.id_jira,
                                    "estado_anterior": from_status,
                                    "estado_nuevo": to_status,
                                    "fecha_cambio": t_date
                                })
            except Exception as e:
                print(f"Error procesando historial para {issue_key}: {e}")

            total_processed += 1

        next_page_token = data.get("nextPageToken")
        is_last = data.get("isLast", False)
        
        # Si la API v3 retorna isLast o ya no hay nextPageToken, terminamos
        if is_last or not next_page_token:
            # Fallback legacy si la API anterior respondía con "total" (no es el caso de search/jql, pero por seguridad)
            start_at += max_results
            total = data.get("total", 0)
            if not next_page_token and total > 0 and start_at >= total:
                break
            elif not next_page_token:
                break
    return total_processed

def run_jira_sync_task(user_id: int, tipo_sincronizacion: str = "MANUAL"):
    """
    Función de entrada para BackgroundTasks de FastAPI.
    Abre una conexión independiente a la base de datos (SessionLocal), crea una entrada en logs_sincronizacion,
    ejecuta la extracción asíncrona, recalcula los KPIs y marca el log como SUCCESS o ERROR registrando el traceback.
    """
    db = SessionLocal()
    log_entry = None
    start_time = time.time()
    total_issues = 0

    try:
        if isinstance(user_id, models.User):
            user = user_id
            user_id = user.id_usuario
        else:
            user = user_repo.get(db, user_id)

        if not user:
            print(f"[Sync Error] Usuario {user_id} no encontrado en base de datos.")
            return

        ejecutado_por = user.nombre or user.email or f"Usuario {user_id}"
        log_entry = log_repo.create(db, obj_in={
            "fecha_ejecucion": datetime.now(timezone.utc),
            "tipo_sincronizacion": tipo_sincronizacion,
            "issues_procesados": 0,
            "tiempo_ejecucion_segundos": 0,
            "resultado": "RUNNING",
            "ejecutado_por": ejecutado_por
        })
        
        base_jira_url, headers = get_jira_auth_credentials(db, user)
        base_agile_url = base_jira_url.replace("/rest/api/3", "/rest/agile/1.0")

        async def _async_sync():
            nonlocal total_issues
            async with httpx.AsyncClient(timeout=60.0) as client:
                projects = await sync_projects(client, base_jira_url, headers, db, user)
                
                for project in projects:
                    count = await sync_issues_for_project(client, base_jira_url, base_agile_url, headers, db, project)
                    total_issues += count
                    
                    # Calcular y guardar las agregaciones KPI para el proyecto
                    calculate_and_save_kpis(db, project.id_proyecto)
                    print(f"SUCCESS: KPIs calculados para el proyecto {project.id_proyecto}")

        asyncio.run(_async_sync())

        duration = int(time.time() - start_time)
        log_repo.update(db, db_obj=log_entry, obj_in={
            "issues_procesados": total_issues,
            "tiempo_ejecucion_segundos": duration,
            "resultado": "SUCCESS"
        })
        print(f"[Sync Exitoso] Procesados {total_issues} tickets en {duration} segundos por {ejecutado_por}.")

    except Exception as e:
        db.rollback()
        duration = int(time.time() - start_time)
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"[Sync Error] Falló la sincronización: {error_msg}\n{traceback_str}")

        if log_entry:
            log_repo.update(db, db_obj=log_entry, obj_in={
                "issues_procesados": total_issues,
                "tiempo_ejecucion_segundos": duration,
                "resultado": "ERROR",
                "detalle_error": f"{error_msg}\n{traceback_str[:300]}"
            })
    finally:
        db.close()

async def run_jira_sync(user_id: int, db: Session, tipo_sincronizacion: str = "MANUAL"):
    """Wrapper asíncrono para ejecutar la sincronización directamente."""
    run_jira_sync_task(user_id, tipo_sincronizacion)
