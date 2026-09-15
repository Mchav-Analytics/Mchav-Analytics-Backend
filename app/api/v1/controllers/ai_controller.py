# app/api/v1/controllers/ai_controller.py
# Controlador HTTP para la interacción conversacional en tiempo real con la IA de Google Gemini

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
import app.models as models
from app.services.gemini_service import chat_with_gemini, generate_report_insights
from app.services.sprint_health_service import calculate_sprint_health
from app.services.dev_metrics_service import get_base_status
from app.services.kpi import get_issue_cycle_time_days

router = APIRouter(dependencies=[Depends(get_current_user)])


class ChatMessageRequest(BaseModel):
    message: str
    project_id: Optional[str] = "PROJ-01"
    history: Optional[List[Dict[str, str]]] = []


class ReportInsightsRequest(BaseModel):
    reportType: Optional[str] = "sprint"
    sprintName: Optional[str] = "Sprint Actual"
    velocity: Optional[float] = 0.0
    throughput: Optional[int] = 0
    cycleTime: Optional[float] = 0.0
    blockedDays: Optional[int] = 0
    bugs: Optional[int] = 0
    totalScope: Optional[float] = 0.0
    sprintHealth: Optional[float] = 0.0
    p50: Optional[float] = 0.0
    p85: Optional[float] = 0.0
    p95: Optional[float] = 0.0
    plannedIssues: Optional[int] = 0
    developerName: Optional[str] = None
    developerId: Optional[str] = None
    projectId: Optional[str] = "PROJ-01"
    projectMetrics: Optional[List[Dict[str, Any]]] = []

>>>>>>> origin/Prueba_Desarrollo

