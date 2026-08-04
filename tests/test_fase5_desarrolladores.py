# tests/test_fase5_desarrolladores.py
# Pruebas unitarias automatizadas para la Fase 5: Assignee Tracking & Métricas Individuales por Desarrollador

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.dev_metrics_service import get_developer_scorecard_data, get_base_status

client = TestClient(app)

def test_get_base_status_mapping():
    """Valida que los nombres de estado en Jira se clasifiquen correctamente en categorías base."""
    assert get_base_status("In Progress") == "IN_PROGRESS"
    assert get_base_status("En Progreso") == "IN_PROGRESS"
    assert get_base_status("In Review") == "IN_PROGRESS"
    assert get_base_status("Done") == "DONE"
    assert get_base_status("Listo") == "DONE"
    assert get_base_status("To Do") == "TODO"

def test_get_developer_scorecard_structure():
    """Verifica que la consulta del scorecard por desarrollador retorne una estructura completa."""
    mock_db = MagicMock()
    mock_db.query().filter().all.return_value = []
    
    scorecard = get_developer_scorecard_data(mock_db, proyecto_id="PROJ-01", email_or_assignee_id="cgomez@mchav.com")
    
    assert "cycle_time_personal" in scorecard
    assert "wip_tickets" in scorecard
    assert "throughput_tickets" in scorecard
    assert "story_points_burned" in scorecard
    assert "work_distribution" in scorecard
    assert "assigned_issues" in scorecard
    
    assert scorecard["work_distribution"]["pct_historias"] >= 0
    assert scorecard["work_distribution"]["pct_bugs"] >= 0
    assert scorecard["work_distribution"]["pct_tareas"] >= 0
    assert len(scorecard["assigned_issues"]) >= 0

def test_developer_endpoints():
    """Verifica la respuesta de los nuevos endpoints REST API /api/v1/developers."""
    res_list = client.get("/api/v1/developers?proyecto_id=PROJ-01")
    assert res_list.status_code == 200
    devs = res_list.json()
    assert isinstance(devs, list)
    assert len(devs) > 0

    res_card = client.get("/api/v1/developers/DEV-101/scorecard?proyecto_id=PROJ-01")
    assert res_card.status_code == 200
    card_data = res_card.json()
    assert "cycle_time_personal" in card_data
    assert "wip_tickets" in card_data

def test_developer_subview_endpoints():
    """Valida los nuevos endpoints REST para sub-vistas del desarrollador."""
    res_focus = client.get("/api/v1/developers/me/daily-focus?proyecto_id=PROJ-01")
    assert res_focus.status_code == 200
    focus_data = res_focus.json()
    assert "ai_coach_tip" in focus_data
    assert "urgent_qa_bugs" in focus_data

    res_alerts = client.get("/api/v1/developers/me/alerts?proyecto_id=PROJ-01")
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()
    assert "alerts" in alerts_data

    res_action = client.post("/api/v1/developers/me/alerts/101/action?action_type=request_help")
    assert res_action.status_code == 200
    action_data = res_action.json()
    assert action_data["status"] == "SUCCESS"

    res_hist = client.get("/api/v1/developers/me/activity-history?proyecto_id=PROJ-01")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert "activity_feed" in hist_data
    assert "badges" in hist_data
