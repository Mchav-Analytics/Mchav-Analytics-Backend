"""Casos de uso de consultas Jira en vivo (API token)."""

from __future__ import annotations

from app.core.exceptions import AppError, JiraNotFoundError
from app.datasources.jira_client import JiraClient
from app.ports.jira_gateway import JiraGateway
from app.services.jql_builder import JqlBuilder


class JiraQueryService:
    """Orquesta el gateway Jira; los controllers no hablan con HTTP."""

    def __init__(self, jira: JiraGateway | None = None):
        self.jira = jira or JiraClient()

    def test_connection(self) -> dict:
        result = self.jira.test_connection()
        if not result.get("ok"):
            raise AppError(result.get("detail", "Conexión Jira fallida"), status_code=400)
        return {
            "detail": result["detail"],
            "cuenta": result.get("cuenta"),
        }

    def get_project(self, project_key: str) -> dict:
        data = self.jira.get_project(project_key)
        if not data:
            raise JiraNotFoundError("Proyecto no encontrado")
        return data

    def search_issues(
        self, jql: str, start_at: int = 0, max_results: int = 50
    ) -> dict:
        payload = self.jira.search_issues(
            jql=jql, start_at=start_at, max_results=max_results
        )
        return {
            "total": payload.get("total", 0),
            "start_at": payload.get("startAt", start_at),
            "max_results": payload.get("maxResults", max_results),
            "issues": payload.get("issues", []),
        }

    def open_issues_metrics(self, project_key: str) -> dict:
        jql = JqlBuilder.open_issues(project_key)
        payload = self.jira.search_issues(jql=jql, max_results=1)
        return {
            "project_key": project_key,
            "open_issues": payload.get("total", 0),
            "jql": jql,
        }

    def resolved_issues_metrics(self, project_key: str, days: int = 30) -> dict:
        jql = JqlBuilder.resolved_in_period(project_key, days=days)
        payload = self.jira.search_issues(jql=jql, max_results=1)
        return {
            "project_key": project_key,
            "resolved_last_days": payload.get("total", 0),
            "days": days,
            "jql": jql,
        }
