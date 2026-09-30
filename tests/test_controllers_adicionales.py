import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
import app.models as models

client = TestClient(app)

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id_usuario = 1
    user.nombre = "Admin Test"
    user.email = "admin@test.com"
    rol = MagicMock()
    rol.nombre_rol = "Líder Técnico"
    user.rol = rol
    return user

@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()

def test_alerts_controller_endpoints(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. GET /api/v1/alerts
    with patch("app.api.v1.controllers.alerts_controller.get_system_alerts", return_value=[{"id_alerta": 1, "tipo_alerta": "BLOCK_48H"}]):
        resp = client.get("/api/v1/alerts?proyecto_id=PROJ-01")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    # 2. POST /api/v1/alerts/1/acknowledge
    with patch("app.api.v1.controllers.alerts_controller.acknowledge_alert", return_value={"atendida": True}):
        resp = client.post("/api/v1/alerts/1/acknowledge")
        assert resp.status_code == 200
        assert resp.json()["atendida"] is True

    # 3. GET /api/v1/alerts/help-requests
    with patch("app.api.v1.controllers.alerts_controller.get_help_requests", return_value=[{"id_solicitud": 10}]):
        resp = client.get("/api/v1/alerts/help-requests?proyecto_id=PROJ-01")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    # 4. POST /api/v1/alerts/help-requests
    with patch("app.api.v1.controllers.alerts_controller.create_help_request", return_value={"id_solicitud": 11}):
        resp = client.post("/api/v1/alerts/help-requests", json={"titulo": "Ayuda"})
        assert resp.status_code == 200
        assert resp.json()["id_solicitud"] == 11

    # 5. PATCH /api/v1/alerts/help-requests/11
    with patch("app.api.v1.controllers.alerts_controller.update_help_request_status", return_value={"estado": "RESUELTA"}):
        resp = client.patch("/api/v1/alerts/help-requests/11?status=RESUELTA&responded_by=Lider")
        assert resp.status_code == 200
        assert resp.json()["estado"] == "RESUELTA"

def test_reports_controller_endpoints(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. GET /api/v1/reports/pdf
    with patch("app.api.v1.controllers.reports_controller.generate_pdf_report_bytes", return_value=b"%PDF-report-data"):
        resp = client.get("/api/v1/reports/pdf?proyecto_id=PROJ-01")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    # 2. GET /api/v1/reports/historical
    with patch("app.api.v1.controllers.reports_controller.resolve_project_id", return_value="PROJ-01"):
        mock_db.query.return_value.filter.return_value.all.return_value = []
        resp = client.get("/api/v1/reports/historical?proyecto_id=PROJ-01&month=2026-03")
        assert resp.status_code == 200
        assert "pointsCompleted" in resp.json()

    # 3. GET /api/v1/reports/historical/range
    resp = client.get("/api/v1/reports/historical/range?proyecto_id=PROJ-01&start_date=2026-01-01&end_date=2026-03-01")
    assert resp.status_code == 200
    assert "month" in resp.json()

    # 4. POST /api/v1/reports/send-monthly
    resp = client.post("/api/v1/reports/send-monthly?target_email=test@test.com")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_ai_controller_endpoints(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. GET /api/v1/ai/prompts
    resp = client.get("/api/v1/ai/prompts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 4

    # 2. POST /api/v1/ai/chat
    with patch("app.api.v1.controllers.ai_controller.chat_with_gemini", return_value="Respuesta de NubI AI"):
        resp = client.post("/api/v1/ai/chat", json={"message": "¿Cómo está el sprint?", "project_id": "PROJ-01"})
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Respuesta de NubI AI"

    # 3. POST /api/v1/ai/generate-report-insights
    with patch("app.api.v1.controllers.ai_controller.generate_report_insights", return_value="Insights simulados"):
        resp = client.post("/api/v1/ai/generate-report-insights", json={
            "reportType": "sprint",
            "velocity": 25.0,
            "cycleTime": 3.0
        })
        assert resp.status_code == 200
        assert resp.json()["data"] == "Insights simulados"

def test_flow_controller_endpoints(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.services.flow_service.calculate_cycle_time_percentiles", return_value={"p50": 2.0}), \
         patch("app.services.flow_service.calculate_flow_efficiency", return_value={"flow_efficiency_pct": 75.0}), \
         patch("app.services.flow_service.detect_bottlenecks", return_value=[]), \
         patch("app.services.flow_service.get_blockers", return_value=[]), \
         patch("app.services.flow_service.get_aging_work", return_value=[]), \
         patch("app.services.flow_service.calculate_cfd_and_wip", return_value={"cfd": []}):

        resp = client.get("/api/v1/flow/cycle-time?proyecto_id=PROJ-01")
        assert resp.status_code == 200

        resp = client.get("/api/v1/flow/efficiency?proyecto_id=PROJ-01")
        assert resp.status_code == 200

        resp = client.get("/api/v1/flow/bottlenecks?proyecto_id=PROJ-01")
        assert resp.status_code == 200

        resp = client.get("/api/v1/flow/blockers?proyecto_id=PROJ-01")
        assert resp.status_code == 200

        resp = client.get("/api/v1/flow/aging?proyecto_id=PROJ-01")
        assert resp.status_code == 200

        resp = client.get("/api/v1/flow/cfd-wip?proyecto_id=PROJ-01")
        assert resp.status_code == 200
