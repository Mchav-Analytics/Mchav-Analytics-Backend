import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from app.services.dev_metrics_service import (
    get_base_status,
    get_developer_scorecard_data,
    get_daily_focus_data,
    get_developer_alerts_data,
    perform_alert_action,
    get_activity_history_data,
    _format_transition_time
)
import app.models as models

def test_get_base_status():
    assert get_base_status(None) == "TODO"
    assert get_base_status("Done") == "DONE"
    assert get_base_status("In Progress") == "IN_PROGRESS"
    assert get_base_status("En revisión") == "IN_PROGRESS"
    assert get_base_status("Backlog") == "TODO"

    # With DB mapping
    mock_db = MagicMock()
    mapping = MagicMock(estado_base="DONE")
    mock_db.query.return_value.filter.return_value.first.return_value = mapping
    assert get_base_status("En Pruebas", mock_db, "P1") == "DONE"

def test_get_developer_scorecard_data_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    scorecard = get_developer_scorecard_data(mock_db, "P1", "dev@test.com")
    assert scorecard["proyecto_id"] == "P1"
    assert scorecard["throughput_tickets"] == 0
    assert scorecard["wip_tickets"] == 0

def test_get_developer_scorecard_data_with_issues():
    mock_db = MagicMock()
    
    issue_done = MagicMock(
        id_jira="J1", key_issue="K1", summary="Sum 1", status_actual="Done", id_proyecto="P1",
        story_points="3", issue_type="Story", priority="High", assignee_email="dev@test.com",
        assignee_id="dev1", assignee_name="Dev Uno", created_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc), sprint_activo=None, transiciones=[]
    )
    issue_wip = MagicMock(
        id_jira="J2", key_issue="K2", summary="Sum 2", status_actual="In Progress", id_proyecto="P1",
        story_points="5", issue_type="Bug", priority="Medium", assignee_email="dev@test.com",
        assignee_id="dev1", assignee_name="Dev Uno", created_at=datetime.now(timezone.utc),
        resolved_at=None, sprint_activo=None, transiciones=[]
    )
    
    def query_handler(model):
        m = MagicMock()
        if model == models.Issue:
            m.filter.return_value.all.return_value = [issue_done, issue_wip]
        else:
            m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            m.filter.return_value.first.return_value = None
        return m
        
    mock_db.query.side_effect = query_handler
    
    with patch("app.services.dev_metrics_service.get_issue_cycle_time_days", side_effect=[2.0, 0.0]):
        scorecard = get_developer_scorecard_data(mock_db, "P1", "dev@test.com")
        
    assert scorecard["throughput_tickets"] == 1
    assert scorecard["story_points_burned"] == 3.0
    assert scorecard["wip_tickets"] == 1
    assert len(scorecard["assigned_issues"]) == 2

def test_get_daily_focus_data():
    mock_db = MagicMock()
    scorecard = {
        "cycle_time_personal": 2.0,
        "cycle_time_prev": 3.0,
        "throughput_tickets": 5,
        "assigned_issues": [
            {"issue_type": "Bug", "status_base": "IN_PROGRESS", "key_issue": "BUG-1", "cycle_time_days": 1.0},
            {"issue_type": "Story", "status_base": "IN_PROGRESS", "key_issue": "ST-1", "cycle_time_days": 0.5},
            {"issue_type": "Story", "status_actual": "In Review", "key_issue": "ST-2", "cycle_time_days": 0.5}
        ]
    }
    
    with patch("app.services.dev_metrics_service.get_developer_scorecard_data", return_value=scorecard), \
         patch("app.services.dev_metrics_service._generate_ai_coach_tip", return_value="Tip"):
        focus = get_daily_focus_data(mock_db, "P1", "dev@test.com")
        
    assert focus["ai_coach_tip"] == "Tip"
    assert len(focus["urgent_qa_bugs"]) == 1
    assert len(focus["active_in_progress"]) == 1

def test_get_developer_alerts_data():
    mock_db = MagicMock()
    scorecard = {
        "wip_tickets": 4, # triggers WIP_EXCEEDED
        "assigned_issues": [
            {"id_jira": "J1", "key_issue": "K1", "summary": "S1", "status_base": "IN_PROGRESS", "status_actual": "Doing", "cycle_time_days": 3.0}
        ]
    }
    with patch("app.services.dev_metrics_service.get_developer_scorecard_data", return_value=scorecard):
        alerts_data = get_developer_alerts_data(mock_db, "P1", "dev@test.com")
        
    assert alerts_data["total_active_alerts"] == 2
    alert_types = [a["type"] for a in alerts_data["alerts"]]
    assert "INACTIVITY" in alert_types
    assert "WIP_EXCEEDED" in alert_types

def test_perform_alert_action():
    r1 = perform_alert_action(MagicMock(), "J10", "request_help")
    assert "solicitud de auxilio" in r1["message"].lower()

    r2 = perform_alert_action(MagicMock(), "J10", "mark_blocked")
    assert "[BLOCKED]" in r2["message"]

    r3 = perform_alert_action(MagicMock(), "J10", "split_task")
    assert "sub-tareas" in r3["message"]

def test_format_transition_time():
    now = datetime.now(timezone.utc)
    assert _format_transition_time(None) == "Fecha desconocida"
    assert "minutos" in _format_transition_time(now)
    assert "Ayer" in _format_transition_time(now - timedelta(days=1))
    assert "días" in _format_transition_time(now - timedelta(days=3))

def test_get_activity_history_data():
    mock_db = MagicMock()
    
    t1 = MagicMock(id_jira="J1", estado_anterior="To Do", estado_nuevo="Done", fecha_cambio=datetime.now(timezone.utc))
    issue1 = MagicMock(id_jira="J1", key_issue="K1", story_points=3, issue_type="Story")
    
    q_trans = MagicMock()
    q_trans.join.return_value.filter.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = [t1]
    
    def query_handler(model):
        if model == models.TransicionEstadoIssue:
            return q_trans
        elif model == models.Issue:
            m = MagicMock()
            m.filter.return_value.first.return_value = issue1
            return m
        return MagicMock()
        
    mock_db.query.side_effect = query_handler
    
    scorecard = {
        "cycle_time_personal": 1.5,
        "throughput_tickets": 10,
        "kpis": {"bugs_totales": 0, "bugs_resueltos": 0, "commitment_rate_pct": 90, "throughput_issues": 10}
    }
    
    with patch("app.services.dev_metrics_service.get_developer_scorecard_data", return_value=scorecard):
        act_data = get_activity_history_data(mock_db, "P1", "dev@test.com")
        
    assert len(act_data["activity_feed"]) == 1
    assert act_data["unlocked_badges_count"] > 0
