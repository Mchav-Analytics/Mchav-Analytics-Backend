import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from app.services import auth_service
from app.core.security import sign_session_id, verify_session_id

def test_generar_y_validar_estado_oauth():
    """Verifica que un token de estado CSRF generado se valide y consuma correctamente."""
    state = auth_service.generate_oauth_state()
    assert isinstance(state, str)
    assert len(state) > 10
    
    assert auth_service.validate_oauth_state(state) is True
    assert auth_service.validate_oauth_state(state) is False

def test_rechazar_estado_oauth_invalido():
    """Verifica que un estado no generado retorne False."""
    assert auth_service.validate_oauth_state("invalid_state_12345") is False

@patch('app.services.auth_service.CLIENT_ID', 'test_client_id_123')
def test_construir_url_oauth_jira_exitosa():
    """Verifica la construcción correcta de la URL de autorización con parámetros."""
    url = auth_service.build_jira_oauth_url("my_test_state")
    assert "https://auth.atlassian.com/authorize" in url
    assert "client_id=test_client_id_123" in url
    assert "state=my_test_state" in url

@patch('app.services.auth_service.CLIENT_ID', '')
def test_error_url_oauth_sin_client_id():
    """Verifica que si no hay CLIENT_ID configurado se lance una excepción 500."""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.build_jira_oauth_url("state")
    assert exc_info.value.status_code == 500

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_canjear_codigo_oauth_por_perfil_exitoso(mock_get, mock_post):
    """Verifica el canje exitoso de código OAuth por perfil de usuario de Jira."""
    mock_post_res = MagicMock(status_code=200)
    mock_post_res.json.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token"
    }
    mock_post.return_value = mock_post_res
    
    mock_res_resources = MagicMock(status_code=200)
    mock_res_resources.json.return_value = [{"id": "cloud_id_123", "name": "Mi Jira"}]
    
    mock_res_myself = MagicMock(status_code=200)
    mock_res_myself.json.return_value = {
        "accountId": "jira_acc_999",
        "emailAddress": "testuser@mchav.com",
        "displayName": "Test User"
    }
    
    mock_get.side_effect = [mock_res_resources, mock_res_myself]
    
    user_data = await auth_service.exchange_code_for_user_profile("mock_code")
    
    assert user_data["jira_account_id"] == "jira_acc_999"
    assert user_data["email"] == "testuser@mchav.com"
    assert user_data["nombre"] == "Test User"
    assert user_data["cloud_id"] == "cloud_id_123"

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
async def test_error_canjear_codigo_oauth_invalido(mock_post):
    """Verifica el manejo de error cuando Atlassian rechaza el código de autorización."""
    mock_post_res = MagicMock(status_code=400, text="invalid_grant")
    mock_post.return_value = mock_post_res
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.exchange_code_for_user_profile("invalid_code")
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_validar_credenciales_api_jira_exitoso(mock_get):
    """Verifica la validación correcta de API Token directo de Jira."""
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {
        "emailAddress": "api_user@mchav.com",
        "displayName": "API User"
    }
    mock_get.return_value = mock_res
    
    result = await auth_service.verify_jira_api_credentials(
        domain="https://empresa.atlassian.net",
        email="api_user@mchav.com",
        token="valid_token_123"
    )
    
    assert result["jira_domain"] == "https://empresa.atlassian.net"
    assert result["jira_email"] == "api_user@mchav.com"

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_rechazar_credenciales_api_jira_invalidas(mock_get):
    """Verifica que se lance 401 si las credenciales directas de Jira son inválidas."""
    mock_res = MagicMock(status_code=401)
    mock_get.return_value = mock_res
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.verify_jira_api_credentials(
            domain="https://empresa.atlassian.net",
            email="wrong@mchav.com",
            token="invalid_token"
        )
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_error_oauth_sin_recursos_jira(mock_get, mock_post):
    """Verifica que si el usuario de Atlassian no tiene recursos accesibles se lance error 400."""
    mock_post_res = MagicMock(status_code=200)
    mock_post_res.json.return_value = {"access_token": "acc", "refresh_token": "ref"}
    mock_post.return_value = mock_post_res
    
    mock_res_resources = MagicMock(status_code=200)
    mock_res_resources.json.return_value = []
    mock_get.return_value = mock_res_resources
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.exchange_code_for_user_profile("code_123")
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_error_servidor_recursos_jira(mock_get, mock_post):
    """Verifica error 500 cuando accesible-resources retorna 500."""
    mock_post_res = MagicMock(status_code=200)
    mock_post_res.json.return_value = {"access_token": "acc"}
    mock_post.return_value = mock_post_res
    
    mock_res_resources = MagicMock(status_code=500)
    mock_get.return_value = mock_res_resources
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.exchange_code_for_user_profile("code_123")
    assert exc_info.value.status_code == 500

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_error_obtener_perfil_usuario_jira(mock_get, mock_post):
    """Verifica error cuando /myself retorna 403."""
    mock_post_res = MagicMock(status_code=200)
    mock_post_res.json.return_value = {"access_token": "acc"}
    mock_post.return_value = mock_post_res
    
    mock_res_resources = MagicMock(status_code=200)
    mock_res_resources.json.return_value = [{"id": "cloud_123"}]
    
    mock_res_myself = MagicMock(status_code=403)
    mock_get.side_effect = [mock_res_resources, mock_res_myself, mock_res_myself]
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.exchange_code_for_user_profile("code_123")
    assert exc_info.value.status_code == 403

def test_firmar_y_verificar_sesion_hmac():
    """Verifica firmado y validación HMAC de sesión."""
    token = sign_session_id(99)
    assert "." in token
    verified_id = verify_session_id(token)
    assert verified_id == 99

def test_rechazar_firma_sesion_invalida():
    """Verifica firmas inválidas."""
    assert verify_session_id("99.invalid_signature") is None
    assert verify_session_id("") is None
    assert verify_session_id(None) is None
