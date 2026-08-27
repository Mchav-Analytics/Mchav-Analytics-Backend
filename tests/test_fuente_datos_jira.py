import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.datasources.jira_datasource import JiraDatasource
from app.models.auth import User

def test_obtener_credenciales_jira_desde_env():
    """Verifica autenticación por variables de entorno JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN."""
    mock_db = MagicMock()
    mock_user = MagicMock(cloud_id=None, access_token=None)
    
    with patch('os.getenv') as mock_env:
        mock_env.side_effect = lambda key, default="": {
            "JIRA_DOMAIN": "https://mi-empresa.atlassian.net",
            "JIRA_EMAIL": "admin@empresa.com",
            "JIRA_API_TOKEN": "secret_token_123"
        }.get(key, default)
        
        base_url, headers = JiraDatasource.get_auth_credentials(mock_db, mock_user)
        assert base_url == "https://mi-empresa.atlassian.net/rest/api/3"
        assert "Authorization" in headers
        assert "Basic " in headers["Authorization"]

def test_obtener_credenciales_jira_oauth_fallback():
    """Verifica autenticación por OAuth 2.0 (Bearer token) si no hay credenciales directas en env."""
    mock_db = MagicMock()
    user = User(cloud_id="cloud_99", access_token="oauth_token_xyz")
    
    with patch('os.getenv', return_value=""):
        base_url, headers = JiraDatasource.get_auth_credentials(mock_db, user)
        assert base_url == "https://api.atlassian.com/ex/jira/cloud_99/rest/api/3"
        assert headers["Authorization"] == "Bearer oauth_token_xyz"

def test_error_sin_credenciales_jira():
    """Verifica que se lance una excepción si no hay ninguna credencial válida."""
    mock_db = MagicMock()
    user = User(cloud_id=None, access_token=None)
    
    with patch('os.getenv', return_value=""):
        with pytest.raises(Exception) as exc_info:
            JiraDatasource.get_auth_credentials(mock_db, user)
        assert "No hay credenciales OAuth 2.0 ni de sistema configuradas en Jira" in str(exc_info.value)

@pytest.mark.asyncio
async def test_descargar_lista_proyectos_jira_exitoso():
    """Verifica la descarga de proyectos mediante el cliente HTTP de httpx."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = [{"id": "1", "key": "P1"}]
    mock_client.get.return_value = mock_res
    
    projects = await JiraDatasource.fetch_projects(mock_client, "http://jira", {})
    assert len(projects) == 1
    assert projects[0]["key"] == "P1"

@pytest.mark.asyncio
async def test_consultar_issues_jql_estrategia_3_capas():
    """Verifica la estrategia de 3 capas al consultar issues por JQL."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    
    res_post = MagicMock(status_code=404)
    res_get = MagicMock(status_code=200)
    res_get.json.return_value = {"issues": [{"id": "101", "key": "P1-1"}]}
    
    mock_client.post.return_value = res_post
    mock_client.get.return_value = res_get
    
    data = await JiraDatasource.fetch_issues_jql(mock_client, "http://jira", {}, "project = P1")
    assert "issues" in data
    assert data["issues"][0]["key"] == "P1-1"

@pytest.mark.asyncio
async def test_error_descargar_proyectos_servidor():
    """Verifica excepción cuando fetch_projects retorna status_code HTTP 500."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_res = MagicMock(status_code=500, text="Internal Server Error")
    mock_client.get.return_value = mock_res
    
    with pytest.raises(Exception) as exc_info:
        await JiraDatasource.fetch_projects(mock_client, "http://jira", {})
    assert "Error al obtener proyectos" in str(exc_info.value)

@pytest.mark.asyncio
async def test_consultar_issues_jql_metodo_post_exitoso():
    """Verifica que si GET /search/jql falla pero POST /search/jql retorna 200 se use el POST."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    
    mock_get_res = MagicMock(status_code=404)
    mock_post_res = MagicMock(status_code=200)
    mock_post_res.json.return_value = {"issues": [{"id": "2", "key": "P1-2"}]}
    
    mock_client.get.return_value = mock_get_res
    mock_client.post.return_value = mock_post_res
    
    data = await JiraDatasource.fetch_issues_jql(mock_client, "http://jira", {}, "project = P1")
    assert data["issues"][0]["key"] == "P1-2"

@pytest.mark.asyncio
async def test_descargar_tableros_de_proyecto():
    """Verifica la descarga de tableros por proyecto."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {"values": [{"id": 10}]}
    mock_client.get.return_value = mock_res
    
    data = await JiraDatasource.fetch_boards_for_project(mock_client, "http://agile", {}, "P1")
    assert len(data["values"]) == 1

@pytest.mark.asyncio
async def test_descargar_sprints_de_tablero():
    """Verifica la descarga de sprints de un tablero."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {"values": [{"id": 100}]}
    mock_client.get.return_value = mock_res
    
    data = await JiraDatasource.fetch_board_sprints(mock_client, "http://agile", {}, 10)
    assert len(data["values"]) == 1

@pytest.mark.asyncio
async def test_descargar_historial_transiciones_ticket():
    """Verifica la descarga del changelog de un ticket."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {"values": [{"id": "trans_1"}]}
    mock_client.get.return_value = mock_res
    
    data = await JiraDatasource.fetch_issue_changelog(mock_client, "http://jira", {}, "P1-1")
    assert len(data["values"]) == 1
