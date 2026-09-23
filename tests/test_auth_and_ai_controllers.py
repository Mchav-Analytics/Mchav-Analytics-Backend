import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user, sign_session_id
from app.models.auth import User, Role
from app.core.database import get_db
import app.models as models

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="admin@mchav.com", activo=True, rol=mock_role)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

# ----------------------------------------------------------------------
# 1. AUTH CONTROLLER
# ----------------------------------------------------------------------

def test_auth_login_local_existing_and_new():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Existing user
    existing_user = User(
        id_usuario=10,
        email="user@mchav.com",
        nombre="User Test",
        activo=True,
        id_rol=1,
        rol=Role(nombre_rol="Desarrollador")
    )
    mock_db.query().filter().first.return_value = existing_user

    res = client.post("/api/v1/auth/login", json={"email": "user@mchav.com"})
    assert res.status_code == 200
    assert res.json()["email"] == "user@mchav.com"
    assert "session_id" in res.cookies

    # Brand new user
    mock_db.query().filter().first.return_value = None
    mock_db.query().filter().first.side_effect = [None, Role(id_rol=1, nombre_rol="Administrador")]
    res2 = client.post("/api/v1/auth/login", json={"email": "newadmin@mchav.com", "role": "ADMIN"})
    assert res2.status_code == 200

def test_auth_logout_endpoints():
    res_post = client.post("/api/v1/auth/logout")
    assert res_post.status_code == 200

    res_get = client.get("/api/v1/auth/logout")
    assert res_get.status_code == 200

def test_auth_token_endpoint():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Invalid user / pwd
    mock_db.query().filter().first.return_value = None
    res_err = client.post("/api/v1/auth/token", data={"username": "unknown@test.com", "password": "wrong"})
    assert res_err.status_code == 401

    # Valid user
    user = User(id_usuario=5, email="valid@test.com", activo=True)
    with patch('app.api.v1.controllers.auth_controller.verify_password', return_value=True):
        user.password_hash = "hashed"
        mock_db.query().filter().first.return_value = user
        res_ok = client.post("/api/v1/auth/token", data={"username": "valid@test.com", "password": "correct"})
        assert res_ok.status_code == 200
        assert "access_token" in res_ok.json()


# ----------------------------------------------------------------------
# 2. AI CONTROLLER
# ----------------------------------------------------------------------

def test_ai_chat_with_rich_context_and_prompts():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Create dummy issues in progress, done, bug, stuck
    now = datetime.now()
    i_done = models.Issue(
        id_jira="1", key_issue="DONE-1", summary="Done task", status_actual="Done",
        story_points=3.0, assignee_name="Carlos", assignee_email="carlos@mchav.com",
        created_at=now - timedelta(days=5), resolved_at=now - timedelta(days=2)
    )
    i_prog = models.Issue(
        id_jira="2", key_issue="PROG-1", summary="WIP task", status_actual="In Progress",
        story_points=5.0, assignee_name="Carlos", assignee_email="carlos@mchav.com",
        priority="High"
    )
    i_bug = models.Issue(
        id_jira="3", key_issue="BUG-1", summary="Critical bug", status_actual="Bloqueado",
        issue_type="Bug", priority="Highest", assignee_name="Carlos", assignee_email="carlos@mchav.com"
    )

    mock_db.query().filter().all.return_value = [i_done, i_prog, i_bug]
    with patch('app.api.v1.controllers.ai_controller.chat_with_gemini', return_value="Respuesta de IA"):
        res = client.post(
            "/api/v1/ai/chat",
            json={"message": "¿Cómo va el equipo?", "project_id": "PROJ-1"},
            cookies={"session_id": sign_session_id(1)}
        )
        assert res.status_code == 200
        assert res.json()["reply"] == "Respuesta de IA"

    res_prompts = client.get("/api/v1/ai/prompts")
    assert res_prompts.status_code == 200
    assert len(res_prompts.json()) == 4

def test_ai_generate_report_insights_developer():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    sprint = models.Sprint(id_sprint=10, id_proyecto="PROJ-01", nombre="Sprint 1", estado="closed")
    mock_db.query().filter().order_by().limit().all.return_value = [sprint]

    issue = models.Issue(id_jira="10", key_issue="DEV-1", status_actual="Done", story_points=5.0, assignee_id="dev-1")
    mock_db.query().filter().all.return_value = [issue]

    payload = {
        "reportType": "desarrollador",
        "developerId": "dev-1",
        "developerName": "Carlos Dev",
        "projectId": "PROJ-01",
        "velocity": 20,
        "cycleTime": 3.0
    }

    with patch('app.services.gemini_service.generate_report_insights', return_value={"summary": "Excelente desempeño"}):
        res = client.post("/api/v1/ai/generate-report-insights", json=payload, cookies={"session_id": sign_session_id(1)})
        assert res.status_code == 200
        assert res.json()["status"] == "success"
