import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

from app.core.security import get_current_user
from app.models.auth import User, Role

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="test@mchav.com", activo=True, rol=mock_role)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
@patch('httpx.AsyncClient.get')
def test_obtener_metricas_jira_exitoso(
    mock_httpx_get,
    mock_auth_creds,
    mock_check_user,
    mock_current_user
):
    """Verifica que /api/v1/jira/metrics retorne las 4 métricas agregadas."""
    mock_current_user.return_value = 1
    mock_check_user.return_value = MagicMock(id_usuario=1)
    mock_auth_creds.return_value = ("http://jira", {"Authorization": "Basic 123"})
    
    mock_res_projects = MagicMock(status_code=200)
    mock_res_projects.json.return_value = [{"id": "1"}, {"id": "2"}]
    
    mock_res_jql = MagicMock(status_code=200)
    mock_res_jql.json.return_value = {"total": 5}
    
    mock_httpx_get.side_effect = [mock_res_projects, mock_res_jql, mock_res_jql, mock_res_jql]
    
    response = client.get(
        "/api/v1/jira/metrics",
        cookies={"session_id": "1.mocked"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["active_projects"] == 2
    assert data["completed_tickets"] == 5
    assert data["in_progress_tickets"] == 5
    assert data["critical_bugs"] == 5

@patch('app.api.v1.controllers.jira_controller.project_repo')
@patch('app.api.v1.controllers.jira_controller.issue_repo')
@patch('app.api.v1.controllers.jira_controller.calculate_and_save_kpis')
def test_recibir_webhook_jira_exitoso(
    mock_calc_kpis,
    mock_issue_repo,
    mock_project_repo
):
    """Verifica la recepción de Webhooks enviadas por Jira."""
    mock_project = MagicMock(id_proyecto="10001")
    mock_project_repo.get.return_value = mock_project
    mock_issue_repo.get_by_key.return_value = None
    
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "10001",
            "key": "PROJ-10",
            "fields": {
                "summary": "Fix bug en login",
                "status": {"name": "In Progress"},
                "project": {"id": "10001"},
                "created": "2026-07-01T10:00:00.000+0000",
                "resolutiondate": None
            }
        }
    }
    
    response = client.post("/api/v1/jira/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["issue"] == "PROJ-10"
    mock_issue_repo.create.assert_called_once()
    mock_calc_kpis.assert_called_once()

@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.run_jira_sync_task')
def test_iniciar_sincronizacion_jira_segundo_plano(mock_sync_task, mock_check_user, mock_user_id):
    """Verifica que /api/v1/jira/sync encole la tarea asíncrona en segundo plano."""
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock(id_usuario=1)
    
    response = client.post(
        "/api/v1/jira/sync",
        cookies={"session_id": "1.mocked"}
    )
    assert response.status_code == 200
    assert "Sincronización iniciada" in response.json()["message"]

def test_ignorar_webhook_sin_ticket():
    """Verifica ignorar webhook si no contiene información de issue."""
    response = client.post("/api/v1/jira/webhook", json={"webhookEvent": "jira:test"})
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

@patch('app.api.v1.controllers.jira_controller.project_repo.get', return_value=None)
def test_ignorar_webhook_proyecto_no_registrado(mock_get_proj):
    """Verifica ignorar webhook si el proyecto del issue no está guardado en BD."""
    payload = {
        "issue": {
            "id": "999",
            "key": "UNKNOWN-1",
            "fields": {"project": {"id": "999"}}
        }
    }
    response = client.post("/api/v1/jira/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
