from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.cache import ShortLivedCache
from app.core.database import Base
from app.repositories import project_repo, sprint_repo, issue_repo, transition_repo
from app.api.v1.controllers.projects_controller import get_projects, get_project_kpis, get_project_sprints
from app.api.v1.controllers.jira_controller import get_sync_logs
from app.main import app

from app.core.security import get_current_user
from app.models.auth import User, Role

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=55, email="test@mchav.com", activo=True, rol=mock_role)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture(name="db_session")
def fixture_db_session():
    """Configura una base de datos SQLite en memoria limpia para cada test."""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_cache_memoria_operaciones_basicas():
    """Prueba que ShortLivedCache realice correctamente get, set y clear."""
    cache = ShortLivedCache(ttl_seconds=10)
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"
    
    cache.clear()
    assert cache.get("foo") is None

def test_cache_memoria_expiracion_tiempo_vida():
    """Prueba que el valor de ShortLivedCache expire una vez pasado el TTL."""
    cache = ShortLivedCache(ttl_seconds=5)
    cache.set("hello", "world")
    assert cache.get("hello") == "world"
    
    future = datetime.now() + timedelta(seconds=6)
    with patch('app.core.cache.datetime') as mock_datetime:
        mock_datetime.now.return_value = future
        assert cache.get("hello") is None

@pytest.mark.anyio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('httpx.AsyncClient.get')
async def test_obtener_metricas_jira_uso_de_cache(mock_httpx_get, mock_check_user, mock_current_user):
    """Verifica que el endpoint /metrics use ShortLivedCache en llamadas repetidas."""
    from app.api.v1.controllers.jira_controller import metrics_cache
    metrics_cache.clear()
    
    mock_current_user.return_value = 55
    mock_user = MagicMock()
    mock_user.id_usuario = 55
    mock_user.cloud_id = "cloud-abc"
    mock_user.access_token = "token-123"
    mock_check_user.return_value = mock_user
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"total": 5}
    mock_httpx_get.return_value = mock_response
    
    response1 = client.get("/api/v1/jira/metrics", cookies={"session_id": "55.mock"})
    assert response1.status_code == 200
    assert response1.json()["completed_tickets"] == 5
    assert mock_httpx_get.call_count == 4
    
    mock_httpx_get.reset_mock()
    
    response2 = client.get("/api/v1/jira/metrics", cookies={"session_id": "55.mock"})
    assert response2.status_code == 200
    assert response2.json()["completed_tickets"] == 5
    mock_httpx_get.assert_not_called()

def test_persistencia_crud_proyecto_y_sprint(db_session):
    """Verifica la persistencia básica (creación, lectura, actualización y borrado) de Proyectos y Sprints."""
    proyecto_in = {"id_proyecto": "P-1", "key_proyecto": "KEY-1", "nombre": "Proyecto Prueba"}
    proyecto = project_repo.create(db_session, obj_in=proyecto_in)
    
    assert proyecto.id_proyecto == "P-1"
    assert proyecto.nombre == "Proyecto Prueba"
    
    sprint_in = {
        "id_sprint": "S-1",
        "id_proyecto": "P-1",
        "nombre": "Sprint 1",
        "estado": "active",
        "fecha_inicio": datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    }
    sprint = sprint_repo.create(db_session, obj_in=sprint_in)
    
    assert sprint.id_sprint == "S-1"
    assert sprint.id_proyecto == "P-1"
    
    db_project = project_repo.get(db_session, id="P-1")
    assert db_project is not None
    assert len(db_project.sprints) == 1
    assert db_project.sprints[0].id_sprint == "S-1"
    
    project_repo.update(db_session, db_obj=db_project, obj_in={"nombre": "Proyecto Renombrado"})
    updated_project = project_repo.get(db_session, id="P-1")
    assert updated_project.nombre == "Proyecto Renombrado"
    
    project_repo.remove(db_session, id="P-1")
    assert project_repo.get(db_session, id="P-1") is None
    assert sprint_repo.get(db_session, id="S-1") is None