def _build_rich_project_context(db: Session, project_id: str, user_name: str) -> Dict[str, Any]:
    """
    Extrae un contexto analítico profundo y completo de la base de datos local:
    - Salud del sprint y métricas de flujo
    - Desempeño individual por desarrollador (SP, Cycle Time, WIP, Bugs, Tareas)
    - Cuellos de botella e incidencias críticas
    - Alertas operativas del sistema
    """
    target_project = project_id or "10000"
    
    # Si el frontend envía 'PROJ-01' o una clave corta, intentar resolver la clave a id_proyecto de BD
    try:
        proj_obj = db.query(models.Proyecto).filter(
            (models.Proyecto.id_proyecto == target_project) | (models.Proyecto.key_proyecto == target_project)
        ).first()
        if proj_obj:
            target_project = proj_obj.id_proyecto
    except Exception:
        pass

    # 1. Salud de Sprint
    sprint_health_data = {}
    try:
        sprint_health_data = calculate_sprint_health(db, target_project)
    except Exception as e:
        print("Aviso: No se pudo calcular sprint health para el chat de IA:", e)

    # 2. Obtener todas las incidencias del proyecto
    issues_query = db.query(models.Issue)
    if target_project and target_project != "ALL":
        issues_query = issues_query.filter(models.Issue.id_proyecto == target_project)
    all_issues = issues_query.all()

    # 3. Agrupar desempeño por desarrollador individual
    dev_map = {}
    stuck_tickets = []

    for issue in all_issues:
        assignee = issue.assignee_name or issue.assignee_email or "Sin Asignar"
        if assignee == "Sin Asignar" and not issue.assignee_id:
            continue

        if assignee not in dev_map:
            dev_map[assignee] = {
                "name": assignee,
                "email": issue.assignee_email or "",
                "completed_sp": 0.0,
                "completed_count": 0,
                "wip_count": 0,
                "bugs_count": 0,
                "cycle_times": [],
                "active_tasks": []
            }

        st = get_base_status(issue.status_actual, db, target_project)
        sp = float(issue.story_points or 0)

        if st == "DONE":
            dev_map[assignee]["completed_sp"] += sp
            dev_map[assignee]["completed_count"] += 1
            ct = get_issue_cycle_time_days(issue)
            if ct and ct > 0:
                dev_map[assignee]["cycle_times"].append(ct)
        elif st == "IN_PROGRESS":
            dev_map[assignee]["wip_count"] += 1
            dev_map[assignee]["active_tasks"].append({
                "key": issue.key_issue,
                "summary": issue.summary,
                "status": issue.status_actual,
                "sp": sp,
                "priority": issue.priority or "Medium"
            })

        if issue.issue_type and issue.issue_type.lower() == "bug":
            dev_map[assignee]["bugs_count"] += 1

        # Detectar tickets bloqueados o estancados
        if (issue.status_actual or "").lower() in ("bloqueado", "blocked", "en qa", "qa", "in review", "en revisión") or issue.priority in ("High", "Highest"):
            stuck_tickets.append({
                "key": issue.key_issue,
                "summary": issue.summary,
                "assignee": assignee,
                "status": issue.status_actual,
                "priority": issue.priority
            })

    # Resumen analítico por desarrollador
    dev_performance_list = []
    for dev_name, data in dev_map.items():
        avg_ct = round(sum(data["cycle_times"]) / max(len(data["cycle_times"]), 1), 1) if data["cycle_times"] else 2.5
        dev_performance_list.append({
            "desarrollador": dev_name,
            "story_points_entregados": round(data["completed_sp"], 1),
            "tareas_completadas": data["completed_count"],
            "wip_en_progreso": data["wip_count"],
            "bugs_asignados": data["bugs_count"],
            "cycle_time_promedio_dias": avg_ct,
            "tareas_activas": data["active_tasks"][:4]
        })

    # 4. Alertas del sistema
    alerts_summary = []
    try:
        system_alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).limit(5).all()
        for alt in system_alerts:
            alerts_summary.append({
                "titulo": getattr(alt, "title", "Alerta"),
                "mensaje": getattr(alt, "message", str(alt)),
                "tipo": getattr(alt, "alert_type", "WARN")
            })
    except Exception:
        pass

    return {
        "id_proyecto": target_project,
        "user_name": user_name,
        "salud_sprint": {
            "health_score": sprint_health_data.get("health_score", 85),
            "cumplimiento_compromiso_pct": sprint_health_data.get("commitment_reliability_pct", 90.0),
            "scope_creep_sp": sprint_health_data.get("scope_creep_sp", 0.0),
            "eficiencia_flujo_pct": sprint_health_data.get("flow_efficiency_pct", 75.0),
            "cuello_botella_insight": sprint_health_data.get("bottleneck_insight", "Operación estable"),
            "diagnostico_gemini": sprint_health_data.get("gemini_insights", {})
        },
        "desempeno_desarrolladores_individual": dev_performance_list,
        "tickets_bloqueados_o_criticos": stuck_tickets[:6],
        "alertas_recientes": alerts_summary
    }


