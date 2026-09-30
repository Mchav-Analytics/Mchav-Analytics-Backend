import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.repositories.dev_metrics_repo import dev_kpi_repo
from app.repositories.metrics_repo import kpi_repo, log_repo
from app.services.sprint_health_service import calculate_burndown_chart_data, calculate_sprint_health
import app.models as models

def test_dev_metrics_repo():
    mock_db = MagicMock()
    
    # get_by_dev_and_sprint with sprint_id
    dev_kpi_repo.get_by_dev_and_sprint(mock_db, "PROJ-1", "user1", "SP-1")
    assert mock_db.query.called

    # get_by_dev_and_sprint without sprint_id
    dev_kpi_repo.get_by_dev_and_sprint(mock_db, "PROJ-1", "user1", None)
    assert mock_db.query.called

    # get_all_by_project
    dev_kpi_repo.get_all_by_project(mock_db, "PROJ-1")
    assert mock_db.query.called

def test_metrics_repo():
    mock_db = MagicMock()

    # get_general_kpi
    kpi_repo.get_general_kpi(mock_db, "PROJ-1")
    assert mock_db.query.called

    # get_sprint_kpi
    kpi_repo.get_sprint_kpi(mock_db, "PROJ-1", "SP-1")
    assert mock_db.query.called

    # get_all_by_project
    kpi_repo.get_all_by_project(mock_db, "PROJ-1")
    assert mock_db.query.called

    # log_repo
    log_repo.get_recent(mock_db, skip=0, limit=10)
    assert mock_db.query.called

    mock_db.query.return_value.filter.return_value.count.return_value = 0
    assert log_repo.has_running_sync(mock_db) is False

    # get_filtered_logs with no filters (calls get_recent)
    with patch.object(log_repo, "get_recent") as mock_rec:
        log_repo.get_filtered_logs(mock_db)
        mock_rec.assert_called_once()

    # get_filtered_logs with filters
    log_repo.get_filtered_logs(
        mock_db,
        tipo_sincronizacion="MANUAL",
        resultado="SUCCESS",
        fecha_inicio="2026-01-01T00:00:00Z",
        fecha_fin="2026-01-31T23:59:59Z"
    )
    assert mock_db.query.called

def test_calculate_burndown_chart():
    mock_db = MagicMock()
    
    # 1. No sprint found
    mock_db.query.return_value.filter_by.return_value.first.return_value = None
    mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
    res_empty = calculate_burndown_chart_data(mock_db, "PROJ-1", "SP-1")
    assert res_empty == []

    # 2. Sprint found with issues and transitions
    sprint = MagicMock()
    sprint.id_sprint = "SP-1"
    start = datetime(2026, 3, 1, 9, 0, 0)
    end = datetime(2026, 3, 5, 18, 0, 0)
    sprint.fecha_inicio = start
    sprint.fecha_fin = end

    issue1 = MagicMock()
    issue1.id_jira = "101"
    issue1.story_points = 5.0
    issue1.estado = "Done"

    issue2 = MagicMock()
    issue2.id_jira = "102"
    issue2.story_points = 3.0
    issue2.estado = "En progreso"

    trans1 = MagicMock()
    trans1.id_jira = "101"
    trans1.fecha_cambio = datetime(2026, 3, 3, 12, 0, 0)
    trans1.estado_nuevo = "Done"

    def query_mock(model):
        m = MagicMock()
        if model == models.Sprint:
            m.filter_by.return_value.first.return_value = sprint
            m.filter_by.return_value.order_by.return_value.first.return_value = sprint
        elif model == models.Issue:
            m.filter.return_value.all.return_value = [issue1, issue2]
        elif model == models.TransicionEstadoIssue:
            m.filter.return_value.order_by.return_value.all.return_value = [trans1]
        return m

    mock_db.query.side_effect = query_mock

    res = calculate_burndown_chart_data(mock_db, "PROJ-1", "SP-1")
    assert len(res) == 5  # delta_days + 1
    assert res[0]["fecha"] == "Día 0"
    assert "esfuerzo_ideal" in res[0]
    assert "esfuerzo_restante" in res[0]

def test_sprint_health_service_more_branches():
    mock_db = MagicMock()
    sprint = MagicMock()
    sprint.id_sprint = "SP-1"
    sprint.fecha_inicio = datetime(2026, 3, 1, tzinfo=timezone.utc)

    # Issue with scope creep and review
    issue_rev = MagicMock()
    issue_rev.key_issue = "ISSUE-REV"
    issue_rev.summary = "Review task"
    issue_rev.status_actual = "In Review"
    issue_rev.story_points = 3.0
    issue_rev.created_at = datetime(2026, 3, 2, tzinfo=timezone.utc)
    issue_rev.updated_at = datetime(2026, 3, 3, tzinfo=timezone.utc)
    issue_rev.resolved_at = None
    issue_rev.assignee_name = "Dev Reviewer"
    issue_rev.sprint_activo = sprint

    # Issue canceled
    issue_canc = MagicMock()
    issue_canc.key_issue = "ISSUE-CANC"
    issue_canc.summary = "Canceled task"
    issue_canc.status_actual = "Cancelled"
    issue_canc.story_points = 2.0
    issue_canc.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
    issue_canc.updated_at = datetime(2026, 3, 3, tzinfo=timezone.utc)
    issue_canc.resolved_at = None
    issue_canc.assignee_name = "Dev Reviewer"
    issue_canc.sprint_activo = sprint

    def query_mock(model):
        m = MagicMock()
        if model == models.Sprint:
            m.filter.return_value.first.return_value = sprint
            m.filter.return_value.order_by.return_value.first.return_value = sprint
            m.filter_by.return_value.first.return_value = sprint
        elif model == models.Issue:
            m.filter.return_value.all.return_value = [issue_rev, issue_canc]
            m.filter.return_value.filter.return_value.all.return_value = [issue_rev, issue_canc]
            m.all.return_value = [issue_rev, issue_canc]
        elif model == models.MapeoEstado:
            m.filter.return_value.all.return_value = []
        return m

    mock_db.query.side_effect = query_mock

    with patch("app.services.sprint_health_service.get_issue_cycle_time_days", return_value=4.0):
        health = calculate_sprint_health(mock_db, "PROJ-1", "SP-1")
        assert "diagnostico" in health
        assert "health_score" in health
        assert health["metrics"]["tickets_changed"] >= 1
