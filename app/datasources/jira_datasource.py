import base64
import os
import httpx
from typing import Any, Dict
from sqlalchemy.orm import Session
import app.models as models

class JiraDatasource:
    """
    Fuente de datos encargada de interactuar directamente con la API REST de Atlassian Jira.
    Soporta autenticación mediante OAuth 2.0 (3LO) o API Token directo.
    """

    @staticmethod
    def get_auth_credentials(db: Session, user: models.User) -> tuple[str, dict]:
        """Obtiene la URL base y los encabezados de autenticación para las peticiones HTTP a Jira."""
        domain = os.getenv("JIRA_DOMAIN", "").strip()
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        if domain and email and api_token:
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            credentials = f"{email}:{api_token}"
            encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            base_url = f"{domain}/rest/api/3"
            headers = {
                "Authorization": f"Basic {encoded_creds}",
                "Accept": "application/json"
            }
            return base_url, headers

        if user and user.cloud_id and user.access_token:
            base_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
            headers = {
                "Authorization": f"Bearer {user.access_token}",
                "Accept": "application/json"
            }
            return base_url, headers

        raise Exception("No hay credenciales de Jira configuradas. Por favor vincula tu API Token de Jira en tu perfil o en el .env.")

    @staticmethod
    async def fetch_projects(client: httpx.AsyncClient, base_url: str, headers: Dict[str, str]) -> Any:
        """Obtiene la lista completa de proyectos visibles en Jira."""
        res = await client.get(f"{base_url}/project", headers=headers)
        if res.status_code != 200:
            raise Exception(f"Error al obtener proyectos de Jira: {res.text}")
        return res.json()

    @staticmethod
    async def fetch_issues_jql(
        client: httpx.AsyncClient, 
        base_url: str, 
        headers: Dict[str, str], 
        jql: str, 
        start_at: int = 0, 
        max_results: int = 100
    ) -> Any:
        """
        Realiza una consulta de tickets mediante JQL con expansión de historial (changelog).
        Soporta migración Atlassian Change 2046 (/search/jql).
        """
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "expand": "changelog",
            "fields": "summary,status,created,updated,issuetype,assignee,priority,sprint,customfield_10020"
        }
        
        # 1. Intentar con la nueva API recomendada /search/jql (GET)
        res = await client.get(f"{base_url}/search/jql", headers=headers, params=params)
        if res.status_code == 200:
            return res.json()

        # 2. Intentar POST /search/jql (Payload estándar de Atlassian)
        payload = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "expand": ["changelog"],
            "fields": ["summary", "status", "created", "updated", "issuetype", "assignee", "priority", "sprint", "customfield_10020"]
        }
        res_post = await client.post(f"{base_url}/search/jql", headers=headers, json=payload)
        if res_post.status_code == 200:
            return res_post.json()

        # 3. Fallback al endpoint legacy /search
        res_legacy = await client.get(f"{base_url}/search", headers=headers, params=params)
        if res_legacy.status_code == 200:
            return res_legacy.json()

        raise Exception(f"Error al buscar issues con JQL '{jql}': {res.text} | {res_post.text}")

    @staticmethod
    async def fetch_issue_changelog(
        client: httpx.AsyncClient, 
        base_url: str, 
        headers: Dict[str, str], 
        issue_id: str
    ) -> Any:
        """Obtiene el historial completo de transiciones de un ticket."""
        res = await client.get(f"{base_url}/issue/{issue_id}/changelog", headers=headers)
        if res.status_code != 200:
            return {"values": []}
        return res.json()

    @staticmethod
    async def fetch_boards_for_project(
        client: httpx.AsyncClient, 
        base_agile_url: str, 
        headers: Dict[str, str], 
        project_key: str
    ) -> Any:
        """Busca tableros asociados a un proyecto mediante la API Agile 1.0."""
        res = await client.get(f"{base_agile_url}/board?projectKeyOrId={project_key}", headers=headers)
        if res.status_code != 200:
            return {"values": []}
        return res.json()

    @staticmethod
    async def fetch_board_sprints(
        client: httpx.AsyncClient, 
        base_agile_url: str, 
        headers: Dict[str, str], 
        board_id: int
    ) -> Any:
        """Obtiene TODOS los sprints (activos, futuros y cerrados) de un tablero."""
        res = await client.get(f"{base_agile_url}/board/{board_id}/sprint?state=active,future,closed&maxResults=100", headers=headers)
        if res.status_code != 200:
            return {"values": []}
        return res.json()
