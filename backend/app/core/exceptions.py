"""Excepciones de dominio para respuestas HTTP consistentes."""


class AppError(Exception):
    """Error de negocio o integración controlado."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class JiraConnectionError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class JiraNotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class JiraQueryError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)
