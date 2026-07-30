"""Endpoints administrativos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security

from app.api.v1.controllers import admin_controller
from app.api.v1.deps import get_current_user, get_jira_query_service
from app.dtos.common import DataResponseDTO, StatusResponseDTO
from app.models import User
from app.services.jira_query_service import JiraQueryService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/ping",
    response_model=StatusResponseDTO,
    summary="Verificar acceso de administrador (scope admin)",
)
def admin_ping(
    current_user: Annotated[User, Security(get_current_user, scopes=["admin"])],
):
    _ = current_user
    return admin_controller.admin_ping()


@router.get(
    "/jira/test-connection",
    response_model=DataResponseDTO[dict],
    summary="Probar conexión con Jira (scope admin)",
)
def test_jira_connection(
    current_user: Annotated[User, Security(get_current_user, scopes=["admin"])],
    service: JiraQueryService = Depends(get_jira_query_service),
):
    _ = current_user
    return admin_controller.test_jira_connection(service)
