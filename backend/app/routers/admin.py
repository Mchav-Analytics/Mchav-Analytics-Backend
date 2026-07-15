from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_jira_service, require_role
from app.schemas.common import DataResponse, StatusResponse
from app.services.jira import JiraService

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/ping", response_model=StatusResponse)
def admin_ping(_admin=Depends(require_role("Administrador"))):
    return StatusResponse(detail="Acceso de administrador confirmado")


@router.get("/jira/test-connection", response_model=DataResponse[dict])
def probar_conexion_jira(
    jira: JiraService = Depends(get_jira_service),
    _admin=Depends(require_role("Administrador")),
):
    resultado = jira.probar_conexion()
    if not resultado["ok"]:
        raise HTTPException(status_code=400, detail=resultado["detail"])
    return DataResponse(
        data={"detail": resultado["detail"], "cuenta": resultado.get("cuenta")}
    )
