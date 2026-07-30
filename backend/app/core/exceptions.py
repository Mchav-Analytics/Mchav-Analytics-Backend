"""Excepciones de dominio para respuestas HTTP consistentes.

Los services lanzan estas excepciones; FastAPI las traduce a JSON en main.py.
Así la capa de aplicación no depende de HTTPException.
"""


class AppError(Exception):
    """Error de negocio o integración controlado."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "No autorizado"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Acceso denegado"):
        super().__init__(message, status_code=403)


class ExternalAuthError(AppError):
    """Fallo al hablar con el proveedor OAuth externo."""

    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class JiraConnectionError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class JiraNotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class JiraQueryError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
