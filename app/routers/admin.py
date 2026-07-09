from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_role
from app.schemas.common import DataResponse, StatusResponse
from app.services.jira import JiraService

router = APIRouter(prefix="/api/admin", tags=["Admin"])
jira_service = JiraService()


@router.get("/ping", response_model=StatusResponse, dependencies=[Depends(require_role("Administrador"))])
async def admin_ping():
    return StatusResponse(detail="Acceso de administrador confirmado")


@router.get(
    "/jira/test-connection",
    response_model=DataResponse[dict],
    dependencies=[Depends(require_role("Administrador"))],
)
async def probar_conexion_jira():
    resultado = jira_service.probar_conexion()
    if not resultado["ok"]:
        raise HTTPException(status_code=400, detail=resultado["detail"])
    return DataResponse(
        data={"detail": resultado["detail"], "cuenta": resultado.get("cuenta")}
    )
