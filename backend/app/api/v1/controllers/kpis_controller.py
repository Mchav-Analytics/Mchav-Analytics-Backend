"""Controlador de KPIs ágiles."""

from __future__ import annotations

from app.dtos.common import DataResponseDTO
from app.dtos.kpi import KpiValueDTO, SprintKpisDTO
from app.services.kpi_service import KpiService


def _to_sprint_kpis_dto(payload: dict) -> SprintKpisDTO:
    return SprintKpisDTO(
        id_sprint=payload["id_sprint"],
        sprint_name=payload["sprint_name"],
        kpis=[KpiValueDTO(**item) for item in payload["kpis"]],
    )


def get_sprint_kpis(
    sprint_id: int, service: KpiService
) -> DataResponseDTO[SprintKpisDTO]:
    payload = service.build_sprint_kpis_payload(sprint_id)
    return DataResponseDTO(data=_to_sprint_kpis_dto(payload))


def compute_sprint_kpis(
    sprint_id: int, service: KpiService
) -> DataResponseDTO[SprintKpisDTO]:
    payload = service.compute_and_return_sprint_kpis(sprint_id)
    return DataResponseDTO(data=_to_sprint_kpis_dto(payload))
