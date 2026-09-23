# tests/test_paso1_normalizacion_y_permisos.py
# Pruebas automatizadas para el Paso 1: Normalización bilingüe de Jira y Permisos RBAC

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.models.auth import User, Role
from app.api.v1.controllers.users_controller import _verify_admin, _verify_management_or_admin
from app.services.jira_normalizer import (
    normalize_status,
    is_done,
    is_in_progress,
    is_todo,
    categorize_flow_state,
    normalize_issue_type,
    is_bug,
    DONE_STATUSES,
    IN_PROGRESS_STATUSES,
    BUG_TYPES
)

# ==========================================
# 1. PRUEBAS DE PERMISOS RBAC (USERS_CONTROLLER)
# ==========================================

def test_verify_admin_permite_solo_administrador():
    """_verify_admin debe permitir únicamente al Administrador y rechazar otros roles."""
    admin_user = User(id_usuario=1, email="admin@mchav.com", rol=Role(nombre_rol="Administrador"))
    # No debe levantar excepción
    _verify_admin(admin_user)

    for rol in ["Manager", "Planificador", "Líder Técnico", "Desarrollador", "Desactivado"]:
        other_user = User(id_usuario=2, email="user@mchav.com", rol=Role(nombre_rol=rol))
        with pytest.raises(HTTPException) as excinfo:
            _verify_admin(other_user)
        assert excinfo.value.status_code == 403
        assert "únicamente para administradores" in excinfo.value.detail


def test_verify_management_or_admin_permite_roles_de_gestion():
    """_verify_management_or_admin debe permitir Administrador, Manager, Planificador y Líder Técnico."""
    allowed_roles = ["Administrador", "Manager", "Planificador", "Líder Técnico", "Lider Tecnico", "admin"]
    for rol in allowed_roles:
        user = User(id_usuario=10, email=f"{rol.lower()}@mchav.com", rol=Role(nombre_rol=rol))
        # No debe levantar excepción
        _verify_management_or_admin(user)


def test_verify_management_or_admin_rechaza_roles_no_gestion():
    """_verify_management_or_admin debe rechazar Desarrollador, Desactivado o usuarios sin rol."""
    disallowed_roles = ["Desarrollador", "Developer", "Desactivado", "Guest", "Auditor"]
    for rol in disallowed_roles:
        user = User(id_usuario=20, email="dev@mchav.com", rol=Role(nombre_rol=rol))
        with pytest.raises(HTTPException) as excinfo:
            _verify_management_or_admin(user)
        assert excinfo.value.status_code == 403
        assert "roles de gestión o administradores" in excinfo.value.detail

    # Usuario sin rol asignado
    user_no_role = User(id_usuario=21, email="norole@mchav.com", rol=None)
    with pytest.raises(HTTPException) as excinfo:
        _verify_management_or_admin(user_no_role)
    assert excinfo.value.status_code == 403


# ==========================================
# 2. PRUEBAS DE NORMALIZACIÓN BILINGÜE JIRA
# ==========================================

def test_normalizacion_estados_done():
    """Verifica que estados terminales en inglés y español normalicen a DONE."""
    done_examples = [
        "Done", "done", "DONE",
        "Finalizado", "finalizado", "FINALIZADO",
        "Listo", "listo", "LISTO",
        "Cerrado", "cerrado", "Resolved", "resuelto",
        "Completado", "completado"
    ]
    for st in done_examples:
        assert normalize_status(st) == "DONE", f"Fallo al normalizar {st}"
        assert is_done(st) is True, f"is_done fallo para {st}"
        assert is_in_progress(st) is False
        assert is_todo(st) is False


def test_normalizacion_estados_in_progress():
    """Verifica que estados de desarrollo activo en inglés y español normalicen a IN_PROGRESS."""
    in_prog_examples = [
        "In Progress", "in progress", "IN PROGRESS",
        "En curso", "en curso", "EN CURSO",
        "En progreso", "en progreso",
        "Desarrollo", "En desarrollo", "doing", "active",
        "En revisión", "in review", "qa", "en pruebas"
    ]
    for st in in_prog_examples:
        assert normalize_status(st) == "IN_PROGRESS", f"Fallo al normalizar {st}"
        assert is_in_progress(st) is True, f"is_in_progress fallo para {st}"
        assert is_done(st) is False
        assert is_todo(st) is False


def test_normalizacion_estados_todo():
    """Verifica que estados iniciales en inglés y español normalicen a TODO."""
    todo_examples = [
        "To Do", "to do", "TO DO",
        "Por hacer", "por hacer", "POR HACER",
        "Backlog", "abierto", "open", "nuevo"
    ]
    for st in todo_examples:
        assert normalize_status(st) == "TODO", f"Fallo al normalizar {st}"
        assert is_todo(st) is True, f"is_todo fallo para {st}"
        assert is_done(st) is False
        assert is_in_progress(st) is False


def test_categorize_flow_state():
    """
    Verifica categorización de flujo (Flow Analytics / CFD):
    'Listo' y 'Finalizado' DEBEN ser 'DONE', 'En curso' 'ACTIVE', 'En revisión' 'WAITING', 'Bloqueado' 'BLOCKED'.
    """
    assert categorize_flow_state("Listo") == "DONE"
    assert categorize_flow_state("Finalizado") == "DONE"
    assert categorize_flow_state("Done") == "DONE"

    assert categorize_flow_state("En curso") == "ACTIVE"
    assert categorize_flow_state("In Progress") == "ACTIVE"
    assert categorize_flow_state("Desarrollo") == "ACTIVE"

    assert categorize_flow_state("En revisión") == "WAITING"
    assert categorize_flow_state("In Review") == "WAITING"
    assert categorize_flow_state("QA") == "WAITING"

    assert categorize_flow_state("Bloqueado") == "BLOCKED"
    assert categorize_flow_state("Blocked") == "BLOCKED"
    assert categorize_flow_state("Impediment") == "BLOCKED"


def test_normalizacion_tipos_incidencia_y_bugs():
    """Verifica normalización de tipos de Jira y detección de bugs ('Error' / 'Bug')."""
    assert normalize_issue_type("Error") == "BUG"
    assert normalize_issue_type("Bug") == "BUG"
    assert normalize_issue_type("Defecto") == "BUG"
    assert is_bug("Error") is True
    assert is_bug("Bug") is True
    assert is_bug("Story", summary="[BUG] Error en login") is True

    assert normalize_issue_type("Story") == "STORY"
    assert normalize_issue_type("Historia") == "STORY"
    assert normalize_issue_type("Tarea") == "TASK"
    assert normalize_issue_type("Task") == "TASK"
    assert normalize_issue_type("Epic") == "EPIC"
    assert normalize_issue_type("Subtask") == "SUBTASK"
