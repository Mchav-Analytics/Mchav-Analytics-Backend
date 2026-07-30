"""Base declarativa SQLAlchemy 2.x (recomendado por FastAPI + SQLAlchemy)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""

    pass
