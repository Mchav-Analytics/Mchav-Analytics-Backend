import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.api.v1.controllers.developers_controller import (
    get_team_performance_matrix,
    get_my_scorecard,
    get_my_daily_focus,
    get_my_alerts,
    execute_alert_action,
    get_my_activity_history,
    get_my_issues,
    list_developers,
    get_developer_scorecard_by_id,
    update_task_status,
    TaskStatusUpdate
)
import app.models as models

def test_get_team_performance_matrix():
    mock_db = MagicMock()
    with patch("app.api.v1.controllers.developers_controller.calculate_team_performance_matrix", return_value={"total": 0}):
        res = get_team_performance_matrix("P1", "S1", mock_db)
        assert res == {"total": 0}

    # Exception fallback
    mock_db.rollback.side_effect = None
    with patch("app.api.v1.controllers.developers_controller.calculate_team_performance_matrix", side_effect=Exception("DB Error")):
        res_err = get_team_performance_matrix("P1", "S1", mock_db)
        assert res_err["team_summary"]["total_desarrolladores"] == 0

def test_dev_me_endpoints():
    mock_db = MagicMock()
    user = MagicMock(email="dev@test.com")

    with patch("app.api.v1.controllers.developers_controller.get_developer_scorecard_data", return_value={"assigned_issues": ["i1"]}):
        sc = get_my_scorecard("P1", mock_db, user)
        assert "assigned_issues" in sc

        issues_res = get_my_issues("P1", mock_db, user)
        assert issues_res["total_issues"] == 1

    with patch("app.api.v1.controllers.developers_controller.get_daily_focus_data", return_value={"tip": "ok"}):
        focus = get_my_daily_focus("P1", mock_db, user)
        assert focus["tip"] == "ok"

    with patch("app.api.v1.controllers.developers_controller.get_developer_alerts_data", return_value={"total": 1}):
        alerts = get_my_alerts("P1", mock_db, user)
        assert alerts["total"] == 1

    with patch("app.api.v1.controllers.developers_controller.perform_alert_action", return_value={"status": "SUCCESS"}):
        act = execute_alert_action("J1", "request_help", mock_db, user)
        assert act["status"] == "SUCCESS"

    with patch("app.api.v1.controllers.developers_controller.get_activity_history_data", return_value={"feed": []}):
        act_hist = get_my_activity_history("P1", mock_db, user)
        assert act_hist["feed"] == []

def test_list_developers_and_scorecard_by_id():
    mock_db = MagicMock()
    row1 = MagicMock(assignee_id="DEV1", assignee_name="Dev 1", assignee_email="dev1@test.com")
    mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [row1]

    devs = list_developers("P1", mock_db)
    assert len(devs) == 1
    assert devs[0]["assignee_id"] == "DEV1"

    with patch("app.api.v1.controllers.developers_controller.get_developer_scorecard_data", return_value={"id": "DEV1"}):
        sc = get_developer_scorecard_by_id("DEV1", "P1", mock_db)
        assert sc["id"] == "DEV1"

def test_update_task_status():
    mock_db = MagicMock()
    user = MagicMock()
    
    # Not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        update_task_status("TASK-99", TaskStatusUpdate(status="Done"), mock_db, user)
    assert exc.value.status_code == 404

    # Found
    issue_mock = MagicMock(status_actual="In Progress")
    mock_db.query.return_value.filter.return_value.first.return_value = issue_mock
    res = update_task_status("TASK-1", TaskStatusUpdate(status="Done"), mock_db, user)
    assert res["status"] == "success"
    assert issue_mock.status_actual == "Done"
