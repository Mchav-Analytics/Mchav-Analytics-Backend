from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.features.jira.models import Sprint
from app.schemas.common import DataResponse
from app.schemas.kpi import KpiValueOut, SprintKpisOut
from app.services.kpi import KpiService

router = APIRouter(prefix="/api/kpis", tags=["KPIs"])


@router.get("/sprints/{sprint_id}", response_model=DataResponse[SprintKpisOut])
async def obtener_kpis_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id_sprint == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint no encontrado")

    service = KpiService(db)
    kpis = service.get_latest_sprint_kpis(sprint_id)
    payload = SprintKpisOut(
        id_sprint=sprint.id_sprint,
        sprint_name=sprint.name,
        kpis=[KpiValueOut(**item) for item in kpis],
    )
    return DataResponse(data=payload)


@router.post("/sprints/{sprint_id}/compute", response_model=DataResponse[SprintKpisOut])
async def calcular_kpis_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id_sprint == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint no encontrado")

    service = KpiService(db)
    service.compute_and_store_sprint_kpis(sprint_id)
    kpis = service.get_latest_sprint_kpis(sprint_id)
    payload = SprintKpisOut(
        id_sprint=sprint.id_sprint,
        sprint_name=sprint.name,
        kpis=[KpiValueOut(**item) for item in kpis],
    )
    return DataResponse(data=payload)
