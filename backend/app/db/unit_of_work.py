"""Unit of Work: una sola unidad de trabajo transaccional por caso de uso."""

from __future__ import annotations

from sqlalchemy.orm import Session


class UnitOfWork:
    """Envuelve la Session para commit/rollback explícitos desde application."""

    def __init__(self, session: Session):
        self.session = session

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def refresh(self, instance: object) -> None:
        self.session.refresh(instance)

    def add(self, instance: object) -> None:
        self.session.add(instance)
