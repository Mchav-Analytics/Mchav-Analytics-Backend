import base64
import httpx
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import JIRA_DOMAIN, JIRA_EMAIL, JIRA_API_TOKEN
import app.models as models

class JiraDatasource:
    """
    Fuente de datos de bajo nivel para la comunicación HTTP con la API REST v3 y Agile v1 de Atlassian Jira.
    Administra la autenticación dinámica (Basic Auth por API Token vs Bearer Token por OAuth 2.0).
    """

    @staticmethod
    def get_auth_credentials(db: Session, user: Optional[models.User]) -> Tuple[str, Dict[str, str]]:
        """
        Calcula y retorna la URL base y los encabezados HTTP para la API de Jira.
        Prioridad:
        1. Credenciales de API Token personalizadas por el usuario.
        2. Credenciales por defecto del archivo .env.
        3. Token OAuth 2.0 de Atlassian.
        """
        domain = None
        email = None
        token = None

        if user and user.api_token_vinculado and user.jira_domain and user.jira_email and user.jira_api_token:
            domain = user.jira_domain.rstrip('/')
            email = user.jira_email.strip()
            token = user.jira_api_token.strip()
        elif JIRA_DOMAIN and JIRA_EMAIL and JIRA_API_TOKEN:
            domain = JIRA_DOMAIN.rstrip('/')
            email = JIRA_EMAIL.strip()
            token = JIRA_API_TOKEN.strip()

        if domain and email and token:
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            credentials = f"{email}:{token}"
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
        """Realiza una consulta de tickets mediante JQL (Jira Query Language)."""
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,status,created,updated,issuetype,assignee,priority,sprint,customfield_10020"
        }
        res = await client.get(f"{base_url}/search", headers=headers, params=params)
        if res.status_code != 200:
            raise Exception(f"Error al buscar issues con JQL '{jql}': {res.text}")
        return res.json()

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
    async def fetch_board_sprints(
        client: httpx.AsyncClient, 
        base_agile_url: str, 
        headers: Dict[str, str], 
        board_id: int
    ) -> Any:
        """Obtiene los sprints asociados a un tablero Agile especifico."""
        res = await client.get(f"{base_agile_url}/board/{board_id}/sprint", headers=headers)
        if res.status_code != 200:
            return {"values": []}
        return res.json()
