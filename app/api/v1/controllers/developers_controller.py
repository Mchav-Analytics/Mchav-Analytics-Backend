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

from pydantic import BaseModel, Field

class MatrixConfigPayload(BaseModel):
    quality_threshold: float = Field(80.0, description="Umbral de calidad objetivo (50-95%)")
    weight_throughput: float = Field(25.0, description="Ponderación Throughput (%)")
    weight_velocity: float = Field(20.0, description="Ponderación Velocidad (%)")
    weight_cycletime: float = Field(20.0, description="Ponderación Cycle Time (%)")
    weight_commitment: float = Field(20.0, description="Ponderación Commitment (%)")
    weight_quality: float = Field(15.0, description="Ponderación Calidad (%)")
    nombre_modelo: str = Field("Modelo Personalizado", description="Nombre del perfil de desempeño")

@router.get("/matrix")
def get_team_performance_matrix(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    sprint_id: str = Query(None, description="ID del sprint opcional"),
    db: Session = Depends(get_db),
    quality_threshold: float = Query(None, description="Umbral de calidad dinámico (opcional)"),
    w_tp: float = Query(None, description="Ponderación Throughput"),
    w_sp: float = Query(None, description="Ponderación Velocity"),
    w_ct: float = Query(None, description="Ponderación Cycle Time"),
    w_com: float = Query(None, description="Ponderación Commitment"),
    w_qual: float = Query(None, description="Ponderación Calidad")
):
    """
    Obtiene la Matriz Comparativa de Equipo con el Performance Score (0-100 pts),
    cuadrantes operativos (Estrella, Metódico, Alto Volumen, Atascado) y explicaciones detalladas (Fase 6).
    """
    weights = None
    if any(x is not None for x in [w_tp, w_sp, w_ct, w_com, w_qual]):
        weights = {
            "w_tp": w_tp if w_tp is not None else 25.0,
            "w_sp": w_sp if w_sp is not None else 20.0,
            "w_ct": w_ct if w_ct is not None else 20.0,
            "w_com": w_com if w_com is not None else 20.0,
            "w_qual": w_qual if w_qual is not None else 15.0
        }
    try:
        return calculate_team_performance_matrix(db, proyecto_id, sprint_id, quality_threshold, weights)
    except Exception as e:
        if hasattr(db, 'rollback'): db.rollback()
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

@router.post("/matrix/config")
def save_matrix_config(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    payload: MatrixConfigPayload = None,
    db: Session = Depends(get_db)
):
    """
    Guarda de forma permanente la configuración de umbrales y ponderaciones de la matriz para un proyecto.
    """
    if not payload:
        payload = MatrixConfigPayload()

    cfg = db.query(models.ConfiguracionMatriz).filter(models.ConfiguracionMatriz.id_proyecto == proyecto_id).first()
    if not cfg:
        cfg = models.ConfiguracionMatriz(id_proyecto=proyecto_id)
        db.add(cfg)

    cfg.quality_threshold = payload.quality_threshold
    cfg.weight_throughput = payload.weight_throughput
    cfg.weight_velocity = payload.weight_velocity
    cfg.weight_cycletime = payload.weight_cycletime
    cfg.weight_commitment = payload.weight_commitment
    cfg.weight_quality = payload.weight_quality
    cfg.nombre_modelo = payload.nombre_modelo

    db.commit()
    db.refresh(cfg)
    return {
        "status": "success",
        "message": "Configuración de la Matriz guardada permanentemente con éxito",
        "config": {
            "proyecto_id": proyecto_id,
            "quality_threshold": float(cfg.quality_threshold),
            "weights": {
                "w_tp": float(cfg.weight_throughput),
                "w_sp": float(cfg.weight_velocity),
                "w_ct": float(cfg.weight_cycletime),
                "w_com": float(cfg.weight_commitment),
                "w_qual": float(cfg.weight_quality)
            },
            "nombre_modelo": cfg.nombre_modelo
        }
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

from pydantic import BaseModel

class TaskStatusUpdate(BaseModel):
    status: str

@router.patch("/me/agenda-tasks/{task_key}")
def update_task_status(
    task_key: str,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Actualiza el estado de una tarea asignada en la agenda (directo en BD local).
    """
    issue = db.query(models.Issue).filter(models.Issue.key_issue == task_key).first()
    if issue:
        issue.status_actual = payload.status
        db.commit()
        return {"status": "success", "issue_key": task_key, "new_status": payload.status}
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Issue not found")
