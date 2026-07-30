"""Endpoints de proyecto Jira en vivo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security

from app.api.v1.controllers import jira_controller
from app.api.v1.deps import get_current_user, get_jira_query_service
from app.dtos.common import DataResponseDTO
from app.models import User
from app.services.jira_query_service import JiraQueryService

router = APIRouter(prefix="/jira", tags=["Jira"])


@router.get(
    "/proyecto/{project_key}",
    response_model=DataResponseDTO[dict],
    summary="Obtener proyecto en vivo desde Jira",
)
def get_jira_project(
    project_key: str,
    current_user: Annotated[User, Security(get_current_user, scopes=["jira:read"])],
    service: JiraQueryService = Depends(get_jira_query_service),
):
    _ = current_user
    return jira_controller.get_jira_project(project_key, service)
