import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

from app.core.security import get_current_user, sign_session_id
from app.models.auth import User, Role

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="test@mchav.com", activo=True, rol=mock_role)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.sprint_repo')
def test_obtener_sprints_de_proyecto(mock_sprint_repo, mock_check_user, mock_user_id):
    """Verifica la consulta del listado de sprints de un proyecto."""
    mock_user_id.return_value = 1
    mock_sprint_repo.get_by_project.return_value = [
        {"id_sprint": "100", "nombre": "Sprint 1", "estado": "closed"}
    ]
    
    response = client.get(
        "/api/v1/projects/PROJ-1/sprints",
        cookies={"session_id": sign_session_id(1)}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.issue_repo')
@patch('app.api.v1.controllers.projects_controller.transition_repo')
def test_obtener_estados_unicos_de_proyecto(mock_trans_repo, mock_issue_repo, mock_check_user, mock_user_id):
    """Verifica la obtención de lista única de nombres de estados para mapeos."""
    mock_user_id.return_value = 1
    mock_issue_repo.get_distinct_statuses_by_project.return_value = [("To Do",), ("In Progress",)]
    mock_trans_repo.get_distinct_new_statuses_by_project.return_value = [("Done",)]
    mock_trans_repo.get_distinct_prev_statuses_by_project.return_value = [("To Do",)]
    
    response = client.get(
        "/api/v1/projects/PROJ-1/statuses",
        cookies={"session_id": sign_session_id(1)}
    )
    assert response.status_code == 200
    statuses = response.json()
    assert "Done" in statuses
    assert "In Progress" in statuses

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.mapping_repo')
def test_obtener_reglas_mapeo_de_proyecto(mock_mapping_repo, mock_check_user, mock_user_id):
    """Verifica la consulta de las reglas de mapeo activas de un proyecto."""
    mock_user_id.return_value = 1
    mock_mapping_repo.get_by_project.return_value = [
        {"id_proyecto": "PROJ-1", "estado_jira": "Doing", "estado_base": "IN_PROGRESS"}
    ]
    
    response = client.get(
        "/api/v1/projects/PROJ-1/mappings",
        cookies={"session_id": sign_session_id(1)}
    )
    assert response.status_code == 200
    assert response.json()[0]["estado_jira"] == "Doing"
