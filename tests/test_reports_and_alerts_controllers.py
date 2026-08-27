import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.api.v1.controllers.reports_controller import download_pdf_report, get_historical_report
from app.api.v1.controllers.alerts_controller import (
    list_system_alerts,
    mark_alert_acknowledged,
    list_help_requests,
    submit_help_request,
    update_help_status
)

@pytest.mark.asyncio
async def test_download_pdf_report_success_and_error():
    mock_db = MagicMock()
    mock_req = MagicMock()

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists", return_value=MagicMock(nombre="Admin")), \
         patch("app.api.v1.controllers.reports_controller.generate_pdf_report_bytes", return_value=b"%PDF-1.4 test"):
        response = await download_pdf_report(mock_req, "P1", mock_db)
        assert response.media_type == "application/pdf"
        assert b"%PDF-1.4" in response.body

    # Error handling
    with patch("app.api.v1.deps.get_current_user_id", side_effect=Exception("PDF failed")), \
         patch("app.api.v1.controllers.reports_controller.generate_pdf_report_bytes", side_effect=Exception("Generation error")):
        with pytest.raises(HTTPException) as exc:
            await download_pdf_report(mock_req, "P1", mock_db)
        assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_get_historical_report():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    jira_issue = MagicMock(id_jira="J1", story_points=5.0)
    mock_db.query.return_value.filter.return_value.all.return_value = [jira_issue]
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    rep = await get_historical_report(mock_req, "P1", "2026-01", mock_db)
    assert rep["month"] == "2026-01"
    assert rep["totalIssues"] == 1
    assert rep["pointsCompleted"] == 5.0

@pytest.mark.asyncio
async def test_alerts_controller_endpoints():
    mock_db = MagicMock()

    # list_system_alerts
    with patch("app.api.v1.controllers.alerts_controller.get_system_alerts", return_value=[{"id": 1}]):
        alerts = await list_system_alerts("P1", mock_db)
        assert alerts == [{"id": 1}]

    # mark_alert_acknowledged
    with patch("app.api.v1.controllers.alerts_controller.acknowledge_alert", return_value={"atendida": True}):
        ack = await mark_alert_acknowledged(1, mock_db)
        assert ack["atendida"] is True

    # help requests
    with patch("app.api.v1.controllers.alerts_controller.get_help_requests", return_value=["req1"]):
        reqs = await list_help_requests("P1", mock_db)
        assert reqs == ["req1"]

    with patch("app.api.v1.controllers.alerts_controller.create_help_request", return_value={"id": 10}):
        new_req = await submit_help_request({"titulo": "Ayuda"}, mock_db)
        assert new_req == {"id": 10}

    with patch("app.api.v1.controllers.alerts_controller.update_help_request_status", return_value={"estado": "RESUELTA"}):
        upd = await update_help_status(10, "RESUELTA", "Lider", mock_db)
        assert upd["estado"] == "RESUELTA"

@pytest.mark.asyncio
async def test_alerts_controller_exception_fallbacks():
    mock_db = MagicMock()
    mock_db.rollback.side_effect = None

    with patch("app.api.v1.controllers.alerts_controller.get_system_alerts", side_effect=[Exception("Error"), [{"id": 1}]]):
        alerts_fb = await list_system_alerts("P1", mock_db)
        assert alerts_fb == [{"id": 1}]

    with patch("app.api.v1.controllers.alerts_controller.acknowledge_alert", side_effect=[Exception("Error"), {"atendida": True}]):
        ack_fb = await mark_alert_acknowledged(1, mock_db)
        assert ack_fb["atendida"] is True

    with patch("app.api.v1.controllers.alerts_controller.get_help_requests", side_effect=[Exception("Error"), ["req1"]]):
        reqs_fb = await list_help_requests("P1", mock_db)
        assert reqs_fb == ["req1"]

    with patch("app.api.v1.controllers.alerts_controller.create_help_request", side_effect=[Exception("Error"), {"id": 10}]):
        sub_fb = await submit_help_request({"titulo": "Ayuda"}, mock_db)
        assert sub_fb == {"id": 10}

    with patch("app.api.v1.controllers.alerts_controller.update_help_request_status", side_effect=[Exception("Error"), {"estado": "RESUELTA"}]):
        upd_fb = await update_help_status(10, "RESUELTA", "Lider", mock_db)
        assert upd_fb["estado"] == "RESUELTA"
