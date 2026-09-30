# app/services/alerts_engine_service.py
# Motor analítico de Alertas Inteligentes, Detección de Inactividad y Solicitudes de Ayuda (Fase 8)
# DATOS REALES: Escanea la BD de Jira para generar alertas. Persiste en BD y sincroniza estados.

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import app.models as models
from app.services.kpi import get_issue_cycle_time_days
from app.services.jira_normalizer import is_in_progress, IN_PROGRESS_STATUSES
from app.services.project_resolver import resolve_project_id

def get_issue_active_days(issue: models.Issue) -> float:
    """
    Calcula los días que lleva una tarea en progreso activo sin resolución.
    - Si tiene transiciones, mide desde la última transición (tiempo en estado actual).
    - Si no tiene transiciones, mide desde created_at.
    - Si ya está resuelta, retorna 0.0.
    """
    if issue.resolved_at:
        return 0.0

    now = datetime.now(timezone.utc)
    transitions = sorted(issue.transiciones, key=lambda t: t.fecha_cambio) if hasattr(issue, 'transiciones') and issue.transiciones else []
    if transitions:
        last_t = transitions[-1].fecha_cambio
        if last_t.tzinfo is None:
            last_t = last_t.replace(tzinfo=timezone.utc)
        return round(max(0.0, (now - last_t).total_seconds() / 86400.0), 1)

    if issue.created_at:
        c = issue.created_at
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        return round(max(0.0, (now - c).total_seconds() / 86400.0), 1)

    return 0.0

