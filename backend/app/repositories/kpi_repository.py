"""Persistencia de KPIs y lectura de issues/sprints para cálculo."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Issue, KpiHistory, KpiType, Sprint


class KpiRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_type_by_name(self, name: str) -> KpiType | None:
        return self.db.query(KpiType).filter(KpiType.name == name).first()

    def ensure_types(self, defaults: tuple[tuple[str, str, str], ...]) -> None:
        for name, description, unit in defaults:
            if self.get_type_by_name(name):
                continue
            self.db.add(KpiType(name=name, description=description, unit=unit))
        self.db.commit()

    def list_issues_by_sprint(self, sprint_id: int) -> list[Issue]:
        return self.db.query(Issue).filter(Issue.id_sprint == sprint_id).all()

    def get_sprint(self, sprint_id: int) -> Sprint | None:
        return self.db.query(Sprint).filter(Sprint.id_sprint == sprint_id).first()

    def add_history(
        self, sprint_id: int, kpi_type_id: int, value: float
    ) -> KpiHistory:
        record = KpiHistory(
            id_sprint=sprint_id,
            id_kpi_type=kpi_type_id,
            metric_value=value,
            calc_date=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def latest_by_sprint(self, sprint_id: int) -> list[dict]:
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
