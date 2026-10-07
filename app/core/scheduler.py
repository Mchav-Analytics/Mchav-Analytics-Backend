# app/core/scheduler.py
# Motor de Sincronización Automática e Incremental en Segundo Plano (HU-010)

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories import user_repo, log_repo
from app.services.jira_sync import run_jira_sync

_scheduler = None

def scheduled_sync_job(user_id: int = None):
    """
    Job programado por el Scheduler de APScheduler.
    Ejecuta la sincronización incremental para un usuario específico con bloqueo distribuido.
    """
    if user_id is None:
        db = SessionLocal()
        try:
            if log_repo.has_running_sync(db):
                return
            user = db.query(user_repo.model).filter(user_repo.model.activo.is_(True)).first()
            if not user:
                return
            user_id = user.id_usuario
            try:
                res = run_jira_sync(user_id)
                if asyncio.iscoroutine(res):
                    asyncio.run(res)
            except Exception:
                pass
        except Exception:
            pass
        finally:
            db.close()
        return

    print(f"[Cron Scheduler] Adquiriendo candado y ejecutando job de sincronización para usuario ID {user_id}...")
    
    # Enviar petición HTTP al endpoint interno de FastAPI para delegar
    # la ejecución asíncrona a Starlette BackgroundTasks (evita bug de threading)
    import httpx
    try:
        # Usamos httpx en modo síncrono con Client()
        with httpx.Client(timeout=5.0) as client:
            res = client.post(f"http://127.0.0.1:8000/api/v1/jira/sync/internal_cron?user_id={user_id}")
            
        if res.status_code == 200:
            print(f"[Cron Scheduler] Petición de sincronización delegada exitosamente (User {user_id}).")
        else:
            print(f"[Cron Scheduler] Delegación denegada (ej. Sincronización en curso): {res.text}")
    except Exception as http_err:
        print(f"[Cron Scheduler] Falló la delegación HTTP: {http_err}")

def scheduled_monthly_reports_job():
    """
    Job programado mensual de APScheduler.
    Se ejecuta el primer día de cada mes a las 08:00 AM para consolidar métricas y despachar correos a Admins y Líderes.
    """
    print("[Cron Scheduler] Ejecutando envío mensual de reportes por correo con Nubi AI...")
    db = SessionLocal()
    try:
        from app.services.monthly_report_dispatcher_service import dispatch_monthly_reports
        result = dispatch_monthly_reports(db)
        print(f"[Cron Scheduler] Reportes mensuales despachados con éxito: {result}")
    except Exception as e:
        print(f"[Cron Scheduler] Error en el trabajo mensual de reportes: {e}")
    finally:
        db.close()

def start_scheduler():
    """Inicializa y arranca el planificador de tareas APScheduler y lee los horarios de la DB."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        
        # Programar ejecución mensual automática el 1 de cada mes a las 08:00 AM
        _scheduler.add_job(
            scheduled_monthly_reports_job,
            trigger=CronTrigger(day=1, hour=8, minute=0),
            id="automatic_monthly_reports",
            replace_existing=True
        )
        
        # Leer horarios de los usuarios y programarlos
        db = SessionLocal()
        try:
            users = db.query(user_repo.model).filter(
                user_repo.model.activo.is_(True),
                user_repo.model.auto_sync_enabled.is_(True)
            ).all()
            for user in users:
                # Se fija a las 23:00 para todos de forma predeterminada
                cron_time = "23:00"
                
                try:
                    hour, minute = cron_time.split(":")
                    _scheduler.add_job(
                        scheduled_sync_job, 
                        args=[user.id_usuario],
                        trigger=CronTrigger(hour=int(hour), minute=int(minute)), 
                        id=f"automatic_jira_sync_{user.id_usuario}",
                        replace_existing=True
                    )
                    print(f"[Cron Scheduler] Tarea programada para usuario {user.id_usuario} a las {cron_time}.")
                except Exception as e:
                    print(f"[Cron Scheduler] Error programando tarea para usuario {user.id_usuario}: {e}")
                    
        except Exception as e:
            print(f"[Cron Scheduler] Error al leer usuarios para programar tareas: {e}")
        finally:
            db.close()
            
        _scheduler.start()
        print("[Cron Scheduler] APScheduler iniciado.")

def stop_scheduler():
    """Detiene el planificador si está activo."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Cron Scheduler] APScheduler detenido.")
