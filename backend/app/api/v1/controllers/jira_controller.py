"""Controlador de consultas Jira en vivo."""

from __future__ import annotations

from app.dtos.common import DataResponseDTO
from app.dtos.jira import JqlSearchRequestDTO, JqlSearchResponseDTO
from app.services.jira_query_service import JiraQueryService


def get_jira_project(
    project_key: str, service: JiraQueryService
) -> DataResponseDTO[dict]:
    return DataResponseDTO(data=service.get_project(project_key))


def search_jql(
    body: JqlSearchRequestDTO, service: JiraQueryService
) -> DataResponseDTO[JqlSearchResponseDTO]:
    payload = service.search_issues(
        jql=body.jql,
        start_at=body.start_at,
        max_results=body.max_results,
    )
    return DataResponseDTO(data=JqlSearchResponseDTO(**payload))


def open_issues_metrics(
    project_key: str, service: JiraQueryService
) -> DataResponseDTO[dict]:
    return DataResponseDTO(data=service.open_issues_metrics(project_key))


def resolved_issues_metrics(
    project_key: str, service: JiraQueryService, days: int = 30
) -> DataResponseDTO[dict]:
    return DataResponseDTO(
        data=service.resolved_issues_metrics(project_key, days=days)
    )
