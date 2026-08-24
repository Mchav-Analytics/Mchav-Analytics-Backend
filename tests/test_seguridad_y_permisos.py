import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import SecurityScopes
from app.core.security import sign_session_id, verify_session_id, get_current_user
from app.models.auth import User, Role
from app.api.v1 import deps

def test_formato_firma_sesion_hmac():
    """Prueba que la función sign_session_id genere un Token JWT de 8 horas verificado por verify_session_id."""
    user_id = 5
    signed = sign_session_id(user_id)
    verified_id = verify_session_id(signed)
    assert verified_id == user_id

def test_verificar_firma_sesion_valida():
    """Prueba que una firma auténtica se decodifique y valide correctamente"""
    user_id = 5
    signed = sign_session_id(user_id)
    verified_id = verify_session_id(signed)
    assert verified_id == 5

def test_rechazar_firma_sesion_alterada():
    """Prueba que el sistema rechace el acceso si se altera la firma del JWT."""
    user_id = 5
    signed = sign_session_id(user_id)
    # Alterar un caracter en la firma del JWT
    tampered_signed = signed[:20] + "X" + signed[21:]
    verified_id = verify_session_id(tampered_signed)
    assert verified_id is None

def test_rechazar_cambio_id_usuario_sesion():
    """Prueba que el sistema rechace si alguien intenta cambiar su ID de usuario."""
    user_id = 5
    signed = sign_session_id(user_id)
    tampered_signed = signed[:35] + "99" + signed[37:]
    verified_id = verify_session_id(tampered_signed)
    assert verified_id is None

def test_rechazar_sesion_vacia_o_nula():
    """Prueba que el sistema rechace un token vacío o nulo."""
    assert verify_session_id("") is None
    assert verify_session_id(None) is None

def test_rechazar_sesion_malformada_sin_punto():
    """Prueba que el sistema no falle si envían texto sin punto separador."""
    assert verify_session_id("un_texto_aleatorio_sin_sentido_alguno") is None

def test_rechazar_sesion_id_no_numerico():
    """Prueba que el sistema rechace si el ID provisto no es entero."""
    signed_bad_id = "abc.a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
    assert verify_session_id(signed_bad_id) is None

def test_obtener_usuario_actual_desde_token_bearer():
    """Verifica la extracción exitosa de usuario desde la cabecera Authorization (Bearer)."""
    mock_db = MagicMock()
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=5, email="dev@mchav.com", activo=True, rol=mock_role)
    mock_db.query().filter().first.return_value = mock_user
    
    with patch('app.core.security.verify_session_id', return_value=5):
        scopes = SecurityScopes(scopes=["jira:read"])
        req = MagicMock(cookies={})
        
        user = get_current_user(
            security_scopes=scopes,
            request=req,
            db=mock_db,
            token="5.valid_signed_token"
        )
        assert user.id_usuario == 5

def test_obtener_usuario_actual_desde_cookie_sesion():
    """Verifica la extracción exitosa de usuario desde la cookie de sesión firmada."""
    mock_db = MagicMock()
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read")
    mock_user = User(id_usuario=8, email="cookie@mchav.com", activo=True, rol=mock_role)
    mock_db.query().filter().first.return_value = mock_user
    
    with patch('app.core.security.verify_session_id', return_value=8):
        scopes = SecurityScopes(scopes=[])
        req = MagicMock(cookies={"session_id": "8.valid_signed_cookie"})
        
        user = get_current_user(
            security_scopes=scopes,
            request=req,
            db=mock_db,
            token=None
        )
        assert user.id_usuario == 8

def test_rechazar_usuario_sin_autenticacion():
    """Verifica que se lance HTTPException 401 si no hay ni token ni cookie válidos."""
    mock_db = MagicMock()
    scopes = SecurityScopes(scopes=["admin"])
    req = MagicMock(cookies={})
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            security_scopes=scopes,
            request=req,
            db=mock_db,
            token=None
        )
    assert exc_info.value.status_code == 401

def test_error_id_usuario_sesion_invalida():
    """Verifica error 401 cuando la cookie posee una firma inválida."""
    req = MagicMock(cookies={"session_id": "invalid.signature"})
    with patch('app.api.v1.deps.verify_session_id', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            deps.get_current_user_id(request=req, credentials=None)
        assert exc_info.value.status_code == 401
        assert "Sesión inválida" in exc_info.value.detail

def test_error_usuario_no_existente_bd():
    """Verifica error 401 cuando el ID del usuario no existe en la base de datos."""
    mock_db = MagicMock()
    with patch('app.repositories.user_repo.get', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            deps.check_user_exists(mock_db, 999)
        assert exc_info.value.status_code == 401
        assert "Usuario no encontrado" in exc_info.value.detail

def test_verificar_existencia_usuario_exitoso():
    """Verifica que retorne el usuario si existe."""
    mock_db = MagicMock()
    mock_user = MagicMock(id_usuario=1)
    with patch('app.repositories.user_repo.get', return_value=mock_user):
        u = deps.check_user_exists(mock_db, 1)
        assert u.id_usuario == 1
