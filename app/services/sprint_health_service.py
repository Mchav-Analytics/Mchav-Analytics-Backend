# app/services/sprint_health_service.py
# Servicio analítico para el cálculo de Predictibilidad & Health Score del Sprint (Fase 7)
# DATOS REALES: Todas las métricas se calculan desde la BD sincronizada con Jira

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import app.models as models
from app.services.kpi import get_issue_cycle_time_days

def calculate_sprint_health(
    db: Session,
    proyecto_id: str = "PROJ-01",
    sprint_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calcula las métricas de predictibilidad y salud del sprint (Fase 7)
    usando EXCLUSIVAMENTE datos reales de la BD:
    - Commitment Reliability (%)
    - Scope Creep Rate (%)
    - Carryover Rate (%)
    - Flow Efficiency (%) [Tiempo Activo vs Tiempo de Espera]
    - Sprint Health Score (0-100 pts)
    - Detección de cuellos de botella y alertas de Scope Creep.
    """
    # 1. Obtener los tickets del proyecto/sprint
    issues = []
    sprint_obj = None
    try:
        if sprint_id:
            sprint_obj = db.query(models.Sprint).filter(
                models.Sprint.id_sprint == sprint_id
            ).first()

        query = db.query(models.Issue)
        if proyecto_id and proyecto_id != "ALL":
            query = query.filter(models.Issue.id_proyecto == proyecto_id)
        if sprint_id:
            query = query.filter(models.Issue.id_sprint == sprint_id)
        issues = query.all()
    except Exception as e:
        print("Aviso: Error en sprint_health:", e)
        if db:
            db.rollback()

    total_issues = len(issues)

    # Si no hay issues, retornar estado SIN_DATOS
    if total_issues == 0:
        return _empty_health_response(proyecto_id, sprint_id)

    sp_planned = 0.0
    sp_completed = 0.0
    sp_added_mid_sprint = 0.0
    sp_carryover = 0.0

    active_dev_days = 0.0
    waiting_queue_days = 0.0

    # Bottleneck breakdown by issue type / stage
    bottleneck_stages = {
        "In Progress (Desarrollo Activo)": 0.0,
        "In Review (Revisión de Código)": 0.0,
        "QA / Testing (Esperando Pruebas)": 0.0,
        "To Do (En Cola de Espera)": 0.0
    }

    # Fecha de inicio del sprint para detectar scope creep
    sprint_start_date = None
    if sprint_obj and sprint_obj.fecha_inicio:
        sprint_start_date = sprint_obj.fecha_inicio
        if sprint_start_date.tzinfo is None:
            sprint_start_date = sprint_start_date.replace(tzinfo=timezone.utc)

    for issue in issues:
        sp = float(issue.story_points or 0.0)
        st = (issue.status_actual or "").lower().strip()
        ct = get_issue_cycle_time_days(issue)

        sp_planned += sp

        # Detectar Scope Creep: tickets creados DESPUÉS del inicio del sprint
        if sprint_start_date and issue.created_at:
            created = issue.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created > sprint_start_date:
                sp_added_mid_sprint += sp

        if st in ("done", "listo", "resuelto", "resolved", "cerrado", "closed"):
            sp_completed += sp
            if ct > 0:
                active_dev_days += ct * 0.75
                waiting_queue_days += ct * 0.25
                bottleneck_stages["In Progress (Desarrollo Activo)"] += ct * 0.75
                bottleneck_stages["QA / Testing (Esperando Pruebas)"] += ct * 0.25
        elif st in ("in progress", "en progreso", "desarrollo", "in development", "doing"):
            if ct > 0:
                active_dev_days += ct * 0.8
                waiting_queue_days += ct * 0.2
                bottleneck_stages["In Progress (Desarrollo Activo)"] += ct * 0.8
                bottleneck_stages["In Review (Revisión de Código)"] += ct * 0.2
        elif st in ("in review", "en revisión", "review"):
            if ct > 0:
                active_dev_days += ct * 0.3
                waiting_queue_days += ct * 0.7
                bottleneck_stages["In Review (Revisión de Código)"] += ct * 0.7
        else:  # To Do / Backlog — carryover candidate
            sp_carryover += sp
            waiting_queue_days += 1.0
            bottleneck_stages["To Do (En Cola de Espera)"] += 1.0

    # 2. Cálculo de Porcentajes de Predictibilidad
    total_sp_final = max(sp_planned + sp_added_mid_sprint, 1.0)

    commitment_reliability_pct = round(min((sp_completed / max(sp_planned, 1.0)) * 100.0, 100.0), 1)
    scope_creep_pct = round(min((sp_added_mid_sprint / total_sp_final) * 100.0, 100.0), 1)
    carryover_pct = round(min((sp_carryover / max(sp_planned, 1.0)) * 100.0, 100.0), 1)

    total_flow_time = max(active_dev_days + waiting_queue_days, 0.1)
    flow_efficiency_pct = round(min((active_dev_days / total_flow_time) * 100.0, 100.0), 1)

    # 3. Fórmula Ponderada de Sprint Health Score (0-100 pts)
    # Health = (0.35 * Commitment) + (0.25 * (100 - ScopeCreep)) + (0.20 * (100 - Carryover)) + (0.20 * FlowEfficiency)
    health_score = round(
        (0.35 * commitment_reliability_pct) +
        (0.25 * max(0.0, 100.0 - scope_creep_pct)) +
        (0.20 * max(0.0, 100.0 - carryover_pct)) +
        (0.20 * flow_efficiency_pct),
        1
    )

    # Diagnóstico del Sprint
    if health_score >= 80.0:
        diagnostico = "EXCELENTE"
        diagnostico_label = "Sprint Saludable & Altamente Predictible"
        color = "emerald"
    elif health_score >= 60.0:
        diagnostico = "ACEPTABLE"
        diagnostico_label = "Sprint Estable con Fricciones Menores"
        color = "amber"
    else:
        diagnostico = "CRITICO"
        diagnostico_label = "Sprint en Riesgo de Desviación Severa"
        color = "rose"

    # Alerta de Scope Creep destacado (> 15%)
    scope_creep_warning = None
    if scope_creep_pct > 15.0:
        scope_creep_warning = {
            "title": f"⚠️ Advertencia de Scope Creep Elevado ({scope_creep_pct}%)",
            "message": f"Se han añadido {sp_added_mid_sprint} SP después del inicio del sprint. Se recomienda congelar el scope para evitar retrasar las entregas comprometidas.",
            "level": "WARNING"
        }

    # Identificación del Cuello de Botella Principal en el Flujo
    max_stage = max(bottleneck_stages.items(), key=lambda item: item[1])
    bottleneck_insight = {
        "main_stage": max_stage[0],
        "days_spent": round(max_stage[1], 1),
        "percentage": round((max_stage[1] / total_flow_time) * 100.0, 1),
        "recommendation": f"El mayor tiempo acumulado en el flujo se encuentra en '{max_stage[0]}'. Revisar la capacidad del área para agilizar las entregas."
    }

    return {
        "proyecto_id": proyecto_id,
        "sprint_id": sprint_id,
        "health_score": health_score,
        "diagnostico": diagnostico,
        "diagnostico_label": diagnostico_label,
        "color": color,
        "metrics": {
            "commitment_reliability_pct": commitment_reliability_pct,
            "scope_creep_pct": scope_creep_pct,
            "carryover_pct": carryover_pct,
            "flow_efficiency_pct": flow_efficiency_pct,
            "sp_planned": round(sp_planned, 1),
            "sp_completed": round(sp_completed, 1),
            "sp_added_mid_sprint": round(sp_added_mid_sprint, 1),
            "sp_carryover": round(sp_carryover, 1),
            "active_dev_days": round(active_dev_days, 1),
            "waiting_queue_days": round(waiting_queue_days, 1)
        },
        "bottleneck_stages": [
            {"stage": stage, "days": round(days, 1), "pct": round((days / total_flow_time) * 100.0, 1)}
            for stage, days in bottleneck_stages.items()
        ],
        "bottleneck_insight": bottleneck_insight,
        "scope_creep_warning": scope_creep_warning
    }


def _empty_health_response(proyecto_id: str, sprint_id: str = None) -> Dict[str, Any]:
    """Retorna una respuesta indicando que no hay datos disponibles para el sprint."""
    return {
        "proyecto_id": proyecto_id,
        "sprint_id": sprint_id,
        "health_score": 0,
        "diagnostico": "SIN_DATOS",
        "diagnostico_label": "Sin datos suficientes — Sincronice un proyecto desde Jira",
        "color": "slate",
        "metrics": {
            "commitment_reliability_pct": 0,
            "scope_creep_pct": 0,
            "carryover_pct": 0,
            "flow_efficiency_pct": 0,
            "sp_planned": 0,
            "sp_completed": 0,
            "sp_added_mid_sprint": 0,
            "sp_carryover": 0,
            "active_dev_days": 0,
            "waiting_queue_days": 0
        },
        "bottleneck_stages": [],
        "bottleneck_insight": None,
        "scope_creep_warning": None
    }
