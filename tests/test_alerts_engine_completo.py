import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.services.alerts_engine_service import (
    get_issue_active_days,
    scan_and_generate_alerts,
    get_system_alerts,
    acknowledge_alert,
    create_help_request,
    get_help_requests,
    update_help_request_status
)
import app.models as models

def test_get_issue_active_days():
    now = datetime.now(timezone.utc)
    
    # 1. Resolved issue -> 0.0
    resolved_issue = MagicMock()
    resolved_issue.resolved_at = now
    assert get_issue_active_days(resolved_issue) == 0.0

    # 2. Issue with transitions
    t1 = MagicMock()
    t1.fecha_cambio = now - timedelta(days=3)
    issue_trans = MagicMock()
    issue_trans.resolved_at = None
    issue_trans.transiciones = [t1]
    days = get_issue_active_days(issue_trans)
    assert days >= 2.9

    # 3. Issue without transitions, only created_at
    issue_created = MagicMock()
    issue_created.resolved_at = None
    issue_created.transiciones = []
    issue_created.created_at = now - timedelta(days=1)
    days_created = get_issue_active_days(issue_created)
    assert days_created >= 0.9

def test_scan_and_generate_alerts():
    # None db
    assert scan_and_generate_alerts(None) == []

    mock_db = MagicMock()
    now = datetime.now(timezone.utc)

    # In progress issue > 48h
    i1 = MagicMock()
    i1.key_issue = "TASK-1"
    i1.summary = "Fix auth"
    i1.status_actual = "En progreso"
    i1.assignee_name = "Dev Juan"
    i1.resolved_at = None
    i1.created_at = now - timedelta(days=4)
    i1.transiciones = []

    # WIP excessive (> 3 tasks)
    i2 = MagicMock()
    i2.key_issue = "TASK-2"
    i2.summary = "Fix UI"
    i2.status_actual = "In Progress"
    i2.assignee_name = "Dev Juan"
    i2.resolved_at = None
    i2.created_at = now - timedelta(days=1)
    i2.transiciones = []

    i3 = MagicMock()
    i3.key_issue = "TASK-3"
    i3.summary = "API docs"
    i3.status_actual = "Doing"
    i3.assignee_name = "Dev Juan"
    i3.resolved_at = None
    i3.created_at = now - timedelta(days=1)
    i3.transiciones = []

    i4 = MagicMock()
    i4.key_issue = "TASK-4"
    i4.summary = "Tests"
    i4.status_actual = "Desarrollo"
    i4.assignee_name = "Dev Juan"
    i4.resolved_at = None
    i4.created_at = now - timedelta(days=1)
    i4.transiciones = []

    mock_db.query.return_value.filter.return_value.all.return_value = [i1, i2, i3, i4]

    with patch("app.services.alerts_engine_service.resolve_project_id", return_value="PROJ-01"), \
         patch("app.services.alerts_engine_service.is_in_progress", return_value=True):
        alerts = scan_and_generate_alerts(mock_db, "PROJ-01")
        assert len(alerts) >= 2
        types = [a["tipo_alerta"] for a in alerts]
        assert "BLOCK_48H" in types
        assert "WIP_EXCESSIVE" in types

def test_get_system_alerts_and_acknowledge():
    mock_db = MagicMock()
    alert_orm = MagicMock()
    alert_orm.id_alerta = 1
    alert_orm.id_proyecto = "PROJ-01"
    alert_orm.tipo_alerta = "BLOCK_48H"
    alert_orm.severidad = "HIGH"
    alert_orm.key_issue = "TASK-1"
    alert_orm.assignee_name = "Dev Juan"
    alert_orm.mensaje = "Bloqueo"
    alert_orm.recomendacion = "Revisar"
    alert_orm.atendida = False
    alert_orm.fecha_creacion = datetime.now(timezone.utc)
    alert_orm.fecha_atencion = None

    mock_db.query.return_value.filter.return_value.all.return_value = [alert_orm]
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [alert_orm]
    mock_db.query.return_value.filter.return_value.first.return_value = alert_orm

    with patch("app.services.alerts_engine_service.resolve_project_id", return_value="PROJ-01"), \
         patch("app.services.alerts_engine_service.scan_and_generate_alerts", return_value=[]):
        res = get_system_alerts(mock_db, "PROJ-01")
        assert len(res) == 1
        assert res[0]["id_alerta"] == 1

        ack = acknowledge_alert(mock_db, 1)
        assert ack["atendida"] is True
        assert alert_orm.atendida is True

def test_help_requests_crud():
    # Without db (mock storage)
    data = {
        "id_proyecto": "PROJ-01",
        "solicitado_por_name": "Dev Pedro",
        "titulo": "Ayuda con despliegue",
        "descripcion": "Fallo en build",
        "prioridad": "ALTA"
    }
    req = create_help_request(None, data)
    assert req["titulo"] == "Ayuda con despliegue"

    reqs = get_help_requests(None, "PROJ-01")
    assert len(reqs) >= 1

    upd = update_help_request_status(None, req["id_solicitud"], "EN_PROCESO", "Lider Maria")
    assert upd["estado"] == "EN_PROCESO"

    # With DB
    mock_db = MagicMock()
    req_orm = MagicMock()
    req_orm.id_solicitud = 99
    req_orm.id_proyecto = "PROJ-01"
    req_orm.solicitado_por_name = "Dev Pedro"
    req_orm.solicitado_por_email = "pedro@test.com"
    req_orm.rol_usuario = "DEVELOPER"
    req_orm.titulo = "Ayuda DB"
    req_orm.descripcion = "Timeout"
    req_orm.key_issue = "TASK-5"
    req_orm.prioridad = "ALTA"
    req_orm.estado = "PENDIENTE"
    req_orm.atendido_por_name = None
    req_orm.fecha_creacion = datetime.now(timezone.utc)
    req_orm.fecha_atencion = None

    mock_db.query.return_value.order_by.return_value.filter.return_value.all.return_value = [req_orm]
    mock_db.query.return_value.filter.return_value.first.return_value = req_orm

    with patch("app.services.alerts_engine_service.resolve_project_id", return_value="PROJ-01"):
        created = create_help_request(mock_db, data)
        assert mock_db.add.called
        assert mock_db.commit.called

        fetched = get_help_requests(mock_db, "PROJ-01")
        assert len(fetched) == 1

        updated = update_help_request_status(mock_db, 99, "RESUELTA", "Lider Ana")
        assert updated["estado"] == "RESUELTA"