def test_persistencia_crud_ticket_y_transiciones(db_session):
    """Verifica la persistencia de Issues y Transiciones, incluyendo relaciones."""
    project_repo.create(db_session, obj_in={"id_proyecto": "P-2", "key_proyecto": "KEY-2", "nombre": "Proj 2"})
    sprint_repo.create(db_session, obj_in={"id_sprint": "S-2", "id_proyecto": "P-2", "nombre": "Sprint 2", "estado": "active"})
    
    issue_in = {
        "id_jira": "ISS-99",
        "key_issue": "KEY-2-99",
        "id_proyecto": "P-2",
        "id_sprint": "S-2",
        "summary": "Implementar login",
        "status_actual": "In Progress",
        "story_points": 3.0,
        "created_at": datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        "resolved_at": None
    }
    issue = issue_repo.create(db_session, obj_in=issue_in)
    assert issue.id_jira == "ISS-99"
    assert issue.story_points == 3.0
    
    trans_in = {
        "id_jira": "ISS-99",
        "estado_anterior": "To Do",
        "estado_nuevo": "In Progress",
        "fecha_cambio": datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    }
    transition = transition_repo.create(db_session, obj_in=trans_in)
    assert transition.id_transicion is not None
    assert transition.id_jira == "ISS-99"
    
    db_issue = issue_repo.get(db_session, id="ISS-99")
    assert db_issue is not None
    assert len(db_issue.transiciones) == 1
    assert db_issue.transiciones[0].estado_nuevo == "In Progress"

@pytest.mark.anyio
@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.project_repo')
async def test_paginacion_y_ordenamiento_proyectos(
    mock_project_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de proyectos transmita correctamente los parámetros de paginación y ordenamiento."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    await get_projects(
        request=mock_request,
        limit=15,
        offset=30,
        sort="nombre",
        order="desc",
        db=mock_db
    )
    
    mock_project_repo.get_multi.assert_called_once_with(
        mock_db,
        skip=30,
        limit=15,
        sort="nombre",
        order="desc"
    )

@pytest.mark.anyio
@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.kpi_repo')
async def test_paginacion_y_ordenamiento_kpis(
    mock_kpi_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de KPIs ordene y pagine adecuadamente sobre la consulta SQLAlchemy."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    mock_query = MagicMock()
    mock_kpi_repo.get_all_by_project.return_value = mock_query
    
    await get_project_kpis(
        proyecto_id="PROJ-1",
        request=mock_request,
        sprint_id="S-123",
        limit=10,
        offset=20,
        sort="cycle_time_promedio_dias",
        order="desc",
        db=mock_db
    )
    
    mock_query.filter.assert_called_once()
    filtered_query = mock_query.filter.return_value
    
    filtered_query.order_by.assert_called_once()
    order_by_arg = filtered_query.order_by.call_args[0][0]
    assert "desc" in str(order_by_arg).lower()
    
    ordered_query = filtered_query.order_by.return_value
    ordered_query.offset.assert_called_once_with(20)
    
    offset_query = ordered_query.offset.return_value
    offset_query.limit.assert_called_once_with(10)
    
    limit_query = offset_query.limit.return_value
    limit_query.all.assert_called_once()

@pytest.mark.anyio
@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.sprint_repo')
async def test_paginacion_y_ordenamiento_sprints(
    mock_sprint_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de sprints pase correctamente los parámetros al repositorio de sprints."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    await get_project_sprints(
        proyecto_id="PROJ-1",
        request=mock_request,
        limit=25,
        offset=5,
        sort="nombre",
        order="asc",
        db=mock_db
    )
    
    mock_sprint_repo.get_by_project.assert_called_once_with(
        mock_db,
        "PROJ-1",
        skip=5,
        limit=25,
        sort="nombre",
        order="asc"
    )

@pytest.mark.anyio
@patch('app.api.v1.controllers.jira_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.jira_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.jira_controller.log_repo')
async def test_paginacion_logs_sincronizacion(
    mock_log_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de logs de sincronización pase correctamente la paginación a get_recent."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    await get_sync_logs(
        request=mock_request,
        limit=12,
        offset=24,
        db=mock_db
    )
    
    mock_log_repo.get_recent.assert_called_once_with(
        mock_db,
        skip=24,
        limit=12
    )
