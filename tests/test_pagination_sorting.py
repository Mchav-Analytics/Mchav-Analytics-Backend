from unittest.mock import MagicMock, patch
import pytest
from fastapi import Request

# Import real functions to test their integration/parameter passing
from app.api.v1.endpoints.projects import get_projects, get_project_kpis, get_project_sprints
from app.api.v1.endpoints.jira import get_sync_logs
import app.models as models

@pytest.mark.anyio
@patch('app.api.v1.endpoints.projects.get_current_user_id')
@patch('app.api.v1.endpoints.projects.check_user_exists')
@patch('app.api.v1.endpoints.projects.project_repo')
async def test_get_projects_pagination_and_sorting(
    mock_project_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de proyectos transmita correctamente los parámetros de paginación y ordenamiento."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    # Ejecutamos el endpoint con parámetros no predeterminados
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
@patch('app.api.v1.endpoints.projects.get_current_user_id')
@patch('app.api.v1.endpoints.projects.check_user_exists')
@patch('app.api.v1.endpoints.projects.kpi_repo')
async def test_get_project_kpis_pagination_and_sorting(
    mock_kpi_repo,
    mock_check_user,
    mock_current_user
):
    """Prueba que el endpoint de KPIs ordene y pagine adecuadamente sobre la consulta SQLAlchemy."""
    mock_current_user.return_value = 1
    mock_db = MagicMock()
    mock_request = MagicMock(spec=Request)
    
    # Creamos un mock de la consulta SQLAlchemy (Query)
    mock_query = MagicMock()
    mock_kpi_repo.get_all_by_project.return_value = mock_query
    
    # Ejecutamos con parámetros
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
    
    # 1. Comprobar que se filtra por sprint
    mock_query.filter.assert_called_once()
    filtered_query = mock_query.filter.return_value
    
    # 2. Comprobar que se ordena por el campo correcto en forma descendente
    filtered_query.order_by.assert_called_once()
    # Obtenemos el argumento posicional pasado a order_by
    order_by_arg = filtered_query.order_by.call_args[0][0]
    assert "desc" in str(order_by_arg).lower()

    
    # 3. Comprobar que se aplican limit y offset a la consulta final
    ordered_query = filtered_query.order_by.return_value
    ordered_query.offset.assert_called_once_with(20)
    
    offset_query = ordered_query.offset.return_value
    offset_query.limit.assert_called_once_with(10)
    
    limit_query = offset_query.limit.return_value
    limit_query.all.assert_called_once()


@pytest.mark.anyio
@patch('app.api.v1.endpoints.projects.get_current_user_id')
@patch('app.api.v1.endpoints.projects.check_user_exists')
@patch('app.api.v1.endpoints.projects.sprint_repo')
async def test_get_project_sprints_pagination_and_sorting(
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
@patch('app.api.v1.endpoints.jira.get_current_user_id')
@patch('app.api.v1.endpoints.jira.check_user_exists')
@patch('app.api.v1.endpoints.jira.log_repo')
async def test_get_sync_logs_pagination(
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
