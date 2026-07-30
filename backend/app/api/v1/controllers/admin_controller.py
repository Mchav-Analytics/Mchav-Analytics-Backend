"""Controlador administrativo."""

from __future__ import annotations

from app.dtos.common import DataResponseDTO, StatusResponseDTO
from app.services.jira_query_service import JiraQueryService


def admin_ping() -> StatusResponseDTO:
    return StatusResponseDTO(detail="Acceso de administrador confirmado")


def test_jira_connection(service: JiraQueryService) -> DataResponseDTO[dict]:
    return DataResponseDTO(data=service.test_connection())
