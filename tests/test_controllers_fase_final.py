import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
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
    mock_user.proyectos_asignados = []
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

# ----------------------------------------------------
# 1. PRUEBAS PARA USERS_CONTROLLER
# ----------------------------------------------------

def test_list_users_and_roles():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    u = User(id_usuario=2, email="dev@mchav.com", nombre="Dev", activo=True, rol=Role(nombre_rol="Desarrollador"))
    u.proyectos_asignados = [MagicMock(id_proyecto="PROJ-1")]
    mock_db.query(User).all.return_value = [u]

    res = client.get("/api/v1/users", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["email"] == "dev@mchav.com"

    # List roles
    mock_db.query(Role).all.return_value = [Role(id_rol=1, nombre_rol="Administrador", scopes="admin")]
    res_roles = client.get("/api/v1/users/roles", cookies={"session_id": sign_session_id(1)})
    assert res_roles.status_code == 200
    assert len(res_roles.json()) == 1

def test_update_user_status_cases():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. Admin cannot deactivate self
    res_self = client.put("/api/v1/users/1/status", json={"activo": False}, cookies={"session_id": sign_session_id(1)})
    assert res_self.status_code == 400

    # 2. User not found
    mock_db.query().filter().first.return_value = None
    res_404 = client.put("/api/v1/users/99/status", json={"activo": False}, cookies={"session_id": sign_session_id(1)})
    assert res_404.status_code == 404

    # 3. Success activate/deactivate
    target = User(id_usuario=2, email="dev@mchav.com", activo=True)
    mock_db.query().filter().first.return_value = target
    res_ok = client.put("/api/v1/users/2/status", json={"activo": False}, cookies={"session_id": sign_session_id(1)})
    assert res_ok.status_code == 200
    assert target.activo is False

def test_update_user_role_cases():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    target = User(id_usuario=2, email="dev@mchav.com", activo=True)
    admin_role = Role(id_rol=1, nombre_rol="Administrador")

    # 1. Role not found
    def mock_query_norole(model):
        m = MagicMock()
        if model == User:
            m.filter.return_value.first.return_value = target
        else:
            m.filter.return_value.first.return_value = None
        return m
    mock_db.query.side_effect = mock_query_norole

    res_norole = client.put("/api/v1/users/2/role", json={"role": "ROL_INVALIDO"}, cookies={"session_id": sign_session_id(1)})
    assert res_norole.status_code == 400

    # 2. Success with string role
    def mock_query_ok(model):
        m = MagicMock()
        if model == User:
            m.filter.return_value.first.return_value = target
        else:
            m.filter.return_value.first.return_value = admin_role
        return m
    mock_db.query.side_effect = mock_query_ok

    res_ok = client.put("/api/v1/users/2/role", json={"role": "ADMIN"}, cookies={"session_id": sign_session_id(1)})
    assert res_ok.status_code == 200
    assert target.id_rol == 1

def test_user_projects_and_logs():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    target = User(id_usuario=2, email="dev@mchav.com", activo=True)
    target.proyectos_asignados = [MagicMock(id_proyecto="PROJ-1")]
    mock_db.query().filter().first.return_value = target

    # Get user projects
    res_get = client.get("/api/v1/users/2/projects", cookies={"session_id": sign_session_id(1)})
    assert res_get.status_code == 200
    assert "PROJ-1" in res_get.json()["proyectos"]

    # Assign user projects
    mock_db.query().filter().first.return_value = MagicMock()
    res_assign = client.post("/api/v1/users/2/projects", json={"id_proyectos": ["PROJ-1", "PROJ-2"]}, cookies={"session_id": sign_session_id(1)})
    assert res_assign.status_code == 200

    # User logs
    mock_db.query().filter().order_by().all.return_value = []
    res_logs = client.get("/api/v1/users/2/logs", cookies={"session_id": sign_session_id(1)})
    assert res_logs.status_code == 200

# ----------------------------------------------------
# 2. PRUEBAS PARA ALERTS_CONTROLLER
# ----------------------------------------------------

@patch('app.api.v1.controllers.alerts_controller.get_system_alerts')
def test_alerts_controller_endpoints(mock_alerts):
    mock_alerts.return_value = [{"id_alerta": 1, "tipo": "BLOQUEO"}]

    res = client.get("/api/v1/alerts", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Exception fallback
    mock_alerts.side_effect = [Exception("DB error"), []]
    res2 = client.get("/api/v1/alerts", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200

@patch('app.api.v1.controllers.alerts_controller.acknowledge_alert')
@patch('app.api.v1.controllers.alerts_controller.get_help_requests')
@patch('app.api.v1.controllers.alerts_controller.create_help_request')
@patch('app.api.v1.controllers.alerts_controller.update_help_request_status')
def test_alerts_help_requests_endpoints(mock_update, mock_create, mock_get_help, mock_ack):
    mock_ack.return_value = {"status": "ok"}
    mock_get_help.return_value = [{"id_solicitud": 1, "estado": "PENDIENTE"}]
    mock_create.return_value = {"id_solicitud": 2, "status": "creado"}
    mock_update.return_value = {"id_solicitud": 1, "nuevo_estado": "RESUELTA"}

    res_ack = client.post("/api/v1/alerts/1/acknowledge", cookies={"session_id": sign_session_id(1)})
    assert res_ack.status_code == 200

    res_get_help = client.get("/api/v1/alerts/help-requests", cookies={"session_id": sign_session_id(1)})
    assert res_get_help.status_code == 200

    res_post_help = client.post("/api/v1/alerts/help-requests", json={"mensaje": "Necesito ayuda"}, cookies={"session_id": sign_session_id(1)})
    assert res_post_help.status_code == 200

    res_patch = client.patch("/api/v1/alerts/help-requests/1?status=RESUELTA&responded_by=Admin", cookies={"session_id": sign_session_id(1)})
    assert res_patch.status_code == 200

    # Exception fallbacks
    mock_ack.side_effect = [Exception("error"), {"status": "fallback"}]
    res_ack_err = client.post("/api/v1/alerts/1/acknowledge", cookies={"session_id": sign_session_id(1)})
    assert res_ack_err.status_code == 200

    mock_get_help.side_effect = [Exception("error"), []]
    res_get_err = client.get("/api/v1/alerts/help-requests", cookies={"session_id": sign_session_id(1)})
    assert res_get_err.status_code == 200

    mock_create.side_effect = [Exception("error"), {"status": "fallback"}]
    res_post_err = client.post("/api/v1/alerts/help-requests", json={"mensaje": "test"}, cookies={"session_id": sign_session_id(1)})
    assert res_post_err.status_code == 200

    mock_update.side_effect = [Exception("error"), {"status": "fallback"}]
    res_patch_err = client.patch("/api/v1/alerts/help-requests/1?status=RESUELTA", cookies={"session_id": sign_session_id(1)})
    assert res_patch_err.status_code == 200

# ----------------------------------------------------
# 3. PRUEBAS PARA DEVELOPERS_CONTROLLER
# ----------------------------------------------------

@patch('app.api.v1.controllers.developers_controller.calculate_team_performance_matrix')
@patch('app.api.v1.controllers.developers_controller.get_developer_scorecard_data')
@patch('app.api.v1.controllers.developers_controller.get_daily_focus_data')
@patch('app.api.v1.controllers.developers_controller.get_developer_alerts_data')
@patch('app.api.v1.controllers.developers_controller.perform_alert_action')
@patch('app.api.v1.controllers.developers_controller.get_activity_history_data')
def test_developers_controller_endpoints(mock_hist, mock_action, mock_alerts, mock_focus, mock_scorecard, mock_matrix):
    mock_matrix.return_value = {"developers": []}
    mock_scorecard.return_value = {"developer_name": "Dev", "assigned_issues": [{"key": "ISSUE-1"}]}
    mock_focus.return_value = {"active_task": None}
    mock_alerts.return_value = []
    mock_action.return_value = {"status": "ok"}
    mock_hist.return_value = {"standups": []}

    res_matrix = client.get("/api/v1/developers/matrix", cookies={"session_id": sign_session_id(1)})
    assert res_matrix.status_code == 200

    res_scorecard = client.get("/api/v1/developers/me/scorecard", cookies={"session_id": sign_session_id(1)})
    assert res_scorecard.status_code == 200

    res_focus = client.get("/api/v1/developers/me/daily-focus", cookies={"session_id": sign_session_id(1)})
    assert res_focus.status_code == 200

    res_alerts = client.get("/api/v1/developers/me/alerts", cookies={"session_id": sign_session_id(1)})
    assert res_alerts.status_code == 200

    res_action = client.post("/api/v1/developers/me/alerts/ISSUE-1/action?action_type=request_help", cookies={"session_id": sign_session_id(1)})
    assert res_action.status_code == 200

    res_hist = client.get("/api/v1/developers/me/activity-history", cookies={"session_id": sign_session_id(1)})
    assert res_hist.status_code == 200

    res_issues = client.get("/api/v1/developers/me/issues", cookies={"session_id": sign_session_id(1)})
    assert res_issues.status_code == 200
    assert res_issues.json()["total_issues"] == 1

    res_dev_scorecard = client.get("/api/v1/developers/dev-123/scorecard", cookies={"session_id": sign_session_id(1)})
    assert res_dev_scorecard.status_code == 200

def test_developers_controller_task_and_list():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # List developers
    mock_row = MagicMock(assignee_id="ACC-1", assignee_name="Carlos", assignee_email="carlos@mchav.com")
    mock_db.query().filter().distinct().all.return_value = [mock_row]

    res_list = client.get("/api/v1/developers", cookies={"session_id": sign_session_id(1)})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Update task status: 404
    mock_db.query().filter().first.return_value = None
    res_404 = client.patch("/api/v1/developers/me/agenda-tasks/ISSUE-99", json={"status": "Done"}, cookies={"session_id": sign_session_id(1)})
    assert res_404.status_code == 404

    # Update task status: 200
    mock_issue = models.Issue(key_issue="ISSUE-1", status_actual="In Progress")
    mock_db.query().filter().first.return_value = mock_issue
    res_ok = client.patch("/api/v1/developers/me/agenda-tasks/ISSUE-1", json={"status": "Done"}, cookies={"session_id": sign_session_id(1)})
    assert res_ok.status_code == 200
    assert mock_issue.status_actual == "Done"
