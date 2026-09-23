# app/services/jira_normalizer.py
# Normalizador centralizado y bilingüe (Español/Inglés) de estados y tipos de incidencias de Jira.
# Garantiza consistencia en métricas, KPIs, Flow Analytics, reportes y filtros.

from typing import Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
import app.models as models

# --- CONJUNTOS CANÓNICOS DE ESTADOS (MINÚSCULAS) ---

DONE_STATUSES: Set[str] = {
    "done", "finalizado", "listo", "cerrado", "resuelto",
    "resolved", "closed", "completado", "finished", "completada", "terminado"
}

IN_PROGRESS_STATUSES: Set[str] = {
    "in progress", "en curso", "en progreso", "desarrollo", "in development",
    "doing", "active", "activo", "en desarrollo", "en revisión", "en revision",
    "in review", "en testing", "en pruebas", "testing", "qa", "pruebas",
    "code review", "revisión", "revision", "working", "trabajando"
}

ACTIVE_DEV_STATUSES: Set[str] = {
    "in progress", "en curso", "en progreso", "desarrollo", "in development",
    "doing", "active", "activo", "en desarrollo", "working", "trabajando"
}

WAITING_STATUSES: Set[str] = {
    "in review", "en revisión", "en revision", "revisión", "revision",
    "qa", "testing", "en testing", "en pruebas", "pruebas", "code review",
    "wait", "waiting", "en espera", "espera", "pendiente", "aprobación",
    "aprobacion", "ready for test", "ready for review"
}

BLOCKED_STATUSES: Set[str] = {
    "blocked", "bloqueado", "impediment", "impedido", "detenido", "block", "impedimento"
}

TODO_STATUSES: Set[str] = {
    "to do", "por hacer", "backlog", "abierto", "open", "nuevo", "new",
    "selected for development", "seleccionado para desarrollo", "to-do"
}

# --- CONJUNTOS CANÓNICOS DE TIPOS DE INCIDENCIA ---

BUG_TYPES: Set[str] = {
    "bug", "error", "defecto", "fallo", "incidencia"
}

STORY_TYPES: Set[str] = {
    "story", "historia", "historia de usuario", "user story"
}

TASK_TYPES: Set[str] = {
    "task", "tarea", "mejora", "improvement"
}

EPIC_TYPES: Set[str] = {
    "epic", "épica", "epica"
}

SUBTASK_TYPES: Set[str] = {
    "subtask", "sub-task", "subtarea", "sub-tarea"
}


def normalize_status(
    status_name: Optional[str],
    db: Optional[Session] = None,
    project_id: Optional[str] = None
) -> str:
    """
    Retorna la categoría base ('TODO', 'IN_PROGRESS', 'DONE') para un nombre de estado de Jira.
    1. Si existe mapeo explícito en MapeoEstado de la BD, lo respeta.
    2. Si no, aplica el diccionario bilingüe comprensivo.
    """
    if not status_name:
        return "TODO"

    cleaned = status_name.lower().strip()

    # 1. Consulta en BD si está disponible
    if db and project_id:
        try:
            mapping = db.query(models.MapeoEstado).filter(
                models.MapeoEstado.id_proyecto == project_id,
                func.lower(models.MapeoEstado.estado_jira) == cleaned
            ).first()
            if mapping and mapping.estado_base:
                return mapping.estado_base.upper()
        except Exception:
            pass

    # 2. Diccionario comprensivo
    if cleaned in DONE_STATUSES:
        return "DONE"
    if cleaned in IN_PROGRESS_STATUSES:
        return "IN_PROGRESS"
    if cleaned in TODO_STATUSES:
        return "TODO"

    # Verificación por subcadena para estados compuestos
    if any(k in cleaned for k in ("finaliz", "cerrad", "complet", "resolv", "terminad")):
        return "DONE"
    if any(k in cleaned for k in ("progres", "curs", "desarr", "doing", "activ")):
        return "IN_PROGRESS"
    if any(k in cleaned for k in ("hacer", "todo", "backlog", "abiert", "open")):
        return "TODO"

    return "TODO"


