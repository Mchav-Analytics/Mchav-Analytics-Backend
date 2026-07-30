"""Puerto de salida hacia Jira Cloud (API Token)."""

from __future__ import annotations

from typing import Protocol


class JiraGateway(Protocol):
    """Contrato que debe cumplir cualquier cliente Jira inyectado en services."""

    def test_connection(self) -> dict: ...

    def get_project(self, project_key: str) -> dict | None: ...

    def get_boards(self, project_key: str) -> list[dict]: ...

    def get_sprints(self, board_id: str, max_results: int = 50) -> list[dict]: ...

    def search_issues(
        self, jql: str, start_at: int = 0, max_results: int = 50
    ) -> dict: ...
