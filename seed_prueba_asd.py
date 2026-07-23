import sys
import os
import random
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal, engine
import app.models as models
from app.services.kpi import calculate_and_save_kpis

def seed_data():
    db = SessionLocal()
    try:
        print("Starting seed script for 'Prueba ASD' (ID: 10033)...")
        
        # 1. Obtener o crear Proyecto "Prueba ASD"
        project_id = "10033"
        project = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == project_id).first()
        if not project:
            project = models.Proyecto(
                id_proyecto=project_id,
                key_proyecto="PA",
                nombre="Prueba ASD",
                estado="Active"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        else:
            print(f"Proyecto existente encontrado: {project.nombre} ({project.key_proyecto})")

        # 2. Limpiar datos antiguos especificos de Prueba ASD
        db.query(models.KpisHistoricos).filter(models.KpisHistoricos.id_proyecto == project_id).delete()
        db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == project_id).delete()
        
        existing_issues = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id).all()
        for iss in existing_issues:
            db.query(models.TransicionEstadoIssue).filter(models.TransicionEstadoIssue.id_jira == iss.id_jira).delete()
            db.delete(iss)
            
        db.query(models.Sprint).filter(models.Sprint.id_proyecto == project_id).delete()
        db.commit()
        print("Datos anteriores de 'Prueba ASD' limpiados.")

        # 3. Crear Mapeos de Estado Estándar
        mapeos_base = [
            ("Por hacer", "TODO"),
            ("To Do", "TODO"),
            ("En curso", "IN_PROGRESS"),
            ("In Progress", "IN_PROGRESS"),
            ("En revisión", "IN_PROGRESS"),
            ("Finalizado", "DONE"),
            ("Done", "DONE"),
            ("Cerrado", "DONE")
        ]
        for m_jira, m_base in mapeos_base:
            db.add(models.MapeoEstado(id_proyecto=project_id, estado_jira=m_jira, estado_base=m_base))
        db.commit()

        # 4. Crear Histórico de Sprints (5 cerrados + 1 activo)
        now = datetime.now(timezone.utc)
        sprints_config = [
            {"id": "PA_SP_101", "name": "ASD Sprint 1", "state": "CLOSED", "days_ago_start": 70, "days_ago_end": 56},
            {"id": "PA_SP_102", "name": "ASD Sprint 2", "state": "CLOSED", "days_ago_start": 56, "days_ago_end": 42},
            {"id": "PA_SP_103", "name": "ASD Sprint 3", "state": "CLOSED", "days_ago_start": 42, "days_ago_end": 28},
            {"id": "PA_SP_104", "name": "ASD Sprint 4", "state": "CLOSED", "days_ago_start": 28, "days_ago_end": 14},
            {"id": "PA_SP_105", "name": "ASD Sprint 5", "state": "CLOSED", "days_ago_start": 14, "days_ago_end": 0},
            {"id": "PA_SP_106", "name": "ASD Sprint 6 (Actual)", "state": "ACTIVE", "days_ago_start": 0, "days_ago_end": -14},
        ]

        created_sprints = {}
        for sp in sprints_config:
            dt_start = now - timedelta(days=sp["days_ago_start"])
            dt_end = now - timedelta(days=sp["days_ago_end"])
            dt_comp = dt_end if sp["state"] == "CLOSED" else None
            
            db_sprint = models.Sprint(
                id_sprint=sp["id"],
                id_proyecto=project_id,
                nombre=sp["name"],
                estado=sp["state"],
                fecha_inicio=dt_start,
                fecha_fin=dt_end,
                fecha_finalizacion=dt_comp
            )
            db.add(db_sprint)
            created_sprints[sp["id"]] = db_sprint

        db.commit()
        print(f"Creados {len(created_sprints)} sprints con historial completo.")

        # 5. Crear Tickets y Transiciones por Sprint
        ticket_counter = 100
        total_tickets_created = 0

        summaries_pool = [
            "Implementar interfaz gráfica de métricas de velocidad",
            "Optimizar consultas SQL en backend de FastAPI",
            "Configurar tubería de integración continua en GitHub Actions",
            "Diseñar componente de gráfico de control Cycle Time",
            "Corregir bug de token en autenticación OAuth 2.0",
            "Refactorizar estructura de controladores Clean Architecture",
            "Integrar sistema de caché en memoria Redis / ShortLivedCache",
            "Agregar exportador de reportes en PDF y Excel",
            "Configurar contenedor Docker Compose para desarrollo local",
            "Crear migración de base de datos en Alembic para id_board",
            "Mejorar accesibilidad y contraste WCAG 2.1 AAA",
            "Auditar sentencias import de Python en cabeceras superiores"
        ]

        # Configuración de Story Points y completitud por sprint para simular una curva de velocidad realista
        sprint_ticket_plans = [
            {"sprint_id": "PA_SP_101", "completed_count": 5, "sp_list": [3, 5, 5, 3, 2], "in_progress_count": 0, "todo_count": 0}, # Total SP: 18
            {"sprint_id": "PA_SP_102", "completed_count": 6, "sp_list": [5, 5, 8, 3, 3, 2], "in_progress_count": 0, "todo_count": 0}, # Total SP: 26
            {"sprint_id": "PA_SP_103", "completed_count": 5, "sp_list": [8, 5, 5, 3, 3], "in_progress_count": 0, "todo_count": 0}, # Total SP: 24
            {"sprint_id": "PA_SP_104", "completed_count": 7, "sp_list": [5, 8, 8, 5, 3, 2, 2], "in_progress_count": 0, "todo_count": 0}, # Total SP: 33
            {"sprint_id": "PA_SP_105", "completed_count": 6, "sp_list": [8, 8, 5, 5, 3, 2], "in_progress_count": 0, "todo_count": 0}, # Total SP: 31
            {"sprint_id": "PA_SP_106", "completed_count": 3, "sp_list": [5, 5, 3], "in_progress_count": 4, "todo_count": 3}, # Sprint Activo: 3 Done, 4 In Progress, 3 To Do
        ]

        for plan in sprint_ticket_plans:
            sp_obj = created_sprints[plan["sprint_id"]]
            sp_start = sp_obj.fecha_inicio
            
            # 5a. Tickets completados (Done)
            for sp in plan["sp_list"]:
                ticket_counter += 1
                issue_id = f"PA_ISSUE_{ticket_counter}"
                issue_key = f"PA-{ticket_counter}"
                summary = random.choice(summaries_pool)
                
                # Fechas realistas para Lead Time y Cycle Time
                created_dt = sp_start + timedelta(days=random.randint(0, 3))
                progress_dt = created_dt + timedelta(days=random.randint(1, 2))
                resolved_dt = progress_dt + timedelta(days=random.randint(2, 5))
                
                issue = models.Issue(
                    id_jira=issue_id,
                    key_issue=issue_key,
                    id_proyecto=project_id,
                    id_sprint=plan["sprint_id"],
                    summary=summary,
                    status_actual="Done",
                    story_points=float(sp),
                    created_at=created_dt,
                    resolved_at=resolved_dt
                )
                db.add(issue)
                
                # Transición 1: To Do -> In Progress
                db.add(models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="To Do",
                    estado_nuevo="In Progress",
                    fecha_cambio=progress_dt
                ))
                # Transición 2: In Progress -> Done
                db.add(models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="In Progress",
                    estado_nuevo="Done",
                    fecha_cambio=resolved_dt
                ))
                total_tickets_created += 1

            # 5b. Tickets En Curso (In Progress) en Sprint Activo
            for _ in range(plan.get("in_progress_count", 0)):
                ticket_counter += 1
                issue_id = f"PA_ISSUE_{ticket_counter}"
                issue_key = f"PA-{ticket_counter}"
                summary = random.choice(summaries_pool)
                
                created_dt = sp_start + timedelta(days=random.randint(0, 2))
                progress_dt = created_dt + timedelta(days=random.randint(1, 2))
                
                issue = models.Issue(
                    id_jira=issue_id,
                    key_issue=issue_key,
                    id_proyecto=project_id,
                    id_sprint=plan["sprint_id"],
                    summary=summary,
                    status_actual="In Progress",
                    story_points=float(random.choice([3, 5, 8])),
                    created_at=created_dt,
                    resolved_at=None
                )
                db.add(issue)
                
                db.add(models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="To Do",
                    estado_nuevo="In Progress",
                    fecha_cambio=progress_dt
                ))
                total_tickets_created += 1

            # 5c. Tickets Por Hacer (To Do) en Sprint Activo
            for _ in range(plan.get("todo_count", 0)):
                ticket_counter += 1
                issue_id = f"PA_ISSUE_{ticket_counter}"
                issue_key = f"PA-{ticket_counter}"
                summary = random.choice(summaries_pool)
                
                created_dt = sp_start + timedelta(days=random.randint(0, 3))
                
                issue = models.Issue(
                    id_jira=issue_id,
                    key_issue=issue_key,
                    id_proyecto=project_id,
                    id_sprint=plan["sprint_id"],
                    summary=summary,
                    status_actual="To Do",
                    story_points=float(random.choice([2, 3, 5])),
                    created_at=created_dt,
                    resolved_at=None
                )
                db.add(issue)
                total_tickets_created += 1

        db.commit()
        print(f"Creados {total_tickets_created} tickets con historial completo de transiciones.")

        # 6. Recalcular KPIs Históricos para Prueba ASD
        calculate_and_save_kpis(db, project_id)
        print("KPIs calculados y guardados exitosamente para 'Prueba ASD'.")

        print("=== SEED COMPLETADO 100% EXITOSAMENTE ===")

    except Exception as e:
        db.rollback()
        print(f"Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
