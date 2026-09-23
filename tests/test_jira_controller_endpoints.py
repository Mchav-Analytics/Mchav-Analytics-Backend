import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user, sign_session_id
from app.models.auth import User, Role
from app.core.database import get_db
import app.models as models
from app.api.v1.controllers.jira_controller import metrics_cache

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="admin@mchav.com", activo=True, rol=mock_role)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
def test_get_jira_metrics_cache_hit_and_db_fallback(mock_get_creds, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_user = MagicMock(id_usuario=1)
    mock_check_user.return_value = mock_user
    mock_get_creds.return_value = ("https://jira.example.com", {"Authorization": "Bearer token"})

    # 1. Cache hit
    cache_key = "metrics:1"
    metrics_cache.set(cache_key, {
        "active_projects": 3,
        "completed_tickets": 25,
        "in_progress_tickets": 10,
        "critical_bugs": 2
    })
    res = client.get("/api/v1/jira/metrics", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json()["active_projects"] == 3

    # 2. Invalidate cache and test DB fallback
    metrics_cache.clear()
    # When httpx fails, fallback to DB
    mock_db = MagicMock()
    mock_db.query().count.return_value = 5
    mock_db.query().filter().count.return_value = 3
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception("Connection error")
        res2 = client.get("/api/v1/jira/metrics", cookies={"session_id": sign_session_id(1)})
        assert res2.status_code == 200
        assert res2.json()["active_projects"] == 5

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.log_repo')
def test_trigger_jira_sync(mock_log_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_user = MagicMock(id_usuario=1)
    mock_check_user.return_value = mock_user

    # 1. Normal background trigger
    mock_log_repo.has_running_sync.return_value = False
    res = client.post("/api/v1/jira/sync", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert "iniciada en segundo plano" in res.json()["message"]

    # 2. Already running error
    mock_log_repo.has_running_sync.return_value = True
    res2 = client.post("/api/v1/jira/sync", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 400

    # 3. Wait mode success
    mock_log_repo.has_running_sync.return_value = False
    with patch('app.services.jira_sync_service.async_run_jira_sync', new_callable=AsyncMock) as mock_sync:
        res3 = client.post("/api/v1/jira/sync?wait=true", cookies={"session_id": sign_session_id(1)})
        assert res3.status_code == 200
        assert "completada con éxito" in res3.json()["message"]

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.log_repo')
def test_get_sync_logs(mock_log_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    mock_log = MagicMock()
    mock_log.id_log = 10
    mock_log.fecha_ejecucion = datetime.now()
    mock_log.tipo_sincronizacion = "MANUAL"
    mock_log.resultado = "SUCCESS"
    mock_log.tiempo_ejecucion_segundos = 12
    mock_log.issues_procesados = 45
    mock_log.detalle_error = None
    mock_log.ejecutado_por = "admin"

    mock_log_repo.get_recent.return_value = [mock_log]
    mock_log_repo.get_filtered_logs.return_value = [mock_log]

    # Unfiltered
    res = client.get("/api/v1/jira/sync/logs", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Filtered
    res2 = client.get("/api/v1/jira/sync/logs?tipo_sincronizacion=MANUAL&resultado=SUCCESS", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200
    assert len(res2.json()) == 1

@patch('app.api.v1.controllers.jira_controller.project_repo')
@patch('app.api.v1.controllers.jira_controller.issue_repo')
@patch('app.api.v1.controllers.jira_controller.calculate_and_save_kpis')
def test_jira_webhook_flows(mock_kpis, mock_issue_repo, mock_proj_repo):
    # 1. Empty payload
    res = client.post("/api/v1/jira/webhook", json={}, cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"

    # 2. Project not synced
    mock_proj_repo.get.return_value = None
    payload_unsynced = {
        "issue": {
            "id": "1001",
            "key": "TEST-1",
            "fields": {"project": {"id": "9999"}}
        }
    }
    res2 = client.post("/api/v1/jira/webhook", json=payload_unsynced, cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"

    # 3. Successful webhook sync
    db_proj = MagicMock(id_proyecto="PROJ-1")
    mock_proj_repo.get.return_value = db_proj
    mock_issue_repo.get_by_key.return_value = None
    mock_issue_repo.create.return_value = MagicMock()

    payload_ok = {
        "issue": {
            "id": "1001",
            "key": "TEST-1",
            "fields": {
                "summary": "Fix login bug",
                "status": {"name": "Done"},
                "project": {"id": "PROJ-1"},
                "created": "2026-01-01T10:00:00.000Z",
                "resolutiondate": "2026-01-02T10:00:00.000Z",
                "assignee": {"accountId": "acc123", "displayName": "Juan Perez"},
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "customfield_10028": 5.0
            }
        }
    }
    res3 = client.post("/api/v1/jira/webhook", json=payload_ok, cookies={"session_id": sign_session_id(1)})
    assert res3.status_code == 200
    assert res3.json()["status"] == "success"
    assert mock_kpis.called

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
def test_get_issue_transitions(mock_fetch, mock_creds, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {})

    mock_fetch.return_value = {
        "transitions": [
            {"id": "11", "name": "En Curso", "to": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}},
            {"id": "21", "name": "Finalizado", "to": {"name": "Done", "statusCategory": {"key": "done"}}}
        ]
    }

    res = client.get("/api/v1/jira/issues/TEST-1/transitions", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    data = res.json()
    assert data["issue_key"] == "TEST-1"
    assert len(data["transitions"]) == 2

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions')
@patch('app.datasources.jira_datasource.JiraDatasource.post_issue_transition')
@patch('app.datasources.jira_datasource.JiraDatasource.fetch_issue_details')
@patch('app.api.v1.controllers.jira_controller.issue_repo')
@patch('app.api.v1.controllers.jira_controller.calculate_and_save_kpis')
def test_execute_issue_transition_by_id_and_status(mock_kpis, mock_issue_repo, mock_details, mock_post, mock_fetch, mock_creds, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {})

    mock_fetch.return_value = {
        "transitions": [
            {"id": "31", "name": "En Curso", "to": {"name": "In Progress"}},
            {"id": "41", "name": "Finalizado", "to": {"name": "Done"}}
        ]
    }
    mock_post.return_value = True
    mock_details.return_value = {"fields": {"status": {"name": "Done"}}}

    db_issue = MagicMock(id_proyecto="PROJ-1", resolved_at=None)
    mock_issue_repo.get_by_key.return_value = db_issue

    # 1. Execute by target_status "finalizado"
    res = client.post("/api/v1/jira/issues/TEST-1/transitions", json={"target_status": "finalizado"}, cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["new_status"] == "Done"
    assert mock_post.called

    # 2. Execute with invalid target status
    res2 = client.post("/api/v1/jira/issues/TEST-1/transitions", json={"target_status": "No Existe"}, cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 400

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('app.datasources.jira_datasource.JiraDatasource.assign_issue')
@patch('app.datasources.jira_datasource.JiraDatasource.search_assignable_user')
@patch('app.api.v1.controllers.jira_controller.issue_repo')
def test_reassign_issue_single_and_bulk(mock_issue_repo, mock_search, mock_assign, mock_creds, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()
    mock_creds.return_value = ("https://jira.example.com", {})

    mock_assign.return_value = True
    mock_search.return_value = [{"accountId": "account_search_123"}]

    db_issue = MagicMock(id_proyecto="PROJ-1")
    mock_issue_repo.get_by_key.return_value = db_issue

    # 1. Single reassign
    res = client.put("/api/v1/jira/issues/TEST-1/assignee", json={"new_assignee": "Carlos Dev"}, cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 1b. Single reassign direct accountId
    res_direct = client.put("/api/v1/jira/issues/TEST-1/assignee", json={"new_assignee": "account_direct_12345678901234567890"}, cookies={"session_id": sign_session_id(1)})
    assert res_direct.status_code == 200

    # 1c. Single reassign user not found (404)
    mock_search.return_value = []
    res_404 = client.put("/api/v1/jira/issues/TEST-1/assignee", json={"new_assignee": "Inexistente"}, cookies={"session_id": sign_session_id(1)})
    assert res_404.status_code == 404

    # 1d. Single reassign Jira error (502)
    mock_search.return_value = [{"accountId": "acc-err"}]
    mock_assign.side_effect = Exception("Jira rejected")
    res_502 = client.put("/api/v1/jira/issues/TEST-1/assignee", json={"new_assignee": "Dev Error"}, cookies={"session_id": sign_session_id(1)})
    assert res_502.status_code == 502
    mock_assign.side_effect = None

    # 2. Bulk reassign with mixed success, not found, and exception
    mock_search.side_effect = [[{"accountId": "acc-1"}], []]
    payload_bulk = {
        "assignments": [
            {"issue_key": "TEST-1", "new_assignee": "Carlos Dev"},
            {"issue_key": "TEST-2", "new_assignee": "Inexistente"}
        ]
    }
    res2 = client.post("/api/v1/jira/issues/reassign-bulk", json=payload_bulk, cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200
    assert res2.json()["total_requested"] == 2
    assert res2.json()["total_successful"] == 1
