"""Cálculo y persistencia de KPIs (solo reglas de negocio + repositorio)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models import KpiHistory
from app.repositories import KpiRepository

DONE_STATUSES = frozenset(
    {"done", "closed", "resolved", "completado", "hecho"}
)

DEFAULT_KPI_TYPES = (
    ("velocity", "Story points completados en el sprint", "pts"),
    ("completion_rate", "Porcentaje de issues resueltos", "%"),
    ("open_issues", "Issues abiertos en el sprint", "issues"),
)


class KpiService:
    def __init__(self, db: Session):
        self.uow = UnitOfWork(db)
        self.kpis = KpiRepository(db)

    def ensure_default_kpi_types(self) -> None:
        self.kpis.ensure_types(DEFAULT_KPI_TYPES)

    def _get_kpi_type_id(self, name: str) -> int:
        kpi_type = self.kpis.get_type_by_name(name)
        if not kpi_type:
            raise ValueError(f"Tipo de KPI no configurado: {name}")
        return kpi_type.id_kpi_type

    def calculate_velocity(self, sprint_id: int) -> float:
        issues = self.kpis.list_issues_by_sprint(sprint_id)
        done_points = [
            issue.story_points or 0
            for issue in issues
            if issue.status.lower() in DONE_STATUSES
        ]
        return float(sum(done_points))

    def calculate_completion_rate(self, sprint_id: int) -> float:
        issues = self.kpis.list_issues_by_sprint(sprint_id)
        if not issues:
            return 0.0
        done_count = sum(
            1 for issue in issues if issue.status.lower() in DONE_STATUSES
        )
        return round((done_count / len(issues)) * 100, 2)

    def calculate_open_issues(self, sprint_id: int) -> float:
        issues = self.kpis.list_issues_by_sprint(sprint_id)
        open_count = sum(
            1 for issue in issues if issue.status.lower() not in DONE_STATUSES
        )
        return float(open_count)

    def persist_kpi(self, sprint_id: int, kpi_name: str, value: float) -> KpiHistory:
        return self.kpis.add_history(
            sprint_id, self._get_kpi_type_id(kpi_name), value
        )

    def compute_and_store_sprint_kpis(self, sprint_id: int) -> list[KpiHistory]:
        self.ensure_default_kpi_types()
        calculations = {
            "velocity": self.calculate_velocity(sprint_id),
            "completion_rate": self.calculate_completion_rate(sprint_id),
            "open_issues": self.calculate_open_issues(sprint_id),
        }
        return [
            self.persist_kpi(sprint_id, name, value)
            for name, value in calculations.items()
        ]

    def _get_sprint(self, sprint_id: int):
        sprint = self.kpis.get_sprint(sprint_id)
        if not sprint:
            raise NotFoundError("Sprint no encontrado")
        return sprint

    def build_sprint_kpis_payload(self, sprint_id: int) -> dict:
        sprint = self._get_sprint(sprint_id)
        return {
            "id_sprint": sprint.id_sprint,
            "sprint_name": sprint.name,
            "kpis": self.get_latest_sprint_kpis(sprint_id),
        }

    def compute_and_return_sprint_kpis(self, sprint_id: int) -> dict:
        self.compute_and_store_sprint_kpis(sprint_id)
        return self.build_sprint_kpis_payload(sprint_id)

    def get_latest_sprint_kpis(self, sprint_id: int) -> list[dict]:
        return self.kpis.latest_by_sprint(sprint_id)
