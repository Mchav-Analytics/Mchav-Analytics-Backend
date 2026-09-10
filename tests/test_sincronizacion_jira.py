import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services import jira_sync_service
from app.models.auth import User
from app.models.jira import Proyecto, Sprint, Issue

def test_delegar_credenciales_jira_a_datasource():
    """Verifica que la función delegadora get_jira_auth_credentials invoque JiraDatasource."""
    mock_db = MagicMock()
    mock_user = MagicMock()
    
    with patch('app.datasources.jira_datasource.JiraDatasource.get_auth_credentials') as mock_datasource:
        mock_datasource.return_value = ("https://api.atlassian.com/ex/jira/cloud_123/rest/api/3", {"Authorization": "Bearer mock"})
        url, headers = jira_sync_service.get_jira_auth_credentials(mock_db, mock_user)
        
        assert "https://api.atlassian.com" in url
        assert "Authorization" in headers

@pytest.mark.asyncio
async def test_refrescar_token_oauth_usuario_exitoso():
    """Verifica el refresco de token OAuth cuando el servidor retorna 200."""
    mock_db = MagicMock()
    mock_user = MagicMock(refresh_token="old_refresh", id_usuario=1)
    
    mock_client = MagicMock()
    mock_client.post = AsyncMock()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token"
    }
    mock_client.post.return_value = mock_response
    
    with patch('app.repositories.user_repo.update') as mock_update:
        await jira_sync_service.refresh_user_token(mock_db, mock_user, mock_client)
        mock_update.assert_called_once()

@pytest.mark.asyncio
async def test_ignorar_refresco_sin_refresh_token():
    """Verifica que si el usuario no tiene refresh_token no haga ninguna llamada."""
    mock_db = MagicMock()
    mock_user = MagicMock(refresh_token=None)
    mock_client = MagicMock()
    mock_client.post = AsyncMock()
    
    await jira_sync_service.refresh_user_token(mock_db, mock_user, mock_client)
    mock_client.post.assert_not_called()

