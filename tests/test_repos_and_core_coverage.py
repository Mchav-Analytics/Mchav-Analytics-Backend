import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.repositories.dev_metrics_repo import dev_kpi_repo
from app.repositories.metrics_repo import kpi_repo, log_repo
from app.repositories.jira_repo import transition_repo, mapping_repo, issue_repo
from app.core.security import (
    hash_password,
    verify_password,
    create_jwt_token,
    verify_jwt_token,
    sign_session_id,
    verify_session_id,
    encrypt_jira_token,
    decrypt_jira_token
)
from app.core.scheduler import start_scheduler, stop_scheduler, scheduled_sync_job

def test_dev_metrics_repo():
    mock_db = MagicMock()
    
    dev_kpi_repo.get_by_dev_and_sprint(mock_db, "P1", "DEV1", "S1")
    assert mock_db.query.called

    dev_kpi_repo.get_by_dev_and_sprint(mock_db, "P1", "DEV1", None)
    assert mock_db.query.called

    dev_kpi_repo.get_all_by_project(mock_db, "P1")
    assert mock_db.query.called

def test_metrics_repo():
    mock_db = MagicMock()
    
    kpi_repo.get_general_kpi(mock_db, "P1")
    kpi_repo.get_sprint_kpi(mock_db, "P1", "S1")
    kpi_repo.get_all_by_project(mock_db, "P1")
    
    log_repo.get_recent(mock_db, skip=0, limit=10)
    
    mock_db.query.return_value.filter.return_value.count.return_value = 1
    assert log_repo.has_running_sync(mock_db) is True

    # Filtered logs
    log_repo.get_filtered_logs(mock_db, tipo_sincronizacion="SYNC", resultado="SUCCESS", fecha_inicio="2026-01-01T00:00:00Z", fecha_fin="2026-01-31T00:00:00Z")
    log_repo.get_filtered_logs(mock_db) # Empty params

def test_jira_repos_extra():
    mock_db = MagicMock()
    
    transition_repo.delete_by_issue(mock_db, "J1")
    transition_repo.get_existing(mock_db, "J1", datetime.now(timezone.utc), "To Do", "Done")

    mapping_repo.get_by_project(mock_db, "P1")
    mapping_repo.get_by_project_and_base(mock_db, "P1", "IN_PROGRESS")
    mapping_repo.delete_by_project(mock_db, "P1")

def test_security_core():
    pwd = "SecretPassword123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPwd", hashed) is False

    token = create_jwt_token(123, "Admin")
    assert isinstance(token, str) and len(token) > 10
    assert verify_jwt_token(token) == 123
    assert verify_jwt_token("") is None

    signed = sign_session_id(123)
    assert verify_session_id(signed) == 123
    assert verify_session_id("") is None

    enc = encrypt_jira_token("my_jira_api_token_abc")
    assert enc != "my_jira_api_token_abc"
    dec = decrypt_jira_token(enc)
    assert dec == "my_jira_api_token_abc"
    assert encrypt_jira_token("") == ""
    assert decrypt_jira_token("") == ""

def test_scheduler_core():
    with patch("apscheduler.schedulers.background.BackgroundScheduler.start"), \
         patch("apscheduler.schedulers.background.BackgroundScheduler.shutdown"):
        start_scheduler()
        stop_scheduler()

def test_scheduled_sync_job():
    with patch("app.core.scheduler.SessionLocal") as mock_session_local, \
         patch("app.repositories.log_repo.has_running_sync", return_value=True):
        scheduled_sync_job() # Skip when sync is running

    with patch("app.core.scheduler.SessionLocal") as mock_session_local, \
         patch("app.repositories.log_repo.has_running_sync", return_value=False), \
         patch("app.core.scheduler.run_jira_sync") as mock_sync:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_user = MagicMock(id_usuario=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        scheduled_sync_job()
        assert mock_sync.called
