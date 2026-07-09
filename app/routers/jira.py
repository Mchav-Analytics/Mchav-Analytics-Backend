from fastapi import APIRouter, Depends, HTTPException

from app.core.exceptions import AppError
from app.dependencies import get_current_user, require_role
from app.schemas.common import DataResponse, StatusResponse
from app.schemas.jira import JqlSearchRequest, JqlSearchResponse
from app.services.jira import JiraService
from app.services.jira_queries import open_issues_jql, resolved_in_period_jql

router = APIRouter(prefix="/api/jira", tags=["Jira"])
jira_service = JiraService()


@router.get("/proyecto/{project_key}")
async def obtener_proyecto_jira(project_key: str, _current_user=Depends(get_current_user)):
    try:
        datos = jira_service.verificar_proyecto(project_key)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if not datos:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return DataResponse(data=datos)


@router.post("/search", response_model=DataResponse[JqlSearchResponse])
async def buscar_con_jql(body: JqlSearchRequest, _current_user=Depends(get_current_user)):
    try:
        payload = jira_service.buscar_issues(
            jql=body.jql,
            start_at=body.start_at,
            max_results=body.max_results,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    response = JqlSearchResponse(
        total=payload.get("total", 0),
        start_at=payload.get("startAt", body.start_at),
        max_results=payload.get("maxResults", body.max_results),
        issues=payload.get("issues", []),
    )
    return DataResponse(data=response)


@router.get("/metrics/open-issues/{project_key}")
async def metricas_issues_abiertos(project_key: str, _current_user=Depends(get_current_user)):
    jql = open_issues_jql(project_key)
    try:
        payload = jira_service.buscar_issues(jql=jql, max_results=1)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DataResponse(data={"project_key": project_key, "open_issues": payload.get("total", 0), "jql": jql})


@router.get("/metrics/resolved/{project_key}")
async def metricas_resueltos(project_key: str, days: int = 30, _current_user=Depends(get_current_user)):
    jql = resolved_in_period_jql(project_key, days=days)
    try:
        payload = jira_service.buscar_issues(jql=jql, max_results=1)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data={
            "project_key": project_key,
            "resolved_last_days": payload.get("total", 0),
            "days": days,
            "jql": jql,
        }
    )
