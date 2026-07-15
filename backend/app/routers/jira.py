from fastapi import APIRouter, Depends

from app.core.exceptions import JiraNotFoundError
from app.dependencies import get_current_user, get_jira_service
from app.schemas.common import DataResponse
from app.schemas.jira import JqlSearchRequest, JqlSearchResponse
from app.services.jira import JiraService
from app.services.jira_queries import open_issues_jql, resolved_in_period_jql

router = APIRouter(prefix="/api/jira", tags=["Jira"])


@router.get("/proyecto/{project_key}")
def obtener_proyecto_jira(
    project_key: str,
    jira: JiraService = Depends(get_jira_service),
    _current_user=Depends(get_current_user),
):
    datos = jira.verificar_proyecto(project_key)
    if not datos:
        raise JiraNotFoundError("Proyecto no encontrado")
    return DataResponse(data=datos)


@router.post("/search", response_model=DataResponse[JqlSearchResponse])
def buscar_con_jql(
    body: JqlSearchRequest,
    jira: JiraService = Depends(get_jira_service),
    _current_user=Depends(get_current_user),
):
    payload = jira.buscar_issues(
        jql=body.jql,
        start_at=body.start_at,
        max_results=body.max_results,
    )
    response = JqlSearchResponse(
        total=payload.get("total", 0),
        start_at=payload.get("startAt", body.start_at),
        max_results=payload.get("maxResults", body.max_results),
        issues=payload.get("issues", []),
    )
    return DataResponse(data=response)


@router.get("/metrics/open-issues/{project_key}")
def metricas_issues_abiertos(
    project_key: str,
    jira: JiraService = Depends(get_jira_service),
    _current_user=Depends(get_current_user),
):
    jql = open_issues_jql(project_key)
    payload = jira.buscar_issues(jql=jql, max_results=1)
    return DataResponse(
        data={"project_key": project_key, "open_issues": payload.get("total", 0), "jql": jql}
    )


@router.get("/metrics/resolved/{project_key}")
def metricas_resueltos(
    project_key: str,
    days: int = 30,
    jira: JiraService = Depends(get_jira_service),
    _current_user=Depends(get_current_user),
):
    jql = resolved_in_period_jql(project_key, days=days)
    payload = jira.buscar_issues(jql=jql, max_results=1)
    return DataResponse(
        data={
            "project_key": project_key,
            "resolved_last_days": payload.get("total", 0),
            "days": days,
            "jql": jql,
        }
    )
