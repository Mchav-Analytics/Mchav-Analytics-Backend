import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.responses import Response
from app.api.v1.controllers.auth_controller import (
    get_current_user_info,
    get_jira_credentials,
    save_jira_credentials,
    login_post,
    login,
    callback,
    post_login_local,
    login_local,
    logout,
    JiraCredentialsPayload,
    MockLoginPayload,
    LoginPayload
)
import app.models as models

@pytest.mark.asyncio
async def test_auth_me_and_jira_credentials():
    user = MagicMock(
        id_usuario=1, email="test@mchav.com", nombre="Test", id_rol=1, activo=True,
        rol=MagicMock(nombre_rol="Administrador"), jira_account_id="A1", cloud_id="C1",
        jira_domain="d.atlassian.net", jira_email="test@mchav.com", api_token_vinculado=True,
        jira_api_token="enc:token"
    )

    info = await get_current_user_info(user)
    assert info["email"] == "test@mchav.com"
    assert info["rol"] == "Administrador"

    creds = await get_jira_credentials(user)
    assert creds["has_token"] is True

@pytest.mark.asyncio
async def test_save_jira_credentials():
    mock_db = MagicMock()
    user = MagicMock(id_usuario=1)
    payload = JiraCredentialsPayload(
        jira_domain="test.atlassian.net",
        jira_email="test@mchav.com",
        jira_api_token="secret_token"
    )

    verified = {
        "jira_domain": "test.atlassian.net",
        "jira_email": "test@mchav.com",
        "jira_api_token": "secret_token"
    }

    with patch("app.services.auth_service.verify_jira_api_credentials", new_callable=AsyncMock, return_value=verified), \
         patch("app.repositories.user_repo.update") as mock_user_update:
        res = await save_jira_credentials(payload, mock_db, user)
        assert res["status"] == "success"
        assert mock_user_update.called

@pytest.mark.asyncio
async def test_login_post_and_local():
    mock_db = MagicMock()
    response = Response()
    
    # 1. New user login_post
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with patch("app.repositories.user_repo.create", return_value=MagicMock(id_usuario=1, email="new@mchav.com", nombre="new", id_rol=1, activo=True, rol=MagicMock(nombre_rol="Admin"), jira_account_id=None, cloud_id=None, jira_domain=None, jira_email=None, api_token_vinculado=False)):
        res1 = await login_post(MockLoginPayload(email="new@mchav.com", role="ADMIN"), response, mock_db)
        assert res1["id_usuario"] == 1

    # 2. Local login
    res2 = await post_login_local(LoginPayload(email="vhoyos@mchav.com", role="ADMIN"), response, mock_db)
    assert "token" in res2

def test_login_and_logout():
    with patch("app.services.auth_service.generate_oauth_state", return_value="state123"), \
         patch("app.services.auth_service.build_jira_oauth_url", return_value="http://atlassian/auth"):
        red = login()
        assert red.status_code == 307 or red.status_code == 302

    res_logout = logout()
    assert res_logout.status_code == 200

@pytest.mark.asyncio
async def test_callback_oauth():
    mock_db = MagicMock()
    response = Response()

    # Invalid state
    with patch("app.services.auth_service.validate_oauth_state", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await callback("code1", "bad_state", response, mock_db)
        assert exc.value.status_code == 400

    # Valid state
    u_profile = {"jira_account_id": "J1", "email": "o@mchav.com", "nombre": "O User"}
    with patch("app.services.auth_service.validate_oauth_state", return_value=True), \
         patch("app.services.auth_service.exchange_code_for_user_profile", new_callable=AsyncMock, return_value=u_profile), \
         patch("app.repositories.user_repo.get_by_jira_account_id", return_value=None), \
         patch("app.repositories.user_repo.create", return_value=MagicMock(id_usuario=99)):
        res_cb = await callback("code1", "good_state", response, mock_db)
        assert res_cb.status_code == 302
