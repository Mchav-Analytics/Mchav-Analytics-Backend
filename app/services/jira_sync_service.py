# app/services/jira_sync_service.py
# Motor ETL (Extract, Transform, Load) completo para la sincronización asíncrona de datos desde Jira Cloud
# Descarga proyectos, tableros, sprints, tickets y transiciones; gestiona logs de auditoría e invoca el cálculo de KPIs

import os
import re
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

    # 2. Descargar tickets via JQL y cargarlos en BD
    while True:
        data = await JiraDatasource.fetch_issues_jql(
            client, base_jira_url, headers, jql, start_at=start_at, max_results=max_results
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
            
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.utcnow()
            updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.utcnow()
            
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

            db_issue = issue_repo.get_by_key(db, issue_key)
            i_data = {
                "id_jira": issue_id,
                "key_issue": issue_key,
                "id_proyecto": project.id_proyecto,
                "summary": summary or "",
                "status_actual": estado or "Unknown",
                "created_at": created_at,
                "resolved_at": fecha_fin,
                "id_sprint": sprint_id
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
                    t_date = datetime.fromisoformat(created_t.replace("Z", "+00:00")) if created_t else datetime.utcnow()
                    
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

        start_at += max_results
        total = data.get("total", 0)
        if start_at >= total:
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
        user = user_repo.get(db, user_id)
        if not user:
            print(f"[Sync Error] Usuario {user_id} no encontrado en base de datos.")
            return

        ejecutado_por = user.nombre or user.email or f"Usuario {user_id}"
        log_entry = log_repo.create(db, obj_in={
            "fecha_ejecucion": datetime.utcnow(),
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
