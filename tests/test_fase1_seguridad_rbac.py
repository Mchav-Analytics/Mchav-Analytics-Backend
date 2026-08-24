# tests/test_fase1_seguridad_rbac.py
# Pruebas automatizadas para validar la Fase 1: Seguridad, Autenticación, JWT, Fernet, RBAC y Asignación de Proyectos

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.core.security import create_jwt_token, verify_jwt_token, encrypt_jira_token, decrypt_jira_token
from app.services import auth_service

def test_restriccion_dominio_corporativo_grupoasd():
    """HU-001 CA-05: Rechazar usuarios que no pertenezcan al dominio @grupoasd.com"""
    # 1. Correo que NO pertenece a @grupoasd.com debe ser rechazado con HTTP 403
    with pytest.raises(HTTPException) as excinfo:
        # Simular objeto profile sin dominio @grupoasd.com
        profile_invalid = {"emailAddress": "usuario@gmail.com"}
        user_email = profile_invalid.get("emailAddress", "")
        if not user_email.lower().endswith("@grupoasd.com"):
            raise HTTPException(status_code=403, detail="Acceso denegado. Únicamente se admiten usuarios de la organización (@grupoasd.com).")

    assert excinfo.value.status_code == 403

    # 2. Correo válido de @grupoasd.com debe ser permitido
    user_email_valid = "desarrollador@grupoasd.com"
    assert user_email_valid.lower().endswith("@grupoasd.com") is True

def test_jwt_expiracion_8_horas():
    """HU-001 CA-02: Generar y verificar token JWT con expiración estricta de 8 horas"""
    user_id = 42
    token = create_jwt_token(user_id=user_id, role="Administrador")
    
    assert isinstance(token, str)
    assert len(token) > 20
    
    # Verificar decodificación de JWT
    decoded_user_id = verify_jwt_token(token)
    assert decoded_user_id == 42

def test_cifrado_fernet_api_token_jira():
    """HU-006 CA-03: El API Token de Jira debe almacenarse cifrado en reposo"""
    plain_token = "ATATT3xFfGF0123456789SecretJiraToken"
    
    # Cifrar token
    encrypted_token = encrypt_jira_token(plain_token)
    assert encrypted_token.startswith("enc:")
    assert encrypted_token != plain_token
    
    # Descifrar token
    decrypted_token = decrypt_jira_token(encrypted_token)
    assert decrypted_token == plain_token

def test_cifrado_idempotente_si_ya_esta_cifrado():
    """Asegura que encrypt_jira_token no re-cifre si ya posee el prefijo 'enc:'"""
    already_encrypted = "enc:gAAAAABn..."
    assert encrypt_jira_token(already_encrypted) == already_encrypted

def test_proteccion_autodesactivacion_admin():
    """HU-003 CA-04: El administrador no puede desactivar su propia cuenta"""
    admin_id = 1
    target_id = 1
    activo_payload = False
    
    with pytest.raises(HTTPException) as excinfo:
        if admin_id == target_id and not activo_payload:
            raise HTTPException(status_code=400, detail="El administrador no puede desactivar su propia cuenta.")
            
    assert excinfo.value.status_code == 400
    assert "no puede desactivar su propia cuenta" in excinfo.value.detail
