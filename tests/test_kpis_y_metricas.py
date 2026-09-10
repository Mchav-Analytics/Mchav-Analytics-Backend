import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.project_schema import ProjectResponse

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

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.kpi_repo')
def test_obtener_kpis_de_proyecto(mock_kpi_repo, mock_check_user, mock_current_user):
    """Verifica la consulta de KPIs de un proyecto en /api/v1/projects/{proyecto_id}/kpis."""
    mock_current_user.return_value = 1
    mock_query = MagicMock()
    mock_kpi_repo.get_all_by_project.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_kpi = {
        "id_kpi": 1,
        "id_proyecto": "PROJ-1",
        "velocity_total_sp": 15.0,
        "throughput_issues": 5,
        "lead_time_promedio_dias": 4.5,
        "cycle_time_promedio_dias": 2.5
    }
    mock_query.all.return_value = [mock_kpi]
    
    response = client.get(
        "/api/v1/projects/PROJ-1/kpis",
        cookies={"session_id": "1.mocked"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["velocity_total_sp"] == 15.0

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.project_repo')
def test_obtener_lista_proyectos_endpoint(mock_project_repo, mock_check_user, mock_user_id):
    """Verifica el listado de proyectos registrados en la base de datos."""
    mock_user_id.return_value = 1
    mock_project = ProjectResponse(
        id_proyecto="P1",
        key_proyecto="P1",
        nombre="Proyecto Uno",
        descripcion="Desc",
        mapping_estados={}
    )
    mock_project_repo.get_multi.return_value = [mock_project]
    
    response = client.get("/api/v1/projects/", cookies={"session_id": "1.mocked"})
    assert response.status_code == 200
    assert len(response.json()) == 1

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.sprint_repo')
def test_obtener_sprints_de_proyecto_endpoint(mock_sprint_repo, mock_check_user, mock_user_id):
    """Verifica el listado de sprints de un proyecto."""
    mock_user_id.return_value = 1
    mock_sprint_repo.get_by_project.return_value = [{"id_sprint": "S-1", "nombre": "Sprint 1"}]
    
    response = client.get("/api/v1/projects/PROJ-1/sprints", cookies={"session_id": "1.mocked"})
    assert response.status_code == 200
    assert len(response.json()) == 1

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.mapping_repo')
def test_guardar_reglas_mapeo_de_proyecto(mock_mapping_repo, mock_check_user, mock_user_id):
    """Verifica guardar nuevas reglas de mapeo de estados."""
    mock_user_id.return_value = 1
    payload = [
        {"estado_jira": "Doing", "estado_base": "IN_PROGRESS"}
    ]
    response = client.post("/api/v1/projects/PROJ-1/mappings", json=payload, cookies={"session_id": "1.mocked"})
    assert response.status_code == 200
    mock_mapping_repo.delete_by_project.assert_called_once()
