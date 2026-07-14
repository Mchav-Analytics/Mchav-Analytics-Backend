from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KpiValueOut(BaseModel):
    kpi_type: str
    unit: str
    metric_value: float
    calc_date: datetime | None = None


class SprintKpisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_sprint: int
    sprint_name: str
    kpis: list[KpiValueOut]
