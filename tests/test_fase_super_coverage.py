import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.core import scheduler
from app.services import dev_metrics_service
from app.repositories import jira_repo
import app.models as models

# ----------------------------------------------------------------------
# 1. SCHEDULER
# ----------------------------------------------------------------------

def test_scheduled_sync_job_branches():
    # Branch 1: Sync already running
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.log_repo.has_running_sync', return_value=True):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        scheduler.scheduled_sync_job()
        assert mock_db.close.called

    # Branch 2: No active user
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.log_repo.has_running_sync', return_value=False):
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None
        mock_session_cls.return_value = mock_db
        scheduler.scheduled_sync_job()
        assert mock_db.close.called

    # Branch 3: Active user executes sync
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.log_repo.has_running_sync', return_value=False), \
         patch('app.core.scheduler.run_jira_sync', new_callable=AsyncMock) as mock_sync:
        mock_db = MagicMock()
        mock_user = MagicMock(id_usuario=1)
        mock_db.query().filter().first.return_value = mock_user
        mock_session_cls.return_value = mock_db
        scheduler.scheduled_sync_job()
        assert mock_sync.called
        assert mock_db.close.called

    # Branch 4: Exception handling inside try block
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.log_repo.has_running_sync', side_effect=Exception("DB error")):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        scheduler.scheduled_sync_job()
        assert mock_db.close.called

def test_scheduled_monthly_reports_job_branches():
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.services.monthly_report_dispatcher_service.dispatch_monthly_reports') as mock_dispatch:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_dispatch.return_value = {"sent": 2}
        scheduler.scheduled_monthly_reports_job()
        assert mock_db.close.called

    # Exception inside try block
    with patch('app.core.scheduler.SessionLocal') as mock_session_cls, \
         patch('app.services.monthly_report_dispatcher_service.dispatch_monthly_reports', side_effect=Exception("Monthly error")):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        scheduler.scheduled_monthly_reports_job()
        assert mock_db.close.called

def test_scheduler_lifecycle():
    scheduler._scheduler = None
    with patch('app.core.scheduler.BackgroundScheduler') as mock_sched_cls:
        sched_inst = MagicMock()
        mock_sched_cls.return_value = sched_inst
        scheduler.start_scheduler()
        assert sched_inst.start.called
        scheduler.stop_scheduler()
        assert sched_inst.shutdown.called


# ----------------------------------------------------------------------
# 2. DEV METRICS SERVICE (Pure helpers and edge cases)
# ----------------------------------------------------------------------

def test_dev_metrics_calc_time_ago():
    assert dev_metrics_service._calc_time_ago({"cycle_time_days": 0.2}) == "Reciente"
    assert dev_metrics_service._calc_time_ago({"cycle_time_days": 0.8}) == "Hace unas horas"
    assert dev_metrics_service._calc_time_ago({"cycle_time_days": 1.5}) == "Hace 1 día"
    assert dev_metrics_service._calc_time_ago({"cycle_time_days": 4.0}) == "Hace 4 días"

def test_dev_metrics_ai_coach_tip_rules():
    with patch('app.services.gemini_service.generate_dev_coach_tip', side_effect=lambda sc, u, a, fb: fb):
        # Case 1: ct improvement
        scorecard1 = {"cycle_time_personal": 2.0, "cycle_time_prev": 4.0, "wip_tickets": 2}
        tip1 = dev_metrics_service._generate_ai_coach_tip(scorecard1, [], [])
        assert "mejorado" in tip1

        # Case 2: ct worsening + urgent QA + high WIP
        scorecard2 = {"cycle_time_personal": 5.0, "cycle_time_prev": 3.0, "wip_tickets": 5}
        urgent = [{"key_issue": "BUG-1"}, {"key_issue": "BUG-2"}]
        tip2 = dev_metrics_service._generate_ai_coach_tip(scorecard2, urgent, [])
        assert "aumentado" in tip2
        assert "bug(s) pendientes" in tip2
        assert "WIP actual es 5" in tip2

        # Case 3: Empty tips with throughput
        scorecard3 = {"throughput_tickets": 5}
        tip3 = dev_metrics_service._generate_ai_coach_tip(scorecard3, [], [])
        assert "Has completado 5 tickets" in tip3

        # Case 4: Zero throughput
        scorecard4 = {"throughput_tickets": 0}
        tip4 = dev_metrics_service._generate_ai_coach_tip(scorecard4, [], [])
        assert "Aún no hay entregas" in tip4