def is_done(
    status_name: Optional[str],
    db: Optional[Session] = None,
    project_id: Optional[str] = None
) -> bool:
    """Verifica si un estado corresponde a finalizado / completado."""
    return normalize_status(status_name, db, project_id) == "DONE"


def is_in_progress(
    status_name: Optional[str],
    db: Optional[Session] = None,
    project_id: Optional[str] = None
) -> bool:
    """Verifica si un estado corresponde a trabajo en progreso."""
    return normalize_status(status_name, db, project_id) == "IN_PROGRESS"


def is_todo(
    status_name: Optional[str],
    db: Optional[Session] = None,
    project_id: Optional[str] = None
) -> bool:
    """Verifica si un estado corresponde a pendiente / por hacer."""
    return normalize_status(status_name, db, project_id) == "TODO"


def categorize_flow_state(
    status_name: Optional[str],
    db: Optional[Session] = None,
    project_id: Optional[str] = None
) -> str:
    """
    Categoriza el estado para análisis de flujo (CFD, Flow Efficiency, Bottlenecks):
    Retorna uno de: 'ACTIVE', 'WAITING', 'BLOCKED', 'DONE'.
    Nota crítica: 'Listo' en Jira en español es DONE (columna final del tablero), NO WAITING.
    """
    if not status_name:
        return "WAITING"

    cleaned = status_name.lower().strip()

    # 1. Finalizado primero
    if cleaned in DONE_STATUSES or any(k in cleaned for k in ("finaliz", "cerrad", "complet", "resolv", "terminad")):
        return "DONE"

    # 2. Bloqueado
    if cleaned in BLOCKED_STATUSES or any(k in cleaned for k in ("block", "imped", "detenid")):
        return "BLOCKED"

    # 3. Desarrollo activo
    if cleaned in ACTIVE_DEV_STATUSES or any(k in cleaned for k in ("curs", "desarr", "doing", "working", "activ")):
        return "ACTIVE"

    # 4. En espera / Revisión / QA
    if cleaned in WAITING_STATUSES or any(k in cleaned for k in ("wait", "esper", "revis", "review", "qa", "test", "pendient")):
        return "WAITING"

    # Fallback con MapeoEstado si existe
    base = normalize_status(status_name, db, project_id)
    if base == "DONE":
        return "DONE"
    if base == "IN_PROGRESS":
        return "ACTIVE"

    return "WAITING"


def normalize_issue_type(issue_type_name: Optional[str]) -> str:
    """
    Normaliza el tipo de incidencia al estándar internacional en mayúsculas:
    'STORY', 'BUG', 'TASK', 'EPIC', 'SUBTASK'.
    """
    if not issue_type_name:
        return "STORY"

    cleaned = issue_type_name.lower().strip()
    if cleaned in BUG_TYPES or "error" in cleaned or "bug" in cleaned:
        return "BUG"
    if cleaned in STORY_TYPES or "historia" in cleaned or "story" in cleaned:
        return "STORY"
    if cleaned in EPIC_TYPES or "epic" in cleaned or "épica" in cleaned:
        return "EPIC"
    if cleaned in SUBTASK_TYPES or "sub" in cleaned:
        return "SUBTASK"
    if cleaned in TASK_TYPES or "tarea" in cleaned or "task" in cleaned:
        return "TASK"

    return cleaned.upper()


def is_bug(issue_type_name: Optional[str], summary: Optional[str] = None) -> bool:
    """Verifica si la tarea es un bug o defecto, evaluando tipo y summary."""
    if issue_type_name and normalize_issue_type(issue_type_name) == "BUG":
        return True
    if summary:
        s_lower = summary.lower()
        if any(w in s_lower for w in ("bug", "defecto", "error:", "[bug]", "[error]")):
            return True
    return False