@pytest.mark.asyncio
async def test_sincronizar_y_guardar_proyectos():
    """Verifica la sincronización e inserción de proyectos en base de datos."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_user = MagicMock()
    
    projects_raw = [
        {"id": "10001", "key": "PROJ1", "name": "Proyecto Uno"},
        {"id": "10002", "key": "PROJ2", "name": "Proyecto Dos"}
    ]
    
    with patch('app.datasources.jira_datasource.JiraDatasource.fetch_projects', new_callable=AsyncMock, return_value=projects_raw), \
         patch('app.repositories.project_repo.get_by_key', return_value=None), \
         patch('app.repositories.project_repo.create') as mock_create:
        
        mock_create.side_effect = lambda db, obj_in: Proyecto(
            id_proyecto=obj_in["id_proyecto"],
            key_proyecto=obj_in["key_proyecto"],
            nombre=obj_in["nombre"]
        )
        
        result = await jira_sync_service.sync_projects(mock_client, "http://jira", {}, mock_db, mock_user)
        assert len(result) == 2
        assert mock_create.call_count == 2

@pytest.mark.asyncio
async def test_sincronizar_tickets_y_tableros_proyecto_flujo_completo():
    """Verifica el flujo completo de sincronización de tableros, sprints, tickets y changelogs de un proyecto."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    project = Proyecto(id_proyecto="101", key_proyecto="P1", nombre="Proyecto P1")
    
    boards_raw = {
        "values": [
            {"id": 50, "location": {"projectKey": "P1"}}
        ]
    }
    
    sprints_raw = [
        {
            "id": 200,
            "name": "Sprint 1",
            "state": "closed",
            "startDate": "2026-07-01T00:00:00.000Z",
            "endDate": "2026-07-14T00:00:00.000Z",
            "completeDate": "2026-07-14T00:00:00.000Z"
        }
    ]
    
    issues_page1 = {
        "total": 1,
        "issues": [
            {
                "id": "10001",
                "key": "P1-1",
                "fields": {
                    "summary": "Implementar Login",
                    "status": {"name": "Done"},
                    "created": "2026-07-01T10:00:00.000Z",
                    "resolutiondate": "2026-07-05T12:00:00.000Z",
                    "customfield_10020": [{"id": 200}],
                    "sprint": {"id": 200}
                },
                "changelog": {
                    "histories": [
                        {
                            "created": "2026-07-02T10:00:00.000Z",
                            "items": [
                                {
                                    "field": "status",
                                    "fromString": "To Do",
                                    "toString": "In Progress"
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
    
    with patch('app.datasources.jira_datasource.JiraDatasource.fetch_boards_for_project', new_callable=AsyncMock, return_value=boards_raw), \
         patch('app.datasources.jira_datasource.JiraDatasource.fetch_board_sprints', new_callable=AsyncMock, return_value={"values": sprints_raw}), \
         patch('app.datasources.jira_datasource.JiraDatasource.fetch_issues_jql', new_callable=AsyncMock, return_value=issues_page1), \
         patch('app.repositories.sprint_repo.get_by_id_sprint', return_value=None), \
         patch('app.repositories.sprint_repo.create') as mock_sprint_create, \
         patch('app.repositories.issue_repo.get_by_key', return_value=None), \
         patch('app.repositories.issue_repo.create') as mock_issue_create, \
         patch('app.repositories.transition_repo.get_existing', return_value=None), \
         patch('app.repositories.transition_repo.delete_by_issue') as mock_trans_del, \
         patch('app.repositories.transition_repo.create') as mock_trans_create:
        
        mock_issue_create.return_value = Issue(id_jira="10001", key_issue="P1-1")
        
        total_issues = await jira_sync_service.sync_issues_for_project(
            mock_client, "http://jira", "http://agile", {}, mock_db, project
        )
        
        assert total_issues == 1
        assert mock_sprint_create.call_count >= 1
        mock_issue_create.assert_called_once()
        mock_trans_create.assert_called_once()

@patch('app.services.jira_sync_service.SessionLocal')
@patch('app.services.jira_sync_service.user_repo')
@patch('app.services.jira_sync_service.log_repo')
@patch('app.services.jira_sync_service.sync_projects', new_callable=AsyncMock)
@patch('app.services.jira_sync_service.sync_issues_for_project', new_callable=AsyncMock)
@patch('app.services.jira_sync_service.calculate_and_save_kpis')
def test_ejecutar_tarea_etl_sincronizacion_jira_exitosa(
    mock_calc_kpis,
    mock_sync_issues,
    mock_sync_projects,
    mock_log_repo,
    mock_user_repo,
    mock_session_cls
):
    """Verifica la ejecución del flujo ETL completo run_jira_sync_task."""
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    
    mock_user = User(id_usuario=1, email="admin@mchav.com")
    mock_user_repo.get.return_value = mock_user
    
    mock_log = MagicMock(id_log=10)
    mock_log_repo.create.return_value = mock_log
    
    proj1 = Proyecto(id_proyecto="101", key_proyecto="P1", nombre="Proyecto P1")
    mock_sync_projects.return_value = [proj1]
    mock_sync_issues.return_value = 15
    
    with patch('app.datasources.jira_datasource.JiraDatasource.get_auth_credentials', return_value=("http://jira", {})):
        jira_sync_service.run_jira_sync_task(user_id=1)
        
        mock_log_repo.create.assert_called_once()
        assert mock_log_repo.update.call_count >= 1

@patch('app.services.jira_sync_service.SessionLocal')
@patch('app.services.jira_sync_service.user_repo')
@patch('app.services.jira_sync_service.log_repo')
def test_ignorar_tarea_sincronizacion_usuario_no_existente(
    mock_log_repo,
    mock_user_repo,
    mock_session_cls
):
    """Verifica el retorno temprano si el usuario no existe en la base de datos."""
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_user_repo.get.return_value = None
    
    jira_sync_service.run_jira_sync_task(user_id=999)
    
    mock_log_repo.create.assert_not_called()
