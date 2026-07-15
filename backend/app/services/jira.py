# app/services/jira.py
"""
Servicio de conexión a Jira mediante API Token (HU-006).

Esta es la ÚNICA conexión hacia Jira que usa la plataforma: la configura
el Administrador una sola vez (CA-01/CA-03 HU-006) y la usan todos los
endpoints que consultan datos de Jira (proyectos, issues, JQL, etc.).

El login OAuth2 (HU-001) es un flujo aparte que solo identifica al usuario
y le da acceso a la plataforma (JWT interno); no se usa para llamar a Jira.
"""

import requests
from requests.auth import HTTPBasicAuth

from app.core.config import settings
from app.core.exceptions import JiraConnectionError, JiraQueryError


class JiraService:
    def __init__(self):
        self.base_url = settings.JIRA_BASE_URL
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.headers = {"Accept": "application/json"}

    def _auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.email, self.api_token)

    def _configured(self) -> bool:
        return bool(self.base_url and self.email and self.api_token)

    # -----------------------------------------------------------------
    # HU-006 CA-01/CA-02: probar que el token funciona
    # -----------------------------------------------------------------
    def probar_conexion(self) -> dict:
        """Verifica que las credenciales configuradas sean válidas."""
        if not self._configured():
            return {"ok": False, "detail": "Faltan variables de entorno de Jira"}

        url = f"{self.base_url}/rest/api/3/myself"
        try:
            response = requests.get(url, auth=self._auth(), headers=self.headers, timeout=10)
        except Exception as e:
            return {"ok": False, "detail": f"Error de conexión: {e}"}

        if response.status_code == 200:
            return {"ok": True, "detail": "Conexión exitosa", "cuenta": response.json().get("displayName")}
        return {"ok": False, "detail": f"Código {response.status_code}: {response.text}"}

    # -----------------------------------------------------------------
    # Consulta de un proyecto por su key (ej. 'SCRUM')
    # -----------------------------------------------------------------
    def verificar_proyecto(self, project_key: str) -> dict | None:
        if not self._configured():
            raise JiraConnectionError(
                "La conexión con Jira no está configurada (variables de entorno faltantes)."
            )

        url = f"{self.base_url}/rest/api/3/project/{project_key}"
        try:
            response = requests.get(url, auth=self._auth(), headers=self.headers, timeout=10)
        except Exception as e:
            raise JiraConnectionError(f"Error de conexión con la API de Jira: {e}") from e

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None
        raise JiraConnectionError(f"Error al consultar Jira: {response.status_code} - {response.text}")

    def obtener_boards(self, project_key: str) -> list[dict]:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        url = f"{self.base_url}/rest/agile/1.0/board"
        params = {"projectKeyOrId": project_key}
        try:
            response = requests.get(
                url, auth=self._auth(), headers=self.headers, params=params, timeout=15
            )
        except Exception as e:
            raise JiraConnectionError(f"Error al consultar boards de Jira: {e}") from e

        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise JiraConnectionError(
                f"Error al obtener boards: {response.status_code} - {response.text}"
            )
        return response.json().get("values", [])

    def obtener_sprints(self, board_id: str, max_results: int = 50) -> list[dict]:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
        params = {"maxResults": max_results}
        try:
            response = requests.get(
                url, auth=self._auth(), headers=self.headers, params=params, timeout=15
            )
        except Exception as e:
            raise JiraConnectionError(f"Error al consultar sprints de Jira: {e}") from e

        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise JiraConnectionError(
                f"Error al obtener sprints: {response.status_code} - {response.text}"
            )
        return response.json().get("values", [])

    # -----------------------------------------------------------------
    # HU-008: ejecutar queries JQL
    # -----------------------------------------------------------------
    def buscar_issues(self, jql: str, start_at: int = 0, max_results: int = 50) -> dict:
        if not self._configured():
            raise JiraConnectionError("La conexión con Jira no está configurada.")

        url = f"{self.base_url}/rest/api/3/search"
        params = {"jql": jql, "startAt": start_at, "maxResults": max_results}
        try:
            response = requests.get(url, auth=self._auth(), headers=self.headers, params=params, timeout=15)
        except Exception as e:
            raise JiraConnectionError(f"Error de conexión con la API de Jira: {e}") from e

        if response.status_code == 200:
            return response.json()
        if response.status_code == 400:
            raise JiraQueryError(f"Consulta JQL inválida: {response.text}")
        raise JiraConnectionError(f"Error al ejecutar JQL: {response.status_code} - {response.text}")
