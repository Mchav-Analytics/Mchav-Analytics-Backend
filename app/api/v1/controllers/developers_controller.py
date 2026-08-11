# app/api/v1/controllers/developers_controller.py
# Controlador REST API para el dominio de Métricas Individuales de Desarrolladores (Fase 5)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.deps import get_current_user
import app.models as models
from app.services.dev_metrics_service import (
    get_developer_scorecard_data,
    get_daily_focus_data,
    get_developer_alerts_data,
    perform_alert_action,
    get_activity_history_data
)
from app.services.performance_score_engine import calculate_team_performance_matrix

router = APIRouter()

@router.get("/matrix")
def get_team_performance_matrix(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    sprint_id: str = Query(None, description="ID del sprint opcional"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la Matriz Comparativa de Equipo con el Performance Score (0-100 pts),
    cuadrantes operativos (Estrella, Metódico, Alto Volumen, Atascado) y explicaciones detalladas (Fase 6).
    """
    try:
        return calculate_team_performance_matrix(db, proyecto_id, sprint_id)
    except Exception as e:
        db.rollback()
        print("Error en get_team_performance_matrix:", e)
        return {
            "proyecto_id": proyecto_id,
            "sprint_id": sprint_id,
            "team_summary": {
                "total_desarrolladores": 0,
                "promedio_score_equipo": 0.0,
                "team_avg_tickets": 0.0,
                "team_avg_sp": 0.0,
                "team_avg_cycle_time": 0.0,
                "top_performer": None,
                "conteo_cuadrantes": { "ESTRELLA": 0, "METODICO": 0, "ALTO_VOLUMEN": 0, "ATASCADO": 0 }
            },
            "developers": []
        }


@router.get("/me/scorecard")
def get_my_scorecard(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto a consultar"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene las métricas individuales y el Scorecard del desarrollador actualmente autenticado (Fase 5).
    """
    email = current_user.email if current_user else None
    return get_developer_scorecard_data(db, proyecto_id, email_or_assignee_id=email)

@router.get("/me/daily-focus")
def get_my_daily_focus(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene la matriz de atención diaria (Atención Inmediata, Tarea Activa del Día, En Review) y el consejo AI Dev Coach.
    """
    email = current_user.email if current_user else None
    return get_daily_focus_data(db, proyecto_id, email_or_assignee_id=email)

@router.get("/me/alerts")
def get_my_alerts(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene las alertas activadas por inactividad > 48h o límite de WIP superado para el desarrollador.
    """
    email = current_user.email if current_user else None
    return get_developer_alerts_data(db, proyecto_id, email_or_assignee_id=email)

@router.post("/me/alerts/{issue_id}/action")
def execute_alert_action(
    issue_id: str,
    action_type: str = Query("request_help", description="Tipo de acción: request_help, mark_blocked, split_task"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Ejecuta una acción de desbloqueo en un ticket (pedir ayuda, marcar bloqueado, descomponer tarea).
    """
    return perform_alert_action(db, issue_id, action_type)

@router.get("/me/activity-history")
def get_my_activity_history(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene el timeline de actividad cronológica reciente (Standups) y los logros/medallas desbloqueados.
    """
    email = current_user.email if current_user else None
    return get_activity_history_data(db, proyecto_id, email_or_assignee_id=email)

@router.get("/me/issues")
def get_my_issues(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene el listado de incidencias asignadas directamente al desarrollador autenticado.
    """
    email = current_user.email if current_user else None
    scorecard = get_developer_scorecard_data(db, proyecto_id, email_or_assignee_id=email)
    return {
        "proyecto_id": proyecto_id,
        "total_issues": len(scorecard.get("assigned_issues", [])),
        "issues": scorecard.get("assigned_issues", [])
    }

@router.get("")
def list_developers(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los desarrolladores que tienen tickets asignados en el proyecto.
    """
    devs = []
    try:
        query = db.query(models.Issue.assignee_id, models.Issue.assignee_name, models.Issue.assignee_email).filter(
            models.Issue.id_proyecto == proyecto_id
        ).distinct()
        results = query.all()
        seen = set()
        for row in results:
            a_id = getattr(row, 'assignee_id', None) or "UNASSIGNED"
            if a_id not in seen and a_id != "UNASSIGNED":
                seen.add(a_id)
                devs.append({
                    "assignee_id": a_id,
                    "nombre": getattr(row, 'assignee_name', None) or "Desarrollador",
                    "email": getattr(row, 'assignee_email', None) or ""
                })
    except Exception as e:
        print("Aviso: Fallback en list_developers debido a la estructura de la base de datos:", e)

    return devs

@router.get("/{assignee_id}/scorecard")
def get_developer_scorecard_by_id(
    assignee_id: str,
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db)
):
    """
    Obtiene las métricas individuales de un desarrollador específico por su ID o email.
    """
    return get_developer_scorecard_data(db, proyecto_id, email_or_assignee_id=assignee_id)
