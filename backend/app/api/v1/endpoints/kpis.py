"""Endpoints de KPIs ágiles."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security

from app.api.v1.controllers import kpis_controller
from app.api.v1.deps import get_current_user, get_kpi_service
from app.dtos.common import DataResponseDTO
from app.dtos.kpi import SprintKpisDTO
from app.models import User
from app.services.kpi_service import KpiService

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get(
    "/sprints/{sprint_id}",
    response_model=DataResponseDTO[SprintKpisDTO],
    summary="Obtener KPIs de un sprint",
)
def get_sprint_kpis(
    sprint_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["kpis:read"])],
    service: KpiService = Depends(get_kpi_service),
):
    _ = current_user
    return kpis_controller.get_sprint_kpis(sprint_id, service)


@router.post(
    "/sprints/{sprint_id}/compute",
    response_model=DataResponseDTO[SprintKpisDTO],
    summary="Recalcular y persistir KPIs (scope kpis:compute)",
)
def compute_sprint_kpis(
    sprint_id: int,
    current_user: Annotated[User, Security(get_current_user, scopes=["kpis:compute"])],
    service: KpiService = Depends(get_kpi_service),
):
    _ = current_user
    return kpis_controller.compute_sprint_kpis(sprint_id, service)
