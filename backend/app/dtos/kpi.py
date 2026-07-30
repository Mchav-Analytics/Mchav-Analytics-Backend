"""DTOs de KPIs ágiles."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KpiValueDTO(BaseModel):
    kpi_type: str
    unit: str
    metric_value: float
    calc_date: datetime | None = None


class SprintKpisDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_sprint: int
    sprint_name: str
    kpis: list[KpiValueDTO]
