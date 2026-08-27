import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from app.services.alerts_engine_service import (
    scan_and_generate_alerts,
    get_system_alerts,
    acknowledge_alert,
    create_help_request,
    get_help_requests,
    update_help_request_status
)

def test_scan_and_generate_alerts_no_db():
    assert scan_and_generate_alerts(None, "PROJ-01") == []
    assert get_system_alerts(None, "PROJ-01") == []

def test_scan_and_generate_alerts_with_issues():
    mock_db = MagicMock()
    
    # 3 active issues for Dev A to trigger WIP_EXCESSIVE
    issue1 = MagicMock(key_issue="ISS-1", summary="Issue 1", status_actual="In Progress", assignee_name="Dev A", resolved_at=None, transiciones=[])
    issue2 = MagicMock(key_issue="ISS-2", summary="Issue 2", status_actual="In Progress", assignee_name="Dev A", resolved_at=None, transiciones=[])
    issue3 = MagicMock(key_issue="ISS-3", summary="Issue 3", status_actual="In Progress", assignee_name="Dev A", resolved_at=None, transiciones=[])
    
    # 1 issue with block > 48h (ct = 3.0 days)
    issue4 = MagicMock(key_issue="ISS-4", summary="Issue 4", status_actual="In Progress", assignee_name="Dev B", resolved_at=None, transiciones=[])
    
    mock_db.query.return_value.filter.return_value.all.return_value = [issue1, issue2, issue3, issue4]
    
    with patch("app.services.alerts_engine_service.get_issue_cycle_time_days", side_effect=[1.0, 1.0, 1.0, 3.0]):
        alerts = scan_and_generate_alerts(mock_db, "PROJ-01")
        
    assert len(alerts) >= 2 # BLOCK_48H and WIP_EXCESSIVE
    types = [a["tipo_alerta"] for a in alerts]
    assert "WIP_EXCESSIVE" in types
    assert "BLOCK_48H" in types

def test_acknowledge_alert():
    res = acknowledge_alert(MagicMock(), 5)
    assert res["atendida"] is True
    assert res["alert_id"] == 5

def test_create_help_request_no_db():
    data = {"titulo": "Necesito ayuda con DB", "solicitado_por_name": "Mike"}
    req = create_help_request(None, data)
    assert req["titulo"] == "Necesito ayuda con DB"
    assert req["estado"] == "PENDIENTE"

def test_create_help_request_with_db():
    mock_db = MagicMock()
    mock_req = MagicMock(
        id_solicitud=10, id_proyecto="P1", solicitado_por_name="Dev", solicitado_por_email="dev@test.com",
        rol_usuario="DEV", titulo="Ayuda", descripcion="Desc", key_issue="K1", prioridad="ALTA",
        estado="PENDIENTE", atendido_por_name=None, fecha_creacion=datetime.now(timezone.utc)
    )
    
    with patch("app.models.SolicitudesAyudaDev", return_value=mock_req):
        res = create_help_request(mock_db, {"titulo": "Ayuda"})
        
    assert res["id_solicitud"] == 10
    assert mock_db.commit.called

def test_create_help_request_exception():
    mock_db = MagicMock()
    mock_db.add.side_effect = Exception("DB error")
    res = create_help_request(mock_db, {"titulo": "Ayuda"})
    assert res["estado"] == "ERROR"

def test_get_help_requests():
    # No DB
    reqs_none = get_help_requests(None, "P1")
    assert isinstance(reqs_none, list)
    
    # DB with results
    mock_db = MagicMock()
    r1 = MagicMock(id_solicitud=1, id_proyecto="P1", solicitado_por_name="Dev", solicitado_por_email="a@b.com",
                   rol_usuario="DEV", titulo="T1", descripcion="D1", key_issue="K1", prioridad="MEDIA",
                   estado="PENDIENTE", atendido_por_name=None, fecha_creacion=None)
    mock_db.query.return_value.order_by.return_value.filter.return_value.all.return_value = [r1]
    
    reqs_db = get_help_requests(mock_db, "P1")
    assert len(reqs_db) == 1
    assert reqs_db[0]["id_solicitud"] == 1

def test_update_help_request_status():
    # No DB
    res_nodb = update_help_request_status(None, 1, "EN_ATENCION", "Lider")
    assert res_nodb["estado"] == "EN_ATENCION"
    
    # DB request found
    mock_db = MagicMock()
    mock_req = MagicMock(id_solicitud=2, estado="PENDIENTE", atendido_por_name=None, fecha_resolucion=None)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_req
    
    res_db = update_help_request_status(mock_db, 2, "RESUELTA", "Lider")
    assert res_db["estado"] == "RESUELTA"
    assert mock_db.commit.called
    
    # DB request not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    res_not_found = update_help_request_status(mock_db, 999, "RESUELTA")
    assert "error" in res_not_found
