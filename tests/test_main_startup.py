import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app, startup_event

client = TestClient(app)

def test_read_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "MCHAV Analytics" in res.json()["message"]

def test_startup_event():
    with patch("app.main.engine.connect") as mock_conn, \
         patch("app.main.SessionLocal") as mock_session_local, \
         patch("app.core.scheduler.start_scheduler"):
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Execute startup_event function directly
        startup_event()
