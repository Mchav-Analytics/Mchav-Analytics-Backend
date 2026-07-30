"""Endpoints de búsquedas JQL y métricas en vivo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security

from app.api.v1.controllers import jira_controller
from app.api.v1.deps import get_current_user, get_jira_query_service
from app.dtos.common import DataResponseDTO
from app.dtos.jira import JqlSearchRequestDTO, JqlSearchResponseDTO
from app.models import User
from app.services.jira_query_service import JiraQueryService

router = APIRouter(prefix="/jira", tags=["Jira"])


@router.post(
    "/search",
    response_model=DataResponseDTO[JqlSearchResponseDTO],
    summary="Ejecutar búsqueda JQL",
)
def search_jql(
    body: JqlSearchRequestDTO,
    current_user: Annotated[User, Security(get_current_user, scopes=["jira:read"])],
    service: JiraQueryService = Depends(get_jira_query_service),
):
    _ = current_user
    return jira_controller.search_jql(body, service)


@router.get(
    "/metrics/open-issues/{project_key}",
    response_model=DataResponseDTO[dict],
    summary="Conteo de issues abiertos",
)
def open_issues_metrics(
    project_key: str,
    current_user: Annotated[User, Security(get_current_user, scopes=["jira:read"])],
    service: JiraQueryService = Depends(get_jira_query_service),
):
    _ = current_user
    return jira_controller.open_issues_metrics(project_key, service)


@router.get(
    "/metrics/resolved/{project_key}",
    response_model=DataResponseDTO[dict],
    summary="Conteo de issues resueltos en N días",
)
def resolved_issues_metrics(
    project_key: str,
    current_user: Annotated[User, Security(get_current_user, scopes=["jira:read"])],
    days: int = 30,
    service: JiraQueryService = Depends(get_jira_query_service),
):
    _ = current_user
    return jira_controller.resolved_issues_metrics(project_key, service, days=days)
