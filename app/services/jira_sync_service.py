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
    """Delegador hacia la fuente de datos JiraDatasource."""
    return JiraDatasource.get_auth_credentials(db, user)

async def refresh_user_token(db: Session, user: models.User, client: httpx.AsyncClient):
    """Refresca el token OAuth de Atlassian si expiró."""
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
    """Sincroniza la lista de proyectos desde JiraDatasource."""
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
    """Sincroniza tickets, sprints y transiciones para un proyecto específico."""
    jql = f"project = '{project.key_proyecto}' ORDER BY created ASC"
    start_at = 0
    max_results = 100
    total_processed = 0
    
    # 1. Obtener Sprints del proyecto si hay tablero
    board_id = getattr(project, "id_board", None)
    if board_id:
        try:
            sprints_data = await JiraDatasource.fetch_board_sprints(client, base_agile_url, headers, board_id)
            for spr in sprints_data.get("values", []):
                sprint_id_str = str(spr.get("id"))
                nombre = spr.get("name")
                estado = spr.get("state")
                
                f_inicio = spr.get("startDate")
                f_fin = spr.get("endDate")
                
                dt_inicio = datetime.fromisoformat(f_inicio.replace("Z", "+00:00")) if f_inicio else None
                dt_fin = datetime.fromisoformat(f_fin.replace("Z", "+00:00")) if f_fin else None
                
                existing_sprint = sprint_repo.get_by_id_sprint(db, sprint_id_str)
                s_data = {
                    "id_sprint": sprint_id_str,
                    "id_proyecto": project.id_proyecto,
                    "nombre": nombre,
                    "estado": estado,
                    "fecha_inicio": dt_inicio,
                    "fecha_fin": dt_fin
                }
                if not existing_sprint:
                    sprint_repo.create(db, obj_in=s_data)
                else:
                    sprint_repo.update(db, db_obj=existing_sprint, obj_in=s_data)
        except Exception as e:
            print(f"Advertencia obteniendo Sprints para tablero {board_id}: {e}")

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
            
            sprint_id = None
            sprint_field = fields.get("sprint") or fields.get("customfield_10020")
            if sprint_field:
                if isinstance(sprint_field, list) and len(sprint_field) > 0:
                    last_sprint = sprint_field[-1]
                    if isinstance(last_sprint, dict):
                        sprint_id = str(last_sprint.get("id"))
                    elif isinstance(last_sprint, str) and "id=" in last_sprint:
                        m = re.search(r'id=(\d+)', last_sprint)
                        if m:
                            sprint_id = m.group(1)
                elif isinstance(sprint_field, dict):
                    sprint_id = str(sprint_field.get("id"))
            
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
                
            # Sincronizar Historial de Transiciones del Ticket
            try:
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
    Tarea de segundo plano (Background Task) que abre su propia conexión independiente a la Base de Datos.
    Ejecuta el job completo de sincronización de Jira, calcula métricas y guarda logs inmutables.
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
                    
                    # Calcular y actualizar KPIs
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
    """Sincronizador asíncrono directo (para invocaciones directas)."""
    run_jira_sync_task(user_id, tipo_sincronizacion)
