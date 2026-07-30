"""Cliente HTTP hacia Jira Cloud REST API (API Token admin).

Implementa el puerto JiraGateway (duck typing / Protocol).
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.exceptions import JiraConnectionError, JiraQueryError


class JiraClient:
    def __init__(self, timeout: float = 15.0):
        self.base_url = settings.JIRA_BASE_URL.rstrip("/") if settings.JIRA_BASE_URL else ""
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}

    def _configured(self) -> bool:
        return bool(self.base_url and self.email and self.api_token)

    def _http(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            auth=(self.email, self.api_token),
            headers=self.headers,
            timeout=self.timeout,
        )

    def test_connection(self) -> dict:
        if not self._configured():
            return {"ok": False, "detail": "Faltan variables de entorno de Jira"}

        try:
            with self._http() as client:
                response = client.get("/rest/api/3/myself")
        except Exception as exc:
            return {"ok": False, "detail": f"Error de conexión: {exc}"}

        if response.status_code == 200:
            return {
                "ok": True,
                "detail": "Conexión exitosa",
                "cuenta": response.json().get("displayName"),
            }
        return {
            "ok": False,
            "detail": f"Código {response.status_code}: {response.text}",
        }

    def get_project(self, project_key: str) -> dict | None:
        if not self._configured():
            raise JiraConnectionError(
                "La conexión con Jira no está configurada (variables de entorno faltantes)."
            )

        try:
            with self._http() as client:
                response = client.get(f"/rest/api/3/project/{project_key}")
        except Exception as exc:
            raise JiraConnectionError(f"Error de conexión con la API de Jira: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        raise JiraConnectionError(
            f"Error al consultar Jira: {response.status_code} - {response.text}"
        )

    def get_boards(self, project_key: str) -> list[dict]:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        try:
            with self._http() as client:
                response = client.get(
                    "/rest/agile/1.0/board",
                    params={"projectKeyOrId": project_key},
                )
        except Exception as exc:
            raise JiraConnectionError(f"Error al consultar boards de Jira: {exc}") from exc

        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise JiraConnectionError(
                f"Error al obtener boards: {response.status_code} - {response.text}"
            )
        return response.json().get("values", [])

    def get_sprints(self, board_id: str, max_results: int = 50) -> list[dict]:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        try:
            with self._http() as client:
                response = client.get(
                    f"/rest/agile/1.0/board/{board_id}/sprint",
                    params={"maxResults": max_results},
                )
        except Exception as exc:
            raise JiraConnectionError(f"Error al consultar sprints de Jira: {exc}") from exc

        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise JiraConnectionError(
                f"Error al obtener sprints: {response.status_code} - {response.text}"
            )
        return response.json().get("values", [])

    def search_issues(self, jql: str, start_at: int = 0, max_results: int = 50) -> dict:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        try:
            with self._http() as client:
                response = client.get(
                    "/rest/api/3/search",
                    params={"jql": jql, "startAt": start_at, "maxResults": max_results},
                )
        except Exception as exc:
            raise JiraConnectionError(f"Error de conexión con la API de Jira: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        if response.status_code == 400:
            raise JiraQueryError(f"Consulta JQL inválida: {response.text}")
        raise JiraConnectionError(
            f"Error al ejecutar JQL: {response.status_code} - {response.text}"
        )
