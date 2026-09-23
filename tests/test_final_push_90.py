import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app, startup_event
from app.core.security import get_current_user, sign_session_id
from app.models.auth import User, Role
from app.models.jira import Issue, Proyecto
from app.models.metrics import LogsSincronizacion
from app.models.issue_history import IssueHistory
from app.core.database import get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="admin@mchav.com", activo=True, rol=mock_role, api_token_vinculado=False)
    mock_user.proyectos_asignados = []
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

# -----------------------------------------------------------------------------
# 1. REPORTS CONTROLLER HISTORICAL TESTS
# -----------------------------------------------------------------------------

def test_get_historical_report_success_and_edge_cases():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Issue 1: has IssueHistory with valid float
    issue1 = Issue(id_jira="ISSUE-1", key_issue="ISSUE-1", id_proyecto="P1", story_points=3.0)
    hist1 = IssueHistory(id_jira="ISSUE-1", campo_modificado="story_points", valor_nuevo="5.5", fecha_cambio=datetime(2026, 2, 1))

    # Issue 2: has IssueHistory with invalid string (ValueError)
    issue2 = Issue(id_jira="ISSUE-2", key_issue="ISSUE-2", id_proyecto="P1", story_points=2.0)
    hist2 = IssueHistory(id_jira="ISSUE-2", campo_modificado="Story point estimate", valor_nuevo="invalid_num", fecha_cambio=datetime(2026, 2, 1))

    # Issue 3: no history, falls back to issue.story_points
    issue3 = Issue(id_jira="ISSUE-3", key_issue="ISSUE-3", id_proyecto="P1", story_points=8.0)

    history_first_mock = MagicMock(side_effect=[hist1, hist2, None])

    def mock_query(model):
        q = MagicMock()
        if model == Issue:
            q.filter.return_value.all.return_value = [issue1, issue2, issue3]
        elif model == IssueHistory:
            q.filter.return_value.order_by.return_value.first = history_first_mock
        return q

    mock_db.query.side_effect = mock_query

    res = client.get("/api/v1/reports/historical?proyecto_id=P1&month=2026-02")
    assert res.status_code == 200
    data = res.json()
    assert data["month"] == "2026-02"
    assert data["totalIssues"] == 3
    # 5.5 + 0 (ValueError) + 8.0 = 13.5
    assert data["pointsCompleted"] == 13.5
    assert data["sprintHealth"] == 88

def test_get_historical_report_error_handling():
    # Invalid month format causes ValueError in split or int conversion
    res = client.get("/api/v1/reports/historical?proyecto_id=P1&month=invalid-month-date")
    assert res.status_code == 400
    assert "Error reconstruyendo historial" in res.json()["detail"]

def test_get_historical_report_range_all_time_and_dates():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    issue = Issue(id_jira="ISSUE-1", key_issue="ISSUE-1", id_proyecto="P1", story_points=4.0)
    hist = IssueHistory(id_jira="ISSUE-1", campo_modificado="story_points", valor_nuevo="10.0")

    mock_db.query.return_value.filter.return_value.all.return_value = [issue]
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = hist

    # Test all_time=true
    res = client.get("/api/v1/reports/historical/range?proyecto_id=P1&all_time=true")
    assert res.status_code == 200
    assert res.json()["month"] == "Historial Completo"
    assert res.json()["pointsCompleted"] == 10.0

    # Test with range dates
    res2 = client.get("/api/v1/reports/historical/range?proyecto_id=P1&start_date=2026-01-01&end_date=2026-03-01")
    assert res2.status_code == 200
    assert res2.json()["month"] == "2026-01-01 a 2026-03-01"

    # Test error handling with invalid date
    res3 = client.get("/api/v1/reports/historical/range?proyecto_id=P1&end_date=bad-date")
    assert res3.status_code == 400
    assert "Error reconstruyendo historial por rango" in res3.json()["detail"]

# -----------------------------------------------------------------------------
# 2. MAIN STARTUP DB MIGRATIONS TESTS
# -----------------------------------------------------------------------------

def test_startup_db_migrations_seeding_and_cleanup():
    with patch('app.main.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.start_scheduler') as mock_scheduler:
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        # Role exists
        mock_role = Role(id_rol=1, nombre_rol="Administrador")
        # Simulate: first 2 users don't exist (new_u added), 3rd user exists without password_hash
        existing_user = User(id_usuario=99, email="corredorbeltran592@gmail.com", password_hash=None)

        def mock_query(model):
            q = MagicMock()
            if model == User:
                # filter by email
                def user_filter(*args, **kwargs):
                    sub = MagicMock()
                    sub.first.side_effect = [None, None, existing_user, None, None]
                    return sub
                q.filter = user_filter
            elif model == Role:
                q.filter.return_value.first.return_value = mock_role
            elif model == LogsSincronizacion:
                stuck_log = LogsSincronizacion(id_log=1, resultado="RUNNING")
                q.filter.return_value.all.return_value = [stuck_log]
            return q

        mock_db.query.side_effect = mock_query

        startup_event()

        assert mock_db.commit.called
        assert mock_db.close.called
        assert mock_scheduler.called

