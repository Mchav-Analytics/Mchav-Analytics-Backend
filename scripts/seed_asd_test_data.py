import os
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
import app.models as models
from app.services.kpi import calculate_and_save_kpis

def seed_asd_data():
    db: Session = SessionLocal()
    try:
        project_id = "10033"
        project_key = "PA"
        
        # 1. Buscar o crear proyecto Prueba ASD
        project = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == project_id).first()
        if not project:
            project = models.Proyecto(
                id_proyecto=project_id,
                key_proyecto=project_key,
                nombre="Prueba ASD",
                estado="Active"
            )
            db.add(project)
            db.commit()
            print(f"Proyecto {project.nombre} ({project_id}) creado.")
        else:
            print(f"Proyecto existente encontrado: {project.nombre} ({project_id}).")

        # 2. Configurar Mapeo de Estados para Prueba ASD
        print("Configurando Mapeo de Estados...")
        db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == project_id).delete()
        
        mappings = [
            models.MapeoEstado(id_proyecto=project_id, estado_jira="Por hacer", estado_base="BACKLOG"),
            models.MapeoEstado(id_proyecto=project_id, estado_jira="En curso", estado_base="IN_PROGRESS"),
            models.MapeoEstado(id_proyecto=project_id, estado_jira="En revisión", estado_base="IN_PROGRESS"),
            models.MapeoEstado(id_proyecto=project_id, estado_jira="Listo", estado_base="DONE")
        ]
        db.add_all(mappings)
        db.commit()

        # 3. Limpiar sprints e issues antiguos del proyecto para generar dataset limpio y coherente
        print("Limpiando datos antiguos de sprints e issues...")
        old_issues = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id).all()
        for issue in old_issues:
            db.query(models.TransicionEstadoIssue).filter(models.TransicionEstadoIssue.id_jira == issue.id_jira).delete()
            issue.sprints.clear()
            db.delete(issue)
        db.commit()

        old_sprints = db.query(models.Sprint).filter(models.Sprint.id_proyecto == project_id).all()
        for spr in old_sprints:
            db.delete(spr)
        db.commit()

        # 4. Definir Sprints (4 Cerrados + 1 Activo)
        now = datetime.now(timezone.utc)
        
        sprints_info = [
            {
                "id_sprint": "sprint-asd-1",
                "nombre": "Sprint 1 - Fundación",
                "estado": "closed",
                "start": now - timedelta(days=50),
                "end": now - timedelta(days=36),
                "complete": now - timedelta(days=36)
            },
            {
                "id_sprint": "sprint-asd-2",
                "nombre": "Sprint 2 - Autenticación y Perfiles",
                "estado": "closed",
                "start": now - timedelta(days=35),
                "end": now - timedelta(days=22),
                "complete": now - timedelta(days=22)
            },
            {
                "id_sprint": "sprint-asd-3",
                "nombre": "Sprint 3 - API & Conectores",
                "estado": "closed",
                "start": now - timedelta(days=21),
                "end": now - timedelta(days=9),
                "complete": now - timedelta(days=9)
            },
            {
                "id_sprint": "sprint-asd-4",
                "nombre": "Sprint 4 - Motor de Métricas",
                "estado": "closed",
                "start": now - timedelta(days=8),
                "end": now - timedelta(days=1),
                "complete": now - timedelta(days=1)
            },
            {
                "id_sprint": "sprint-asd-5",
                "nombre": "Sprint 5 - Dashboard & Reportes (Activo)",
                "estado": "active",
                "start": now - timedelta(days=1),
                "end": now + timedelta(days=13),
                "complete": None
            }
        ]

        db_sprints = {}
        for s_data in sprints_info:
            spr = models.Sprint(
                id_sprint=s_data["id_sprint"],
                id_proyecto=project_id,
                nombre=s_data["nombre"],
                estado=s_data["estado"],
                fecha_inicio=s_data["start"],
                fecha_fin=s_data["end"],
                fecha_finalizacion=s_data["complete"]
            )
            db.add(spr)
            db_sprints[s_data["id_sprint"]] = spr
        db.commit()

        # 5. Generar Issues realistas con historia de transiciones
        task_templates = [
            ("Diseñar esquema de base de datos PostgreSQL", 5.0),
            ("Configurar autenticación OAuth2 con Atlassian", 8.0),
            ("Implementar endpoints de sincronización de Jira", 5.0),
            ("Crear vistas de administración de usuarios y roles", 3.0),
            ("Optimizar consultas SQL para Lead Time y Cycle Time", 5.0),
            ("Integrar gráficos interactivos de Recharts en el Dashboard", 8.0),
            ("Añadir exportación de logs de sincronización a JSON", 2.0),
            ("Refactorizar controladores de FastAPI con inyección de dep", 3.0),
            ("Configurar middleware de seguridad HMAC y cookies", 5.0),
            ("Diseñar componentes de interfaz con modo oscuro", 3.0),
            ("Implementar cálculo de Throughput por Sprint", 5.0),
            ("Desarrollar Webhook de recepción de eventos Jira", 8.0),
            ("Crear pruebas unitarias para repositorios de Jira", 3.0),
            ("Ajustar márgenes y diseño responsive del Dashboard", 2.0),
            ("Configurar tareas programadas Cron para la sincronización", 5.0),
            ("Implementar caché de métricas con ShortLivedCache", 3.0),
            ("Validar gestión de errores 429 de Rate Limit de Atlassian", 5.0),
            ("Desplegar contenedor Docker de Backend y Frontend", 8.0),
            ("Optimizar tiempo de carga inicial de proyectos", 3.0),
            ("Corregir filtrado de rangos de fechas en KPI historicos", 2.0),
            ("Crear documentación técnica de sustentación", 5.0),
            ("Pruebas de estrés de sincronización masiva", 8.0),
            ("Auditar seguridad de credenciales en archivo .env", 3.0),
            ("Implementar selector de Sprint en Dashboard", 2.0)
        ]

        ticket_counter = 101
        
        # Para cada Sprint cerrado, crear entre 5 y 8 tickets resueltos con tiempos creíbles
        for idx, s_data in enumerate(sprints_info[:4]):
            sprint_obj = db_sprints[s_data["id_sprint"]]
            s_start = s_data["start"]
            
            num_tickets = random.randint(6, 8)
            for i in range(num_tickets):
                summary, sp = task_templates[(ticket_counter + i) % len(task_templates)]
                issue_key = f"PA-{ticket_counter}"
                issue_id = f"jira-asd-{ticket_counter}"
                
                # Fechas coherentes:
                # Creación: 1 a 4 días antes de iniciar desarrollo o al inicio del sprint
                created_at = s_start + timedelta(days=random.randint(0, 2), hours=random.randint(8, 11))
                # Inicio de progreso (En curso): 1 a 2 días después de creación
                in_progress_date = created_at + timedelta(days=random.randint(1, 2), hours=random.randint(1, 5))
                # En revisión: 1 a 3 días después de En curso
                review_date = in_progress_date + timedelta(days=random.randint(1, 3), hours=random.randint(1, 4))
                # Listo (resuelto): 1 a 2 días después de En revisión
                resolved_at = review_date + timedelta(days=random.randint(1, 2), hours=random.randint(1, 3))
                
                issue = models.Issue(
                    id_jira=issue_id,
                    key_issue=issue_key,
                    id_proyecto=project_id,
                    id_sprint=sprint_obj.id_sprint,
                    summary=f"{summary} (SP {int(sp)})",
                    status_actual="Listo",
                    story_points=sp,
                    created_at=created_at,
                    resolved_at=resolved_at
                )
                db.add(issue)
                db.flush()
                
                # Relación M:M con Sprint
                issue.sprints.append(sprint_obj)
                
                # Transiciones de estado
                t1 = models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="Por hacer",
                    estado_nuevo="En curso",
                    fecha_cambio=in_progress_date
                )
                t2 = models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="En curso",
                    estado_nuevo="En revisión",
                    fecha_cambio=review_date
                )
                t3 = models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="En revisión",
                    estado_nuevo="Listo",
                    fecha_cambio=resolved_at
                )
                db.add_all([t1, t2, t3])
                ticket_counter += 1

        # Sprint 5 (ACTIVO): Incluir tickets En curso (Tickets Activos!), En revisión, Listos y Por hacer
        active_sprint = db_sprints["sprint-asd-5"]
        s5_start = active_sprint.fecha_inicio
        
        # 1. Tickets ACTIVOS en progreso ("En curso" / "En revisión")
        active_tasks = [
            ("Implementar sistema de notificaciones en tiempo real", 5.0, "En curso"),
            ("Desarrollar exportación de métricas a PDF", 8.0, "En curso"),
            ("Pruebas de usabilidad del módulo de sincronización", 3.0, "En revisión"),
            ("Optimizar consumo de memoria en consultas de Recharts", 5.0, "En curso")
        ]
        
        for summary, sp, status in active_tasks:
            issue_key = f"PA-{ticket_counter}"
            issue_id = f"jira-asd-{ticket_counter}"
            created_at = s5_start - timedelta(days=random.randint(1, 3))
            in_progress_date = s5_start + timedelta(hours=random.randint(2, 10))
            
            issue = models.Issue(
                id_jira=issue_id,
                key_issue=issue_key,
                id_proyecto=project_id,
                id_sprint=active_sprint.id_sprint,
                summary=summary,
                status_actual=status,
                story_points=sp,
                created_at=created_at,
                resolved_at=None  # AÚN NO RESUELTO -> TICKET ACTIVO!
            )
            db.add(issue)
            db.flush()
            issue.sprints.append(active_sprint)
            
            t1 = models.TransicionEstadoIssue(
                id_jira=issue_id,
                estado_anterior="Por hacer",
                estado_nuevo="En curso",
                fecha_cambio=in_progress_date
            )
            db.add(t1)
            
            if status == "En revisión":
                t2 = models.TransicionEstadoIssue(
                    id_jira=issue_id,
                    estado_anterior="En curso",
                    estado_nuevo="En revisión",
                    fecha_cambio=in_progress_date + timedelta(days=1)
                )
                db.add(t2)
            ticket_counter += 1

        # 2. Tickets listos en Sprint 5
        ready_tasks = [
            ("Ajustar diseño de tarjetas del Dashboard", 3.0),
            ("Fix de desbordamiento en tabla de auditoría de logs", 2.0)
        ]
        for summary, sp in ready_tasks:
            issue_key = f"PA-{ticket_counter}"
            issue_id = f"jira-asd-{ticket_counter}"
            created_at = s5_start - timedelta(days=2)
            in_progress_date = s5_start + timedelta(hours=4)
            resolved_at = s5_start + timedelta(days=1, hours=2)
            
            issue = models.Issue(
                id_jira=issue_id,
                key_issue=issue_key,
                id_proyecto=project_id,
                id_sprint=active_sprint.id_sprint,
                summary=summary,
                status_actual="Listo",
                story_points=sp,
                created_at=created_at,
                resolved_at=resolved_at
            )
            db.add(issue)
            db.flush()
            issue.sprints.append(active_sprint)
            
            t1 = models.TransicionEstadoIssue(
                id_jira=issue_id,
                estado_anterior="Por hacer",
                estado_nuevo="En curso",
                fecha_cambio=in_progress_date
            )
            t2 = models.TransicionEstadoIssue(
                id_jira=issue_id,
                estado_anterior="En curso",
                estado_nuevo="Listo",
                fecha_cambio=resolved_at
            )
            db.add_all([t1, t2])
            ticket_counter += 1

        # 3. Tickets por hacer en Sprint 5 (Backlog)
        todo_tasks = [
            ("Integrar alertas de Slack para fallos de sincronización", 5.0),
            ("Documentar API REST con Swagger / OpenAPI", 3.0)
        ]
        for summary, sp in todo_tasks:
            issue_key = f"PA-{ticket_counter}"
            issue_id = f"jira-asd-{ticket_counter}"
            created_at = s5_start
            
            issue = models.Issue(
                id_jira=issue_id,
                key_issue=issue_key,
                id_proyecto=project_id,
                id_sprint=active_sprint.id_sprint,
                summary=summary,
                status_actual="Por hacer",
                story_points=sp,
                created_at=created_at,
                resolved_at=None
            )
            db.add(issue)
            db.flush()
            issue.sprints.append(active_sprint)
            ticket_counter += 1

        db.commit()
        print(f"Total tickets insertados: {ticket_counter - 101}")

        # 6. Calcular y guardar KPIs en base de datos
        print("Calculando KPIs históricos para el proyecto y sus sprints...")
        calculate_and_save_kpis(db, project_id)
        
        print("¡DATOS DE PRUEBA GENERADOS CON ÉXITO PARA PROYECTO PRUEBA ASD (10033)!")

    except Exception as e:
        db.rollback()
        print(f"Error al sembrar datos de prueba: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_asd_data()
