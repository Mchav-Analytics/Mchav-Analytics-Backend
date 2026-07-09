"""Cálculo y persistencia de KPIs sobre datos locales."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.features.jira.models import Issue, KpiHistory, KpiType, Sprint


DEFAULT_KPI_TYPES = (
    ("velocity", "Story points completados en el sprint", "pts"),
    ("completion_rate", "Porcentaje de issues resueltos", "%"),
    ("open_issues", "Issues abiertos en el sprint", "issues"),
)


class KpiService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_default_kpi_types(self) -> None:
        for name, description, unit in DEFAULT_KPI_TYPES:
            exists = self.db.query(KpiType).filter(KpiType.name == name).first()
            if exists:
                continue
            self.db.add(KpiType(name=name, description=description, unit=unit))
        self.db.commit()

    def _get_kpi_type(self, name: str) -> KpiType:
        kpi_type = self.db.query(KpiType).filter(KpiType.name == name).first()
        if not kpi_type:
            raise ValueError(f"Tipo de KPI no configurado: {name}")
        return kpi_type

    def _sprint_issues(self, sprint_id: int) -> list[Issue]:
        return self.db.query(Issue).filter(Issue.id_sprint == sprint_id).all()

    def calculate_velocity(self, sprint_id: int) -> float:
        issues = self._sprint_issues(sprint_id)
        done_points = [
            issue.story_points or 0
            for issue in issues
            if issue.status.lower() in {"done", "closed", "resolved", "completado", "hecho"}
        ]
        return float(sum(done_points))

    def calculate_completion_rate(self, sprint_id: int) -> float:
        issues = self._sprint_issues(sprint_id)
        if not issues:
            return 0.0
        done_count = sum(
            1
            for issue in issues
            if issue.status.lower() in {"done", "closed", "resolved", "completado", "hecho"}
        )
        return round((done_count / len(issues)) * 100, 2)

    def calculate_open_issues(self, sprint_id: int) -> float:
        issues = self._sprint_issues(sprint_id)
        open_count = sum(
            1
            for issue in issues
            if issue.status.lower() not in {"done", "closed", "resolved", "completado", "hecho"}
        )
        return float(open_count)

    def persist_kpi(self, sprint_id: int, kpi_name: str, value: float) -> KpiHistory:
        kpi_type = self._get_kpi_type(kpi_name)
        record = KpiHistory(
            id_sprint=sprint_id,
            id_kpi_type=kpi_type.id_kpi_type,
            metric_value=value,
            calc_date=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def compute_and_store_sprint_kpis(self, sprint_id: int) -> list[KpiHistory]:
        self.ensure_default_kpi_types()
        calculations = {
            "velocity": self.calculate_velocity(sprint_id),
            "completion_rate": self.calculate_completion_rate(sprint_id),
            "open_issues": self.calculate_open_issues(sprint_id),
        }
        return [self.persist_kpi(sprint_id, name, value) for name, value in calculations.items()]

    def get_latest_sprint_kpis(self, sprint_id: int) -> list[dict]:
        rows = (
            self.db.query(KpiHistory, KpiType)
            .join(KpiType, KpiHistory.id_kpi_type == KpiType.id_kpi_type)
            .filter(KpiHistory.id_sprint == sprint_id)
            .order_by(KpiHistory.calc_date.desc())
            .all()
        )

        latest_by_type: dict[str, dict] = {}
        for history, kpi_type in rows:
            if kpi_type.name in latest_by_type:
                continue
            latest_by_type[kpi_type.name] = {
                "kpi_type": kpi_type.name,
                "unit": kpi_type.unit,
                "metric_value": history.metric_value,
                "calc_date": history.calc_date,
            }
        return list(latest_by_type.values())