@router.post("/chat")
def chat_with_ai(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST /api/v1/ai/chat
    Recibe un mensaje del usuario y responde utilizando el motor conversacional analítico de Google Gemini.
    """
    user_name = current_user.nombre if current_user and current_user.nombre else (current_user.email if current_user else "Usuario")
    
    # Extraer el contexto real completo de la BD
    rich_context = _build_rich_project_context(db, payload.project_id, user_name)

    reply_text = chat_with_gemini(
        user_message=payload.message,
        context_info=rich_context,
        conversation_history=payload.history
    )

    return {
        "reply": reply_text,
        "status": "success"
    }


@router.get("/prompts")
def get_suggested_prompts():
    """
    GET /api/v1/ai/prompts
    Retorna preguntas sugeridas para el chat con la IA.
    """
    return [
        {"id": 1, "text": "¿Cuál es el desempeño individual de cada desarrollador?", "category": "Desarrolladores"},
        {"id": 2, "text": "¿Cuál es la salud del sprint y nuestros mayores cuellos de botella?", "category": "Salud Sprint"},
        {"id": 3, "text": "¿Quiénes tienen mayor carga de WIP en progreso?", "category": "Carga de Trabajo"},
        {"id": 4, "text": "¿Qué recomendaciones estratégicas tienes para el equipo?", "category": "Estrategia"}
    ]


@router.post("/generate-report-insights")
def ai_report_insights(
    payload: ReportInsightsRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST /api/v1/ai/generate-report-insights
    Recibe métricas numéricas del frontend y retorna un JSON con análisis textual para inyectar en el reporte.
    """
    metrics = payload.dict()
    report_type = metrics.get('reportType', 'sprint')
    
    # Inyectar datos históricos reales para desarrolladores
    if report_type == "desarrollador":
        dev_id = metrics.get("developerId")
        dev_name = metrics.get("developerName")
        proj_id = metrics.get("projectId") or "PROJ-01"
        
        try:
            from app.models.jira import Sprint, Issue
            from sqlalchemy import desc
            
            # Obtener los últimos 3 sprints cerrados
            sprints = db.query(Sprint).filter(
                Sprint.id_proyecto == proj_id,
                Sprint.estado.in_(["closed", "cerrado", "finalizado", "active"])
            ).order_by(desc(Sprint.fecha_fin)).limit(3).all()
            
            history_data = []
            for sprint in reversed(sprints):  # Orden cronológico (más antiguo primero)
                issues = db.query(Issue).filter(
                    Issue.id_sprint == sprint.id_sprint,
                    ((Issue.assignee_id == dev_id) | (Issue.assignee_name.ilike(f"%{dev_name}%")))
                ).all()
                
                completados = len([i for i in issues if get_base_status(i.status_actual) == "DONE"])
                bloqueos = len([i for i in issues if "bloqueado" in (i.status_actual or "").lower() or "blocked" in (i.status_actual or "").lower()])
                
                # Calcular Cycle Time promedio real
                ct_list = [get_issue_cycle_time_days(i) for i in issues if get_base_status(i.status_actual) == "DONE"]
                ct_promedio = round(sum(ct_list) / len(ct_list), 1) if ct_list else 0.0
                
                planned_sp = sum([(i.story_points or 0) for i in issues])
                completed_sp = sum([(i.story_points or 0) for i in issues if get_base_status(i.status_actual) == "DONE"])
                
                history_data.append({
                    "sprintName": sprint.nombre,
                    "ticketsCompletados": completados,
                    "cycleTime": ct_promedio,
                    "bloqueos": bloqueos,
                    "planned": planned_sp,
                    "completed": completed_sp
                })
            metrics["history_data"] = history_data
        except Exception as e:
            print(f"Error fetching real dev history: {e}")
            metrics["history_data"] = []

    
    # Textos por defecto en caso de fallo (fallback)
    fallback_insights = {
        "executiveSummary": "Durante el período evaluado, el equipo mantuvo un ritmo de trabajo estable. No se dispone de análisis avanzado en este momento.",
        "burnupFinding": "El alcance se mantuvo constante sin desviaciones significativas.",
        "cfdFinding": "El flujo de trabajo operó sin cuellos de botella críticos detectados.",
        "predictabilityConclusion": "La predictibilidad se mantiene dentro de los rangos históricos esperados.",
        "valueDelivery": f"Se entregaron {metrics.get('velocity', 0)} Story Points.",
        "efficiency": f"Se registró un tiempo de ciclo de {metrics.get('cycleTime', 0)} días.",
        "technicalQuality": "No se registraron defectos alarmantes.",
        "generalConclusion": "El equipo se encuentra operando dentro de los márgenes previstos."
    }
    
    report_type = metrics.get('reportType', 'sprint')
    insights = generate_report_insights(metrics, fallback_insights, report_type)
    
    return {
        "status": "success",
        "data": insights
    }