def test_format_transition_time():
    now = datetime.now(timezone.utc)
    assert dev_metrics_service._format_transition_time(None) == "Fecha desconocida"
    assert dev_metrics_service._format_transition_time(now - timedelta(minutes=10)) == "Hace unos minutos"
    assert "Hoy hace" in dev_metrics_service._format_transition_time(now - timedelta(hours=3))
    assert "Ayer" in dev_metrics_service._format_transition_time(now - timedelta(days=1))
    assert "Hace 3 días" in dev_metrics_service._format_transition_time(now - timedelta(days=3))
    assert "/" in dev_metrics_service._format_transition_time(now - timedelta(days=15))

def test_perform_alert_action():
    db = MagicMock()
    r1 = dev_metrics_service.perform_alert_action(db, "101", "request_help")
    assert "Solicitud de auxilio" in r1["message"]

    r2 = dev_metrics_service.perform_alert_action(db, "101", "mark_blocked")
    assert "[BLOCKED]" in r2["message"]

    r3 = dev_metrics_service.perform_alert_action(db, "101", "split_task")
    assert "desglose" in r3["message"]

    r4 = dev_metrics_service.perform_alert_action(db, "101", "custom_action")
    assert "custom_action" in r4["message"]

def test_calculate_dynamic_badges():
    mock_db = MagicMock()
    with patch('app.services.dev_metrics_service.get_developer_scorecard_data') as mock_scorecard:
        # Scorecard with all unlocked
        mock_scorecard.return_value = {
            "cycle_time_personal": 1.5,
            "kpis": {
                "bugs_totales": 5,
                "bugs_resueltos": 5,
                "commitment_rate_pct": 90,
                "throughput_issues": 10
            }
        }
        badges = dev_metrics_service._calculate_dynamic_badges(mock_db, "PROJ-1", "dev@mchav.com")
        assert len(badges) >= 4
        assert all(b["status"] == "UNLOCKED" for b in badges)

        # Scorecard with all locked
        mock_scorecard.return_value = {
            "cycle_time_personal": 4.5,
            "kpis": {
                "bugs_totales": 5,
                "bugs_resueltos": 2,
                "commitment_rate_pct": 50,
                "throughput_issues": 3
            }
        }
        badges2 = dev_metrics_service._calculate_dynamic_badges(mock_db, "PROJ-1", "dev@mchav.com")
        assert any(b["status"] == "LOCKED" for b in badges2)


# ----------------------------------------------------------------------
# 3. JIRA REPOSITORY
# ----------------------------------------------------------------------

def test_jira_repo_get_recent_resolved_issues_raw():
    mock_db = MagicMock()
    mock_db.bind.dialect.name = "sqlite"

    mock_query = MagicMock()
    mock_db.query.return_value = mock_query

    # Branch 1: >= 3 recent issues
    mock_query.filter.return_value.filter.return_value.all.return_value = [("Story", 2.0, 1.0)] * 3
    res = jira_repo.issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in progress"}, days=15)
    assert len(res) == 3

    # Branch 2: Fallback 1 - all_resolved >= 3
    mock_query.filter.return_value.filter.return_value.all.return_value = [("Story", 2.0, 1.0)]  # < 3
    mock_query.filter.return_value.all.return_value = [("Story", 2.0, 1.0)] * 4
    res2 = jira_repo.issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in progress"}, days=15)
    assert len(res2) == 4

    # Branch 3: PostgreSQL dialect
    mock_db.bind.dialect.name = "postgresql"
    res3 = jira_repo.issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in progress"}, days=15)
    assert len(res3) == 4

def test_crud_transicion_delete_by_issue():
    mock_db = MagicMock()
    jira_repo.transition_repo.delete_by_issue(mock_db, "ISSUE-100")
    assert mock_db.commit.called
