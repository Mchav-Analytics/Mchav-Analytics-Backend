import pytest
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

def test_obtener_jql_extraccion_delta():
    """Verifica que el endpoint de extracción delta devuelva el JQL parametrizado."""
    response = client.get("/api/v1/jql/extraction-delta?project_key=MCHAV")
    assert response.status_code == 200
    data = response.json()
    assert "project = 'MCHAV'" in data["jql_executed"]
    assert "metrics" in data

def test_obtener_jql_velocidad_y_rendimiento():
    """Verifica que el endpoint de velocity/throughput devuelva el JQL parametrizado."""
    response = client.get("/api/v1/jql/velocity-throughput?project_key=MCHAV&status_done=Done&sprint_id=12")
    assert response.status_code == 200
    data = response.json()
    assert "project = 'MCHAV'" in data["jql_executed"]
    assert "sprint = 12" in data["jql_executed"]

def test_obtener_jql_tiempos_de_ciclo():
    """Verifica que el endpoint de tiempos de ciclo devuelva el JQL parametrizado."""
    response = client.get("/api/v1/jql/time-cycles?project_key=MCHAV&start_date=2026-01-01&end_date=2026-07-30")
    assert response.status_code == 200
    data = response.json()
    assert "project = 'MCHAV'" in data["jql_executed"]
    assert "2026-01-01" in data["jql_executed"]
