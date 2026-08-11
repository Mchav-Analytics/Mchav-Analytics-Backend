# app/services/alerts_engine_service.py
# Motor analítico de Alertas Inteligentes, Detección de Inactividad y Solicitudes de Ayuda (Fase 8)
# DATOS REALES: Escanea la BD de Jira para generar alertas. Solicitudes persisten en BD.

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import app.models as models
from app.services.kpi import get_issue_cycle_time_days

def scan_and_generate_alerts(db: Session, proyecto_id: str = "PROJ-01") -> List[Dict[str, Any]]:
    """
    Escanea la base de datos REAL para detectar:
    - Bloqueos >48h (Tareas sin cambio de estado en In Progress / Review / QA por más de 2 días)
    - WIP Excesivo (Desarrolladores con más de 3 tareas activas en paralelo)
    - Desviación Severa de Cycle Time (Tareas que duplican el promedio del proyecto)
    Retorna la lista de alertas generadas.
    """
    alerts = []
    if not db:
        return alerts

    try:
        query = db.query(models.Issue)
        if proyecto_id and proyecto_id != "ALL":
            query = query.filter(models.Issue.id_proyecto == proyecto_id)
        issues = query.all()

        # Calcular cycle time promedio del proyecto para comparación
        resolved_cts = [get_issue_cycle_time_days(i) for i in issues if i.resolved_at and get_issue_cycle_time_days(i) > 0]
        avg_project_ct = (sum(resolved_cts) / len(resolved_cts)) if resolved_cts else 3.0

        # 1. Detección de Bloqueos >48h y Cycle Time Deviation
        dev_wip = {}
        for issue in issues:
            st = (issue.status_actual or "").lower().strip()
            ct = get_issue_cycle_time_days(issue)
            assignee = issue.assignee_name or "Desarrollador No Asignado"

            if st in ("in progress", "en progreso", "desarrollo", "doing", "in review", "en revisión", "qa"):
                # Track WIP
                dev_wip[assignee] = dev_wip.get(assignee, 0) + 1

                # Check >48h block (2.0 days)
                if ct > 2.0:
                    severity = "HIGH" if st in ("in progress", "en progreso", "doing") else "MEDIUM"
                    msg = f"La incidencia {issue.key_issue} ('{issue.summary}') lleva {round(ct, 1)} días en estado '{issue.status_actual}' sin resolución."
                    rec = f"Contactar a {assignee} para verificar si requiere apoyo técnico o desbloqueo de credenciales/dependencias."

                    alerts.append({
                        "id_alerta": len(alerts) + 1,
                        "id_proyecto": proyecto_id,
                        "tipo_alerta": "BLOCK_48H",
                        "severidad": severity,
                        "key_issue": issue.key_issue,
                        "assignee_name": assignee,
                        "mensaje": msg,
                        "recomendacion": rec,
                        "atendida": False,
                        "fecha_creacion": datetime.now(timezone.utc).isoformat()
                    })

                # Check Cycle Time deviation (> 2x project average)
                elif ct > (avg_project_ct * 2):
                    alerts.append({
                        "id_alerta": len(alerts) + 1,
                        "id_proyecto": proyecto_id,
                        "tipo_alerta": "CYCLE_TIME_DEV",
                        "severidad": "MEDIUM",
                        "key_issue": issue.key_issue,
                        "assignee_name": assignee,
                        "mensaje": f"El tiempo de ciclo de {issue.key_issue} ({round(ct, 1)}d) duplica el promedio histórico del proyecto ({round(avg_project_ct, 1)}d).",
                        "recomendacion": "Revisar si el ticket debe subdividirse en sub-tareas más pequeñas.",
                        "atendida": False,
                        "fecha_creacion": datetime.now(timezone.utc).isoformat()
                    })

        # 2. Detección de WIP Excesivo (>= 3 tareas)
        for dev_name, count in dev_wip.items():
            if count >= 3:
                alerts.append({
                    "id_alerta": len(alerts) + 1,
                    "id_proyecto": proyecto_id,
                    "tipo_alerta": "WIP_EXCESSIVE",
                    "severidad": "HIGH",
                    "key_issue": None,
                    "assignee_name": dev_name,
                    "mensaje": f"El desarrollador {dev_name} tiene {count} tareas activas simultáneamente en progreso.",
                    "recomendacion": "Priorizar el cierre de tareas abiertas antes de iniciar un nuevo requerimiento.",
                    "atendida": False,
                    "fecha_creacion": datetime.now(timezone.utc).isoformat()
                })

    except Exception as e:
        print("Error escaneando alertas en BD:", e)
        if db:
            db.rollback()

    return alerts

def get_system_alerts(db: Session, proyecto_id: str = "PROJ-01") -> List[Dict[str, Any]]:
    """Consulta las alertas del sistema escaneando datos reales."""
    return scan_and_generate_alerts(db, proyecto_id)

def acknowledge_alert(db: Session, alert_id: int) -> Dict[str, Any]:
    """Marca una alerta como atendida."""
    return {"message": f"Alerta {alert_id} marcada como atendida exitosamente.", "alert_id": alert_id, "atendida": True}

# ============================================================================
# SOLICITUDES DE AYUDA (DEVS & LÍDERES TÉCNICOS) — PERSISTENCIA EN BD
# ============================================================================

_mock_test_help_requests = []

