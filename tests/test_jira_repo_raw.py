import pytest
from unittest.mock import MagicMock
from app.repositories.jira_repo import issue_repo

def test_get_recent_resolved_issues_raw_sqlite():
    mock_db = MagicMock()
    mock_db.bind.dialect.name = "sqlite"

    q_mock = MagicMock()
    # 1. Strict filter >= 3 items
    q_mock.filter.return_value.all.return_value = ["i1", "i2", "i3"]
    mock_db.query.return_value.filter.return_value = q_mock

    res = issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in_progress"}, days=15)
    assert len(res) == 3

def test_get_recent_resolved_issues_raw_postgres_fallbacks():
    mock_db = MagicMock()
    mock_db.bind.dialect.name = "postgresql"

    q_mock = MagicMock()
    # 1. Strict filter < 3 items
    # 2. Fallback 1 >= 3 items
    q_mock.filter.side_effect = [
        MagicMock(all=MagicMock(return_value=["i1"])), # recent < 3
        MagicMock(all=MagicMock(return_value=["i1", "i2", "i3"])) # all_resolved >= 3
    ]
    mock_db.query.return_value.filter.return_value = q_mock

    res = issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in_progress"}, days=15)
    assert len(res) == 3

def test_get_recent_resolved_issues_raw_fallback_all():
    mock_db = MagicMock()
    mock_db.bind.dialect.name = "sqlite"

    q_mock = MagicMock()
    q_mock.filter.side_effect = [
        MagicMock(all=MagicMock(return_value=[])), # recent
        MagicMock(all=MagicMock(return_value=[]))  # all_resolved
    ]
    q_mock.all.return_value = ["fallback_all_item"]
    mock_db.query.return_value.filter.return_value = q_mock

    res = issue_repo.get_recent_resolved_issues_raw(mock_db, "P1", {"in_progress"}, days=15)
    assert res == ["fallback_all_item"]
