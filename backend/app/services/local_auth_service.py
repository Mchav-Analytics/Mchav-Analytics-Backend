"""Autenticación local (usuario y contraseña)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.unit_of_work import UnitOfWork
from app.models import User
from app.repositories import UserRepository
from app.services.jwt_service import JwtService


class LocalAuthError(Exception):
    """Credenciales o estado inválidos para login local."""


class LocalAuthService:
    def __init__(self, db: Session):
        self.uow = UnitOfWork(db)
        self.users = UserRepository(db)

    def authenticate(self, username: str, password: str) -> User:
        normalized = (username or "").strip().lower()
        if not normalized or not password:
            raise LocalAuthError("Usuario y contraseña son obligatorios")

        user = self.users.get_by_email(normalized)
        if not user or not user.hashed_password:
            raise LocalAuthError("Credenciales inválidas")

        if not verify_password(password, user.hashed_password):
            raise LocalAuthError("Credenciales inválidas")

        if user.status != "active":
            raise LocalAuthError("Usuario inactivo")

        return user

    def login(self, username: str, password: str) -> dict:
        user = self.authenticate(username, password)
        return JwtService.build_auth_response(user)

    def refresh(self, token: str) -> dict:
        try:
            payload = JwtService.decode(token)
        except ValueError as exc:
            raise LocalAuthError("Token inválido o expirado") from exc

        user_id = payload.get("sub")
        if user_id is None:
            raise LocalAuthError("Token inválido o expirado")

        user = self.users.get_by_id(int(user_id))
        if not user or user.status != "active":
            raise LocalAuthError("Usuario no disponible")

        return JwtService.build_auth_response(user)
