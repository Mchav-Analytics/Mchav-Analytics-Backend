# tests/test_paso2_alertas_y_proyectos.py
# Pruebas automatizadas para el Paso 2: Motor de Alertas Inteligentes, Detección de Inactividad y Fallback de Proyectos

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.models.jira import Issue, TransicionEstadoIssue, Proyecto
from app.models.alerts import AlertasSistema
from app.services.project_resolver import resolve_project_id
from app.services.alerts_engine_service import (
    get_issue_active_days,
    scan_and_generate_alerts,
    get_system_alerts,
    acknowledge_alert
)

# ==========================================
# 1. PRUEBAS DE RESOLUCIÓN DE PROYECTO
# ==========================================

def test_resolve_project_id_fallback_proj01():
    """resolve_project_id debe resolver 'PROJ-01' o vacío al primer proyecto real de la BD."""
    mock_db = MagicMock()
    mock_project = Proyecto(id_proyecto="10000", key_proyecto="SCRUM", nombre="MCHAV ANALYTICS")
    mock_db.query().filter().first.return_value = None  # PROJ-01 no existe
    mock_db.query().order_by().first.return_value = mock_project

    # Caso 1: PROJ-01 debe resolverse a 10000
    resolved = resolve_project_id(mock_db, "PROJ-01")
    assert resolved == "10000"

    # Caso 2: None debe resolverse a 10000
    resolved_none = resolve_project_id(mock_db, None)
    assert resolved_none == "10000"

    # Caso 3: "ALL" debe preservarse
    resolved_all = resolve_project_id(mock_db, "ALL")
    assert resolved_all == "ALL"


def test_resolve_project_id_clave_o_id_existente():
    """resolve_project_id debe encontrar el id_proyecto si se pasa la clave ('PA' -> '10033')."""
    mock_db = MagicMock()
    mock_project_pa = Proyecto(id_proyecto="10033", key_proyecto="PA", nombre="Prueba ASD")
    mock_db.query().filter().first.return_value = mock_project_pa

    resolved = resolve_project_id(mock_db, "PA")
    assert resolved == "10033"

    resolved_id = resolve_project_id(mock_db, "10033")
    assert resolved_id == "10033"


# ==========================================
# 2. PRUEBAS DE CÁLCULO DE TIEMPO ACTIVO (BUG RESOLVED_AT)
# ==========================================

def test_get_issue_active_days_tarea_en_progreso():
    """
    Una tarea no resuelta (resolved_at=None) debe medir los días transcurridos
    desde su última transición o creación.
    """
    now = datetime.now(timezone.utc)
    five_days_ago = now - timedelta(days=5, hours=2)

    # Issue con transición hace 5 días
    transition = TransicionEstadoIssue(
        id_transicion=1,
        id_jira="JIRA-1",
        estado_anterior="To Do",
        estado_nuevo="En curso",
        fecha_cambio=five_days_ago
    )
    issue = Issue(
        id_jira="JIRA-1",
        key_issue="MCHAV-10",
        id_proyecto="10000",
        summary="Desarrollo de feature",
        status_actual="En curso",
        created_at=five_days_ago,
        resolved_at=None,
        transiciones=[transition]
    )

    active_days = get_issue_active_days(issue)
    assert 4.9 <= active_days <= 5.2, f"Esperado ~5.0 días, obtenido {active_days}"


def test_get_issue_active_days_tarea_resuelta_retorna_cero():
    """Una tarea resuelta (resolved_at no nulo) debe retornar 0.0 días activos."""
    now = datetime.now(timezone.utc)
    issue_done = Issue(
        id_jira="JIRA-2",
        key_issue="MCHAV-11",
        id_proyecto="10000",
        summary="Feature terminada",
        status_actual="Finalizado",
        created_at=now - timedelta(days=10),
        resolved_at=now - timedelta(days=2),
        transiciones=[]
    )
    assert get_issue_active_days(issue_done) == 0.0


# ==========================================
# 3. PRUEBAS DEL MOTOR DE ALERTAS REALES
# ==========================================

def test_scan_and_generate_alerts_detecta_bloqueo_48h():
    """scan_and_generate_alerts debe detectar tareas activas en progreso >48h como BLOCK_48H."""
    now = datetime.now(timezone.utc)
    three_days_ago = now - timedelta(days=3)

    issue_blocked = Issue(
        id_jira="JIRA-100",
        key_issue="SCRUM-99",
        id_proyecto="10000",
        summary="Tarea bloqueada en desarrollo",
        status_actual="En curso",
        assignee_name="Carlos Dev",
        created_at=three_days_ago,
        resolved_at=None,
        transiciones=[
            TransicionEstadoIssue(
                id_transicion=1,
                id_jira="JIRA-100",
                estado_anterior="Por hacer",
                estado_nuevo="En curso",
                fecha_cambio=three_days_ago
            )
        ]
    )

    mock_db = MagicMock()
    mock_db.query().filter().all.return_value = [issue_blocked]
    # Simular que el resolver retorna '10000'
    mock_db.query().filter().first.return_value = Proyecto(id_proyecto="10000", key_proyecto="SCRUM")

    alerts = scan_and_generate_alerts(mock_db, "10000")
    assert len(alerts) >= 1

    block_alert = next((a for a in alerts if a["tipo_alerta"] == "BLOCK_48H"), None)
    assert block_alert is not None
    assert block_alert["key_issue"] == "SCRUM-99"
    assert block_alert["severidad"] == "HIGH"
    assert block_alert["assignee_name"] == "Carlos Dev"
    assert "días en estado 'En curso' sin resolución" in block_alert["mensaje"]


def test_scan_and_generate_alerts_detecta_wip_excesivo():
    """scan_and_generate_alerts debe generar WIP_EXCESSIVE si un desarrollador tiene >= 3 tareas activas."""
    now = datetime.now(timezone.utc)
    mock_issues = []
    for i in range(4):
        mock_issues.append(
            Issue(
                id_jira=f"JIRA-{i}",
                key_issue=f"SCRUM-{i}",
                id_proyecto="10000",
                summary=f"Tarea activa {i}",
                status_actual="En curso",
                assignee_name="Ana Dev",
                created_at=now - timedelta(hours=10),
                resolved_at=None,
                transiciones=[]
            )
        )

    mock_db = MagicMock()
    mock_db.query().filter().all.return_value = mock_issues
    mock_db.query().filter().first.return_value = Proyecto(id_proyecto="10000", key_proyecto="SCRUM")

    alerts = scan_and_generate_alerts(mock_db, "10000")
    wip_alert = next((a for a in alerts if a["tipo_alerta"] == "WIP_EXCESSIVE"), None)
    assert wip_alert is not None
    assert wip_alert["assignee_name"] == "Ana Dev"
    assert wip_alert["severidad"] == "HIGH"
    assert "4 tareas activas simultáneamente" in wip_alert["mensaje"]


def test_acknowledge_alert_actualiza_bd():
    """acknowledge_alert debe marcar atendida=True y fecha_atencion en la BD."""
    mock_alert = AlertasSistema(id_alerta=5, id_proyecto="10000", atendida=False)
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = mock_alert

    res = acknowledge_alert(mock_db, 5)
    assert res["atendida"] is True
    assert mock_alert.atendida is True
    assert mock_alert.fecha_atencion is not None
    mock_db.commit.assert_called_once()