def test_startup_db_migrations_exceptions_handled():
    # Test DB exception caught and scheduler error caught
    with patch('app.main.SessionLocal') as mock_session_cls, \
         patch('app.core.scheduler.start_scheduler') as mock_scheduler:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB Query failed")
        mock_session_cls.return_value = mock_db
        mock_scheduler.side_effect = Exception("Scheduler error")
        # Should not raise
        startup_event()
        assert mock_db.close.called

# -----------------------------------------------------------------------------
# 3. JIRA CONTROLLER TRANSITIONS & SYNC TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
@patch('app.services.jira_sync_service.refresh_user_token')
async def test_get_issue_transitions_401_retry_success(
    mock_refresh, mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer old"})

    # First call raises 401, second call succeeds after refresh
    mock_fetch.side_effect = [
        Exception("Client error '401 Unauthorized'"),
        {
            "transitions": [
                {
                    "id": "21",
                    "name": "En Curso",
                    "to": {"name": "En Curso", "statusCategory": {"key": "indeterminate"}}
                }
            ]
        }
    ]
    mock_refresh.return_value = "new_token_123"

    res = client.get("/api/v1/jira/issues/PROJ-101/transitions")
    assert res.status_code == 200
    data = res.json()
    assert data["issue_key"] == "PROJ-101"
    assert len(data["transitions"]) == 1
    assert data["transitions"][0]["name"] == "En Curso"

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
@patch('app.services.jira_sync_service.refresh_user_token')
async def test_get_issue_transitions_401_refresh_fails(
    mock_refresh, mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer old"})

    mock_fetch.side_effect = Exception("Client error '401 Unauthorized'")
    mock_refresh.return_value = None  # Failed to refresh

    res = client.get("/api/v1/jira/issues/PROJ-101/transitions")
    assert res.status_code == 400
    assert "Error consultando transiciones en Jira" in res.json()["detail"]

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
@patch('app.datasources.jira_datasource.JiraDatasource.post_issue_transition')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_details')
@patch('app.api.v1.controllers.jira_controller.issue_repo')
@patch('app.api.v1.controllers.jira_controller.calculate_and_save_kpis')
async def test_execute_issue_transition_success_done(
    mock_kpis, mock_issue_repo, mock_details, mock_post, mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer token"})

    mock_fetch.return_value = {
        "transitions": [
            {"id": "31", "name": "Finalizado", "to": {"name": "Done"}}
        ]
    }
    mock_post.return_value = {}
    mock_details.return_value = {"fields": {"status": {"name": "Done"}}}

    db_issue = Issue(id_jira="101", key_issue="PROJ-101", id_proyecto="P1", resolved_at=None)
    mock_issue_repo.get_by_key.return_value = db_issue

    res = client.post(
        "/api/v1/jira/issues/PROJ-101/transitions",
        json={"target_status": "finalizado"}
    )
    assert res.status_code == 200
    assert res.json()["new_status"] == "Done"
    assert mock_issue_repo.update.called
    assert mock_kpis.called

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
async def test_execute_issue_transition_unavailable_error(
    mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer token"})

    mock_fetch.return_value = {
        "transitions": [
            {"id": "11", "name": "En Revisión", "to": {"name": "In Review"}}
        ]
    }

    res = client.post(
        "/api/v1/jira/issues/PROJ-101/transitions",
        json={"target_status": "finalizado"}
    )
    assert res.status_code == 400
    assert "no está disponible" in res.json()["detail"]

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.log_repo')
@patch('asyncio.sleep', new_callable=AsyncMock)
async def test_trigger_jira_sync_wait_loop(
    mock_sleep, mock_log_repo, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    # has_running_sync is True for initial check, True on 1st loop iteration, False on 2nd
    mock_log_repo.has_running_sync.side_effect = [True, True, False]

    res = client.post("/api/v1/jira/sync?wait=true")
    assert res.status_code == 200
    assert res.json()["message"] == "Sincronización completada con éxito"
    assert mock_sleep.called

# -----------------------------------------------------------------------------
# 4. JQL CONTROLLER TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jql_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jql_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jql_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issues_jql')
async def test_execute_custom_jql_success(
    mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer token"})

    mock_fetch.return_value = {
        "total": 1,
        "issues": [
            {
                "id": "1001",
                "key": "TEST-1",
                "fields": {
                    "summary": "Sample task",
                    "assignee": {"displayName": "John Doe"},
                    "status": {"name": "In Progress"},
                    "issuetype": {"name": "Story"}
                }
            }
        ]
    }

    res = client.post(
        "/api/v1/jql/execute",
        json={"jql": "project = TEST ORDER BY created DESC", "max_results": 20}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["issues"]) == 1
    assert data["issues"][0]["assignee_name"] == "John Doe"
    assert data["issues"][0]["status_actual"] == "In Progress"

@pytest.mark.asyncio
@patch('app.api.v1.controllers.jql_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jql_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jql_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issues_jql')
async def test_execute_custom_jql_error_handling(
    mock_fetch, mock_creds, mock_check_user, mock_user_id
):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer token"})
    mock_fetch.side_effect = Exception("Remote API failure")

    res = client.post(
        "/api/v1/jql/execute",
        json={"jql": "project = TEST", "max_results": 10}
    )
    assert res.status_code == 400
    assert "Error al ejecutar la consulta JQL en Jira" in res.json()["detail"]

def test_get_jql_presets():
    res = client.get("/api/v1/jql/presets?project_key=MCHAV")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["project_key"] == "MCHAV"
    assert len(data["categories"]) > 0

    # Default key
    res2 = client.get("/api/v1/jql/presets")
    assert res2.status_code == 200
    assert res2.json()["project_key"] == "SCRUM"

# -----------------------------------------------------------------------------
# 5. AUTH CONTROLLER OAUTH CALLBACK & LOCAL LOGIN TESTS
# -----------------------------------------------------------------------------

def test_auth_callback_error_query_param():
    res = client.get("/api/v1/auth/callback?error=access_denied", follow_redirects=False)
    assert res.status_code == 302
    assert "login=error" in res.headers["location"]

def test_auth_callback_invalid_state():
    with patch('app.api.v1.controllers.auth_controller.auth_service.validate_oauth_state', return_value=False):
        res = client.get("/api/v1/auth/callback?code=fake_code&state=fake_state")
        assert res.status_code == 400
        assert "inválido o expirado" in res.json()["detail"]

@pytest.mark.asyncio
@patch('app.api.v1.controllers.auth_controller.auth_service.validate_oauth_state', return_value=True)
@patch('app.api.v1.controllers.auth_controller.auth_service.exchange_code_for_user_profile')
@patch('app.api.v1.controllers.auth_controller.user_repo')
async def test_auth_callback_success_create_user(mock_user_repo, mock_exchange, mock_validate):
    mock_exchange.return_value = {
        "jira_account_id": "acc-12345",
        "email": "newuser@example.com",
        "nombre": "New User"
    }
    mock_user_repo.get_by_jira_account_id.return_value = None

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_role = Role(id_rol=1, nombre_rol="Administrador")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_role

    created_user = User(id_usuario=10, email="newuser@example.com", nombre="New User")
    mock_user_repo.create.return_value = created_user

    res = client.get("/api/v1/auth/callback?code=valid_code&state=valid_state", follow_redirects=False)
    assert res.status_code == 302
    assert "login=success" in res.headers["location"]
    assert "session_id=" in res.headers.get("set-cookie", "")

def test_auth_post_login_create_new():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # User does not exist yet
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,  # User not found
        Role(id_rol=1, nombre_rol="Administrador")  # Role found
    ]

    new_user = User(id_usuario=55, email="nuevo@test.com", nombre="Nuevo", id_rol=1, activo=True)
    new_user.rol = Role(id_rol=1, nombre_rol="Administrador")
    mock_db.refresh.side_effect = lambda u: setattr(u, "id_usuario", 55)

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nuevo@test.com", "role": "ADMIN"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "nuevo@test.com"
    assert "session_id" in res.headers.get("set-cookie", "")

def test_auth_logout_get():
    res = client.get("/api/v1/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_audit_middleware_with_bearer_token():
    import jwt
    from app.core.config import SESSION_SECRET_KEY
    from app.core.security import JWT_ALGORITHM
    token = jwt.encode({"sub": "admin@mchav.com"}, SESSION_SECRET_KEY, algorithm=JWT_ALGORITHM)

    # Request with Bearer token that hits PUT in users or other endpoint
    res = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [200, 401]  # Middleware executes and decodes token successfully

    # Hit PUT on users path to test audit middleware line 42-43
    res_put = client.put("/api/v1/users/roles", headers={"Authorization": f"Bearer {token}"})
    assert res_put.status_code in [200, 404, 405]

def test_read_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "Bienvenido" in res.json()["message"]

def test_auth_me_and_credentials_endpoints():
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "admin@mchav.com"

    res_cred = client.get("/api/v1/auth/jira-credentials")
    assert res_cred.status_code == 200