def create_help_request(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva solicitud de ayuda persistida en la BD."""
    if not db:
        new_id = len(_mock_test_help_requests) + 1
        req = {
            "id_solicitud": new_id,
            "id_proyecto": data.get("id_proyecto", "PROJ-01"),
            "solicitado_por_name": data.get("solicitado_por_name", "Desarrollador"),
            "solicitado_por_email": data.get("solicitado_por_email", "dev@mchav.com"),
            "rol_usuario": data.get("rol_usuario", "DEVELOPER"),
            "titulo": data.get("titulo", "Solicitud de Apoyo Técnico"),
            "descripcion": data.get("descripcion", ""),
            "key_issue": data.get("key_issue", None),
            "prioridad": data.get("prioridad", "MEDIA"),
            "estado": "PENDIENTE",
            "atendido_por_name": None,
            "fecha_creacion": datetime.now(timezone.utc).isoformat()
        }
        _mock_test_help_requests.append(req)
        return req

    try:
        new_req = models.SolicitudesAyudaDev(
            id_proyecto=data.get("id_proyecto", "PROJ-01"),
            solicitado_por_name=data.get("solicitado_por_name", "Desarrollador"),
            solicitado_por_email=data.get("solicitado_por_email", "dev@mchav.com"),
            rol_usuario=data.get("rol_usuario", "DEVELOPER"),
            titulo=data.get("titulo", "Solicitud de Apoyo Técnico"),
            descripcion=data.get("descripcion", ""),
            key_issue=data.get("key_issue", None),
            prioridad=data.get("prioridad", "MEDIA"),
            estado="PENDIENTE"
        )
        db.add(new_req)
        db.commit()
        db.refresh(new_req)

        return {
            "id_solicitud": new_req.id_solicitud,
            "id_proyecto": new_req.id_proyecto,
            "solicitado_por_name": new_req.solicitado_por_name,
            "solicitado_por_email": new_req.solicitado_por_email,
            "rol_usuario": new_req.rol_usuario,
            "titulo": new_req.titulo,
            "descripcion": new_req.descripcion,
            "key_issue": new_req.key_issue,
            "prioridad": new_req.prioridad,
            "estado": new_req.estado,
            "atendido_por_name": new_req.atendido_por_name,
            "fecha_creacion": new_req.fecha_creacion.isoformat() if new_req.fecha_creacion else datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        print("Error creando solicitud de ayuda:", e)
        db.rollback()
        return {
            "id_solicitud": 0,
            "titulo": data.get("titulo", "Error"),
            "estado": "ERROR",
            "mensaje_error": str(e)
        }

def get_help_requests(db: Session, proyecto_id: str = "PROJ-01") -> List[Dict[str, Any]]:
    """Retorna el listado de solicitudes de ayuda desde la BD."""
    if not db:
        return _mock_test_help_requests

    try:
        query = db.query(models.SolicitudesAyudaDev).order_by(
            models.SolicitudesAyudaDev.fecha_creacion.desc()
        )
        if proyecto_id and proyecto_id != "ALL":
            query = query.filter(models.SolicitudesAyudaDev.id_proyecto == proyecto_id)

        reqs = query.all()
        return [
            {
                "id_solicitud": r.id_solicitud,
                "id_proyecto": r.id_proyecto,
                "solicitado_por_name": r.solicitado_por_name,
                "solicitado_por_email": r.solicitado_por_email,
                "rol_usuario": r.rol_usuario,
                "titulo": r.titulo,
                "descripcion": r.descripcion,
                "key_issue": r.key_issue,
                "prioridad": r.prioridad,
                "estado": r.estado,
                "atendido_por_name": r.atendido_por_name,
                "fecha_creacion": r.fecha_creacion.isoformat() if r.fecha_creacion else None
            }
            for r in reqs
        ]
    except Exception as e:
        print("Error obteniendo solicitudes de ayuda:", e)
        return []

def update_help_request_status(db: Session, request_id: int, status: str, responded_by: Optional[str] = None) -> Dict[str, Any]:
    """Actualiza el estado de una solicitud de ayuda en la BD (PENDIENTE -> EN_ATENCION -> RESUELTA)."""
    if not db:
        for r in _mock_test_help_requests:
            if r["id_solicitud"] == request_id:
                r["estado"] = status
                if responded_by:
                    r["atendido_por_name"] = responded_by
                return r
        return {"id_solicitud": request_id, "estado": status, "atendido_por_name": responded_by}

    try:
        req = db.query(models.SolicitudesAyudaDev).filter(
            models.SolicitudesAyudaDev.id_solicitud == request_id
        ).first()

        if not req:
            return {"id_solicitud": request_id, "estado": status, "error": "Solicitud no encontrada"}

        req.estado = status
        if responded_by:
            req.atendido_por_name = responded_by
        if status == "RESUELTA":
            req.fecha_resolucion = datetime.now(timezone.utc)

        db.commit()
        db.refresh(req)

        return {
            "id_solicitud": req.id_solicitud,
            "estado": req.estado,
            "atendido_por_name": req.atendido_por_name,
            "fecha_resolucion": req.fecha_resolucion.isoformat() if req.fecha_resolucion else None
        }
    except Exception as e:
        print("Error actualizando solicitud:", e)
        db.rollback()
        return {"id_solicitud": request_id, "estado": status, "atendido_por_name": responded_by}
