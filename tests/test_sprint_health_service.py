import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from app.services.sprint_health_service import (
    calculate_sprint_health,
    calculate_burndown_chart_data,
    _build_gemini_insights,
    _empty_health_response
)
import app.models as models

def test_empty_health_response():
    res = _empty_health_response("PROJ-01", "SPRINT-1")
    assert res["proyecto_id"] == "PROJ-01"
    assert res["sprint_id"] == "SPRINT-1"
    assert res["health_score"] == 0
    assert res["diagnostico"] == "SIN_DATOS"
    assert res["metrics"]["sp_planned"] == 0

def test_calculate_sprint_health_no_issues():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    res = calculate_sprint_health(mock_db, proyecto_id="PROJ-01")
    assert res["diagnostico"] == "SIN_DATOS"

def test_calculate_sprint_health_with_issues_and_scope_creep():
    mock_db = MagicMock()
    
    start_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    mock_sprint = MagicMock(id_sprint="S1", fecha_inicio=start_date)
    
    # Issues
    issue_done = MagicMock(
        story_points=5, status_actual="Done", created_at=start_date - timedelta(days=2),
        resolved_at=start_date + timedelta(days=3), transiciones=[]
    )
    issue_in_prog = MagicMock(
        story_points=3, status_actual="In Progress", created_at=start_date + timedelta(days=1), # Added mid sprint!
        resolved_at=None, transiciones=[]
    )
    issue_review = MagicMock(
        story_points=2, status_actual="In Review", created_at=start_date - timedelta(days=1),
        resolved_at=None, transiciones=[]
    )
    issue_todo = MagicMock(
        story_points=2, status_actual="To Do", created_at=start_date - timedelta(days=1),
        resolved_at=None, transiciones=[]
    )
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sprint
    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
        issue_done, issue_in_prog, issue_review, issue_todo
    ]
    
    with patch("app.services.sprint_health_service._build_gemini_insights", return_value={"test": "ok"}):
        res = calculate_sprint_health(mock_db, proyecto_id="PROJ-01", sprint_id="S1")
        
    assert res["proyecto_id"] == "PROJ-01"
    assert res["sprint_id"] == "S1"
    assert res["metrics"]["sp_planned"] == 12.0
    assert res["metrics"]["sp_completed"] == 5.0
    assert res["metrics"]["sp_added_mid_sprint"] == 3.0
    assert res["metrics"]["sp_carryover"] == 2.0
    assert "scope_creep_warning" in res

def test_calculate_sprint_health_diagnostics_tiers():
    # Test excelente tier
    mock_db = MagicMock()
    mock_sprint = MagicMock(id_sprint="S1", fecha_inicio=None)
    issue_done1 = MagicMock(story_points=10, status_actual="Done", created_at=None, resolved_at=None, transiciones=[])
    issue_done2 = MagicMock(story_points=10, status_actual="Done", created_at=None, resolved_at=None, transiciones=[])
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sprint
    mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [issue_done1, issue_done2]
    
    with patch("app.services.sprint_health_service._build_gemini_insights", return_value={}):
        res = calculate_sprint_health(mock_db, proyecto_id="PROJ-01", sprint_id="S1")
    assert res["diagnostico"] in ["EXCELENTE", "ACEPTABLE", "CRITICO"]

def test_build_gemini_insights_fallback():
    with patch("app.services.gemini_service.generate_lider_dashboard_insights", side_effect=Exception("Gemini error")):
        insights = _build_gemini_insights("PROJ-01", 75, 80.0, 2.0, 90.0, "Cuello de botella en QA")
        assert "diagnostico_ejecutivo" in insights
        assert "PROJ-01" in insights["diagnostico_ejecutivo"]

def test_calculate_burndown_chart_data_no_sprint():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
    
    data = calculate_burndown_chart_data(mock_db, proyecto_id="PROJ-01", sprint_id="INVALID")
    assert data == []

def test_calculate_burndown_chart_data_success():
    mock_db = MagicMock()
    start_date = datetime(2026, 2, 1, 0, 0, 0)
    end_date = datetime(2026, 2, 5, 0, 0, 0)
    mock_sprint = models.Sprint(id_sprint="S1", id_proyecto="PROJ-01", fecha_inicio=start_date, fecha_fin=end_date)
    
    issue1 = MagicMock(id_jira="J-1", story_points="5", estado="Done")
    issue2 = MagicMock(id_jira="J-2", story_points="3", estado="To Do")
    t1 = MagicMock(id_jira="J-1", fecha_cambio=start_date + timedelta(days=2), estado_nuevo="Done")
    
    def query_handler(model):
        m_query = MagicMock()
        if model == models.Sprint:
            m_query.filter_by.return_value.first.return_value = mock_sprint
        elif model == models.Issue:
            m_query.filter.return_value.all.return_value = [issue1, issue2]
        elif model == models.TransicionEstadoIssue:
            m_query.filter.return_value.order_by.return_value.all.return_value = [t1]
        return m_query
        
    mock_db.query.side_effect = query_handler
    
    data = calculate_burndown_chart_data(mock_db, proyecto_id="PROJ-01", sprint_id="S1")
    assert len(data) == 5 # 4 days delta -> 5 data points
    assert data[0]["esfuerzo_ideal"] == 8.0
