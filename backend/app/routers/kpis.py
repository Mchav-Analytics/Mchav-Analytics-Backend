from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_kpi_service, require_role
from app.schemas.common import DataResponse
from app.schemas.kpi import KpiValueOut, SprintKpisOut
from app.services.kpi import KpiService

router = APIRouter(prefix="/api/kpis", tags=["KPIs"])


def _to_sprint_kpis_out(payload: dict) -> SprintKpisOut:
    return SprintKpisOut(
        id_sprint=payload["id_sprint"],
        sprint_name=payload["sprint_name"],
        kpis=[KpiValueOut(**item) for item in payload["kpis"]],
    )


@router.get("/sprints/{sprint_id}", response_model=DataResponse[SprintKpisOut])
def obtener_kpis_sprint(
    sprint_id: int,
    service: KpiService = Depends(get_kpi_service),
    _current_user=Depends(get_current_user),
):
    payload = service.build_sprint_kpis_payload(sprint_id)
    return DataResponse(data=_to_sprint_kpis_out(payload))


@router.post(
    "/sprints/{sprint_id}/compute",
    response_model=DataResponse[SprintKpisOut],
)
def calcular_kpis_sprint(
    sprint_id: int,
    service: KpiService = Depends(get_kpi_service),
    _admin=Depends(require_role("Administrador")),
):
    payload = service.compute_and_return_sprint_kpis(sprint_id)
    return DataResponse(data=_to_sprint_kpis_out(payload))
