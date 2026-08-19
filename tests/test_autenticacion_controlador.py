import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user
from app.models.auth import User, Role

client = TestClient(app)

def test_redireccionar_login_atlassian():
    """Verifica que /api/v1/auth/login genere la redirección hacia Atlassian."""
    with patch('app.services.auth_service.CLIENT_ID', 'mock_client'):
        response = client.get("/api/v1/auth/login", follow_redirects=False)
        assert response.status_code == 307
        assert "https://auth.atlassian.com/authorize" in response.headers["location"]

@patch('app.api.v1.controllers.auth_controller.auth_service.validate_oauth_state')
@patch('app.api.v1.controllers.auth_controller.auth_service.exchange_code_for_user_profile')
@patch('app.api.v1.controllers.auth_controller.user_repo')
def test_procesar_callback_oauth_exitoso(mock_repo, mock_exchange, mock_validate):
    """Verifica el procesamiento exitoso del Callback de OAuth."""
    mock_validate.return_value = True
    mock_exchange.return_value = {
        "jira_account_id": "acc_123",
        "email": "user@mchav.com",
        "nombre": "User Test",
        "access_token": "token_abc"
    }
    
    mock_user = MagicMock()
    mock_user.id_usuario = 42
    mock_repo.get_by_jira_account_id.return_value = mock_user
    mock_repo.update.return_value = mock_user
    
    response = client.get(
        "/api/v1/auth/callback?code=mock_code&state=mock_state",
        follow_redirects=False
    )
    
    assert response.status_code in (302, 307)
    assert "/dashboard" in response.headers["location"]
    assert "session_id" in response.cookies

def test_rechazar_callback_estado_invalido():
    """Verifica error 400 si el estado CSRF en el callback es inválido."""
    with patch('app.api.v1.controllers.auth_controller.auth_service.validate_oauth_state', return_value=False):
        response = client.get("/api/v1/auth/callback?code=code&state=invalid")
        assert response.status_code == 400
        assert "Estado (State) inválido" in response.json()["detail"]

@patch('app.api.v1.controllers.auth_controller.verify_password')
@patch('app.api.v1.controllers.auth_controller.user_repo')
def test_iniciar_sesion_usuario_local(mock_user_repo, mock_verify):
    """Verifica la autenticación exitosa en /api/v1/auth/token con usuario y contraseña."""
    mock_verify.return_value = True
    mock_user = MagicMock()
    mock_user.id_usuario = 10
    mock_user.email = "admin@mchav.com"
    mock_user.password_hash = "$2b$12$mockhash"
    mock_user.activo = True
    
    with patch('app.api.v1.controllers.auth_controller.get_db') as mock_db_dep:
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_user
        mock_db_dep.return_value = mock_db
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin@mchav.com", "password": "123456"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

@patch('app.api.v1.controllers.auth_controller.auth_service.verify_jira_api_credentials', new_callable=AsyncMock)
@patch('app.api.v1.controllers.auth_controller.user_repo')
def test_guardar_credenciales_jira_api(mock_user_repo, mock_verify):
    """Verifica guardar y validar credenciales directas de API Token de Jira usando dependency override."""
    mock_role = Role(nombre_rol="Administrador", scopes="jira:sync")
    mock_user = User(id_usuario=1, email="admin@mchav.com", activo=True, rol=mock_role)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    mock_verify.return_value = {
        "jira_domain": "https://beltrancamilo592.atlassian.net",
        "jira_email": "test@mchav.com",
        "jira_api_token": "token_abc"
    }
    
    payload = {
        "jira_domain": "https://beltrancamilo592.atlassian.net",
        "jira_email": "test@mchav.com",
        "jira_api_token": "token_abc"
    }
    
    response = client.post("/api/v1/auth/jira-credentials", json=payload)
    
    # Limpiar overrides
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_user_repo.update.assert_called_once()
