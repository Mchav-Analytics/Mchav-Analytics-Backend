"""Pruebas unitarias de login local + JwtService."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models import Role, User
from app.services.jwt_service import ACCESS_TOKEN_EXPIRE_SECONDS, JwtService
from app.services.local_auth_service import LocalAuthError, LocalAuthService


def test_hash_and_verify_password():
    hashed = hash_password("Admin123!")
    assert hashed != "Admin123!"
    assert verify_password("Admin123!", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_service_build_auth_response():
    role = SimpleNamespace(name="Administrador")
    user = SimpleNamespace(
        id_user=7,
        email="admin@test.com",
        full_name="Admin",
        status="active",
        role=role,
    )
    payload = JwtService.build_auth_response(user)
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == ACCESS_TOKEN_EXPIRE_SECONDS
    assert payload["user"]["email"] == "admin@test.com"
    assert "admin" in payload["scopes"]
    decoded = JwtService.decode(payload["access_token"])
    assert decoded["sub"] == "7"
    assert decoded["role"] == "Administrador"


def test_authenticate_user_with_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    role = Role(name="Administrador", description="admin")
    db.add(role)
    db.commit()
    db.refresh(role)

    user = User(
        email="local@test.com",
        full_name="Local User",
        hashed_password=hash_password("Secret1!"),
        status="active",
        id_role=role.id_role,
    )
    db.add(user)
    db.commit()

    auth = LocalAuthService(db)
    found = auth.authenticate("local@test.com", "Secret1!")
    assert found.email == "local@test.com"

    with pytest.raises(LocalAuthError):
        auth.authenticate("local@test.com", "bad")

    with pytest.raises(LocalAuthError):
        auth.authenticate("missing@test.com", "Secret1!")

    db.close()
