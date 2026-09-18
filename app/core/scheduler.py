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

def scheduled_sync_job():
    """
    Job programado por el Scheduler de APScheduler.
    Busca usuarios activos e invoca la sincronización incremental de Jira en segundo plano con bloqueo distribuido (Item 2).
    """
    print("[Cron Scheduler] Verificando bloqueo distribuido para sincronización automática...")
    db = SessionLocal()
    try:
        # Bloqueo distribuido: Si ya existe un log 'RUNNING', omitir inmediatamente
        if log_repo.has_running_sync(db):
            print("[Cron Scheduler] Omitiendo ejecución en este nodo: Ya existe una sincronización en proceso en otro nodo/instancia.")
            return

        admin_user = db.query(user_repo.model).filter(user_repo.model.activo.is_(True)).first()
        if admin_user:
            print(f"[Cron Scheduler] Adquiriendo candado y ejecutando job de sincronización para usuario ID {admin_user.id_usuario}...")
            asyncio.run(run_jira_sync(admin_user.id_usuario, sync_type="AUTOMATIC"))
            print("[Cron Scheduler] Sincronización automática distribuida finalizada con éxito.")
        else:
            print("[Cron Scheduler] No se encontró ningún usuario activo para ejecutar el job.")
    except Exception as e:
        print(f"[Cron Scheduler] Error en trabajo programado: {e}")
    finally:
        db.close()

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
    """Inicializa y arranca el planificador de tareas APScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        # Programar ejecución diaria automática a las 02:00 AM (HU-010 CA-01)
        _scheduler.add_job(
            scheduled_sync_job, 
            trigger=CronTrigger(hour=2, minute=0), 
            id="automatic_jira_sync",
            replace_existing=True
        )
        # Programar ejecución mensual automática el 1 de cada mes a las 08:00 AM
        _scheduler.add_job(
            scheduled_monthly_reports_job,
            trigger=CronTrigger(day=1, hour=8, minute=0),
            id="automatic_monthly_reports",
            replace_existing=True
        )
        _scheduler.start()
        print("[Cron Scheduler] APScheduler iniciado. Tarea 'automatic_jira_sync' (02:00 AM) y 'automatic_monthly_reports' (1° del mes 08:00 AM) programadas.")

def stop_scheduler():
    """Detiene el planificador si está activo."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Cron Scheduler] APScheduler detenido.")
