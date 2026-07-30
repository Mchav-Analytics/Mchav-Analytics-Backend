"""Pruebas unitarias de JWT + OAuth2 scopes."""

from fastapi.security import SecurityScopes

from app.core.scopes import ROLE_SCOPES, SCOPES, scopes_for_role
from app.core.security import (
    create_access_token,
    decode_access_token,
    scopes_from_payload,
)
from app.dtos.auth import TokenDataDTO
import pytest


def test_create_and_decode_access_token_includes_scopes():
    token = create_access_token(
        subject="42",
        scopes=["me", "projects:read"],
        extra_claims={"email": "user@grupoasd.com", "role": "Consultor"},
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "user@grupoasd.com"
    assert payload["role"] == "Consultor"
    assert payload["scope"] == "me projects:read"
    assert scopes_from_payload(payload) == ["me", "projects:read"]
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(ValueError, match="Token inválido"):
        decode_access_token("not-a-valid-jwt")


def test_scopes_for_admin_includes_write_scopes():
    scopes = scopes_for_role("Administrador")
    assert "admin" in scopes
    assert "projects:sync" in scopes
    assert "kpis:compute" in scopes
    assert set(scopes) == set(SCOPES.keys())


def test_scopes_for_consultor_are_read_only():
    scopes = scopes_for_role("Consultor")
    assert "projects:read" in scopes
    assert "admin" not in scopes
    assert "projects:sync" not in scopes
    assert scopes == ROLE_SCOPES["Consultor"]


def test_token_data_model():
    data = TokenDataDTO(sub="1", scopes=["me"], email="a@b.com", role="Consultor")
    assert data.scopes == ["me"]


def test_security_scopes_string():
    scopes = SecurityScopes(scopes=["projects:read", "kpis:read"])
    assert scopes.scope_str == "projects:read kpis:read"
