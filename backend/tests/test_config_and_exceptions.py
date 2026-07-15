import pytest

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError


def test_not_found_error_status_code():
    error = NotFoundError("Recurso no encontrado")
    assert error.status_code == 404
    assert error.message == "Recurso no encontrado"


def test_app_error_default_status_code():
    error = AppError("Validación fallida")
    assert error.status_code == 400


def test_production_rejects_insecure_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            ENV="prod",
            JWT_SECRET_KEY="dev-jwt-secret-change-me",
            SESSION_SECRET_KEY="real-session-secret-value",
            DB_PASSWORD="secure-password",
        )


def test_dev_allows_default_secrets():
    settings = Settings(ENV="dev")
    assert settings.JWT_SECRET_KEY == "dev-jwt-secret-change-me"
