# tests/test_transicion_estado_jira.py
# Pruebas unitarias para el endpoint de transiciones bidireccionales de estado en Jira Cloud

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
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
def test_get_issue_transitions_success(
    mock_auth_creds,
    mock_check_user,
    mock_current_user
):
    mock_current_user.return_value = 1
    mock_check_user.return_value = MagicMock(id_usuario=1)
    mock_auth_creds.return_value = ("https://jira.example.com/rest/api/3", {"Authorization": "Basic 123"})

    mock_transitions = {
        "transitions": [
            {"id": "11", "name": "En Progreso", "to": {"name": "En Progreso"}},
            {"id": "21", "name": "En Revisión", "to": {"name": "En Revisión"}},
            {"id": "31", "name": "Finalizado", "to": {"name": "Listo"}}
        ]
    }
    
    with patch("app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_transitions
        res = client.get("/api/v1/jira/issues/MCHAV-101/transitions")
        assert res.status_code == 200
        data = res.json()
        assert "transitions" in data
        assert len(data["transitions"]) == 3


@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.get_jira_auth_credentials')
def test_transition_issue_success(
    mock_auth_creds,
    mock_check_user,
    mock_current_user
):
    mock_current_user.return_value = 1
    mock_check_user.return_value = MagicMock(id_usuario=1)
    mock_auth_creds.return_value = ("https://jira.example.com/rest/api/3", {"Authorization": "Basic 123"})

    mock_transitions = {
        "transitions": [
            {"id": "31", "name": "Finalizado", "to": {"name": "Listo"}}
        ]
    }
    
    with patch("app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions", new_callable=AsyncMock) as mock_fetch, \
         patch("app.datasources.jira_datasource.JiraDatasource.post_issue_transition", new_callable=AsyncMock) as mock_post:
        
        mock_fetch.return_value = mock_transitions
        mock_post.return_value = True
        
        res = client.post("/api/v1/jira/issues/MCHAV-101/transition", json={
            "target_status": "Listo",
            "transition_id": "31"
        })
        
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["issue_key"] == "MCHAV-101"
        assert "actualizado" in data["message"]