def scan_and_generate_alerts(db: Optional[Session], proyecto_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Escanea la base de datos REAL para detectar:
    - Bloqueos >48h (Tareas en progreso/revisión/QA activas por más de 2 días)
    - WIP Excesivo (Desarrolladores con más de 3 tareas activas en paralelo)
    - Desviación Severa de Cycle Time (Tareas que duplican el promedio del proyecto)
    Retorna la lista de alertas generadas.
    """
    alerts = []
    if not db:
        return alerts

    target_pid = resolve_project_id(db, proyecto_id)

    try:
        query = db.query(models.Issue)
        if target_pid and target_pid != "ALL":
            query = query.filter(models.Issue.id_proyecto == target_pid)
        issues = query.all()

        # Calcular cycle time promedio del proyecto para comparación
        resolved_cts = [get_issue_cycle_time_days(i) for i in issues if i.resolved_at and get_issue_cycle_time_days(i) > 0]
        avg_project_ct = (sum(resolved_cts) / len(resolved_cts)) if resolved_cts else 3.0

        # 1. Detección de Bloqueos >48h y Cycle Time Deviation
        dev_wip = {}
        for issue in issues:
            st = (issue.status_actual or "").lower().strip()
            assignee = issue.assignee_name or "Desarrollador No Asignado"

            # Si la tarea está activa en progreso / desarrollo / revisión
            if is_in_progress(st, db, target_pid):
                dev_wip[assignee] = dev_wip.get(assignee, 0) + 1
                active_days = get_issue_active_days(issue)

                # Check >48h block (2.0 días)
                if active_days > 2.0:
                    severity = "HIGH" if any(k in st for k in ("curs", "progres", "desarr", "doing", "active")) else "MEDIUM"
                    msg = f"La incidencia {issue.key_issue} ('{issue.summary}') lleva {active_days} días en estado '{issue.status_actual}' sin resolución."
                    rec = f"Contactar a {assignee} para verificar si requiere apoyo técnico o desbloqueo de credenciales/dependencias."

                    alerts.append({
                        "id_alerta": len(alerts) + 1,
                        "id_proyecto": target_pid,
                        "tipo_alerta": "BLOCK_48H",
                        "severidad": severity,
                        "key_issue": issue.key_issue,
                        "assignee_name": assignee,
                        "mensaje": msg,
                        "recomendacion": rec,
                        "atendida": False,
                        "fecha_creacion": datetime.now(timezone.utc).isoformat()
                    })

            # Check Cycle Time deviation para tickets resueltos
            if issue.resolved_at:
                ct = get_issue_cycle_time_days(issue)
                if ct > (avg_project_ct * 2) and ct > 3.0:
                    alerts.append({
                        "id_alerta": len(alerts) + 1,
                        "id_proyecto": target_pid,
                        "tipo_alerta": "CYCLE_TIME_DEV",
                        "severidad": "MEDIUM",
                        "key_issue": issue.key_issue,
                        "assignee_name": assignee,
                        "mensaje": f"El tiempo de ciclo de {issue.key_issue} ({round(ct, 1)}d) duplica el promedio histórico del proyecto ({round(avg_project_ct, 1)}d).",
                        "recomendacion": "Revisar si el ticket debe subdividirse en sub-tareas más pequeñas.",
                        "atendida": False,
                        "fecha_creacion": datetime.now(timezone.utc).isoformat()
                    })

        # 2. Detección de WIP Excesivo (>= 3 tareas simultáneas)
        for dev_name, count in dev_wip.items():
            if count >= 3 and dev_name != "Desarrollador No Asignado":
                alerts.append({
                    "id_alerta": len(alerts) + 1,
                    "id_proyecto": target_pid,
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

def get_system_alerts(db: Optional[Session], proyecto_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta las alertas del sistema escaneando datos reales y sincronizando con la tabla alertas_sistema."""
    if not db:
        return scan_and_generate_alerts(None, proyecto_id)

    target_pid = resolve_project_id(db, proyecto_id)
    generated = scan_and_generate_alerts(db, target_pid)

    try:
        # Sincronizar alertas en la tabla alertas_sistema para persistencia
        existing = db.query(models.AlertasSistema).filter(
            models.AlertasSistema.id_proyecto == target_pid
        ).all()
        existing_keys = {(a.tipo_alerta, a.key_issue, a.assignee_name): a for a in existing}

        for g in generated:
            key = (g["tipo_alerta"], g.get("key_issue"), g.get("assignee_name"))
            if key not in existing_keys:
                new_alert = models.AlertasSistema(
                    id_proyecto=target_pid,
                    tipo_alerta=g["tipo_alerta"],
                    severidad=g["severidad"],
                    key_issue=g.get("key_issue"),
                    assignee_name=g.get("assignee_name"),
                    mensaje=g["mensaje"],
                    recomendacion=g.get("recomendacion"),
                    atendida=False
                )
                db.add(new_alert)
                existing_keys[key] = new_alert
        db.commit()

        db_alerts = db.query(models.AlertasSistema).filter(
            models.AlertasSistema.id_proyecto == target_pid
        ).order_by(models.AlertasSistema.atendida.asc(), models.AlertasSistema.fecha_creacion.desc()).all()

        return [
            {
                "id_alerta": a.id_alerta,
                "id_proyecto": a.id_proyecto,
                "tipo_alerta": a.tipo_alerta,
                "severidad": a.severidad,
                "key_issue": a.key_issue,
                "assignee_name": a.assignee_name,
                "mensaje": a.mensaje,
                "recomendacion": a.recomendacion,
                "atendida": a.atendida,
                "fecha_creacion": a.fecha_creacion.isoformat() if a.fecha_creacion else None,
                "fecha_atencion": a.fecha_atencion.isoformat() if a.fecha_atencion else None
            }
            for a in db_alerts
        ]
    except Exception as e:
        print("Aviso: Error sincronizando alertas en BD:", e)
        db.rollback()
        return generated

def acknowledge_alert(db: Optional[Session], alert_id: int) -> Dict[str, Any]:
    """Marca una alerta como atendida en la base de datos."""
    if db:
        try:
            db_alert = db.query(models.AlertasSistema).filter(
                models.AlertasSistema.id_alerta == alert_id
            ).first()
            if db_alert:
                db_alert.atendida = True
                db_alert.fecha_atencion = datetime.now(timezone.utc)
                db.commit()
                return {"message": f"Alerta {alert_id} marcada como atendida exitosamente.", "alert_id": alert_id, "atendida": True}
        except Exception as e:
            print("Error actualizando alerta en BD:", e)
            db.rollback()

    return {"message": f"Alerta {alert_id} marcada como atendida exitosamente.", "alert_id": alert_id, "atendida": True}

# ============================================================================
# SOLICITUDES DE AYUDA (DEVS & LÍDERES TÉCNICOS) — PERSISTENCIA EN BD
# ============================================================================

_mock_test_help_requests = []

def create_help_request(db: Optional[Session], data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva solicitud de ayuda persistida en la BD."""
    target_pid = resolve_project_id(db, data.get("id_proyecto"))

    if not db:
        new_id = len(_mock_test_help_requests) + 1
        req = {
            "id_solicitud": new_id,
            "id_proyecto": target_pid,
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
            id_proyecto=target_pid,
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

def get_help_requests(db: Optional[Session], proyecto_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna el listado de solicitudes de ayuda desde la BD."""
    if not db:
        return _mock_test_help_requests

    target_pid = resolve_project_id(db, proyecto_id)

    try:
        query = db.query(models.SolicitudesAyudaDev).order_by(
            models.SolicitudesAyudaDev.fecha_creacion.desc()
        )
        if target_pid and target_pid != "ALL":
            query = query.filter(models.SolicitudesAyudaDev.id_proyecto == target_pid)

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

def update_help_request_status(db: Optional[Session], request_id: int, status: str, responded_by: Optional[str] = None) -> Dict[str, Any]:
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
