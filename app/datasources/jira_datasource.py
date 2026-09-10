# app/datasources/jira_datasource.py
# Fuente de datos de bajo nivel para la comunicación HTTP asíncrona con la API REST v3 y API Agile 1.0 de Jira Cloud
# Encapsula autenticación por credenciales directas (API Token Basic Auth) o tokens OAuth 2.0 (Bearer)
# Incorpora resiliencia con Tenacity (Exponential Backoff & Jitter para Rate Limiting HTTP 429)

import base64
import os
import httpx
from typing import Any, Dict
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
import app.models as models

class JiraTransientError(Exception):
    """Excepción para errores efímeros de red o rate-limiting (429, 502, 503, 504) que deben ser reintentados."""
    pass

# Decorador de reintentos exponenciales para las operaciones HTTP contra Jira Cloud
jira_retry_decorator = retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, JiraTransientError)),
    wait=wait_exponential_jitter(initial=1, max=10),
    stop=stop_after_attempt(4),
    reraise=True
)

class JiraDatasource:
    """
    Fuente de datos encargada de interactuar directamente con la API REST de Atlassian Jira.
    Soporta autenticación mediante OAuth 2.0 (3LO) o API Token directo.
    """

    @staticmethod
    def get_auth_credentials(db: Session, user: models.User) -> tuple[str, dict]:
        """
        Determina de forma transparente el método de autenticación a utilizar:
        1. Prioridad ABSOLUTA: Token OAuth 2.0 de la sesión activa del usuario (Bearer Token).
        2. Fallback (solo si no hay OAuth): Basic Auth con credenciales del .env
        Retorna la URL base y la cabecera (headers) HTTP correspondientes.
        """
        # 1. Intentar Bearer Token con OAuth 2.0 de Atlassian
        if user and user.cloud_id and user.access_token:
            base_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
            headers = {
                "Authorization": f"Bearer {user.access_token}",
                "Accept": "application/json"
            }
            return base_url, headers

        domain = os.getenv("JIRA_DOMAIN", "").strip()
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        # Importación diferida para evitar ciclos de importación
        from app.core.security import decrypt_jira_token

        # 2. Intentar Basic Auth con API Token de administrador del sistema (.env)
        if domain and email and api_token:
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            raw_system_token = decrypt_jira_token(api_token)
            credentials = f"{email}:{raw_system_token}"
            encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            base_url = f"{domain}/rest/api/3"
            headers = {
                "Authorization": f"Basic {encoded_creds}",
                "Accept": "application/json"
            }
            return base_url, headers

        raise Exception("No hay credenciales OAuth 2.0 ni de sistema configuradas en Jira.")

    @staticmethod
    @jira_retry_decorator
    async def fetch_projects(client: httpx.AsyncClient, base_url: str, headers: Dict[str, str]) -> Any:
        """Envía una petición GET al endpoint /project de Jira para obtener los proyectos accesibles."""
        res = await client.get(f"{base_url}/project", headers=headers)
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero de Jira ({res.status_code}): {res.text}")
        if res.status_code != 200:
            raise Exception(f"Error al obtener proyectos de Jira: {res.text}")
        return res.json()

    @staticmethod
    @jira_retry_decorator
    async def fetch_issues_jql(
        client: httpx.AsyncClient, 
        base_url: str, 
        headers: Dict[str, str], 
        jql: str, 
        start_at: int = 0, 
        max_results: int = 100,
        next_page_token: str = None
    ) -> Any:
        """
        Ejecuta una consulta JQL parametrizada con reintentos de resiliencia (Tenacity).
        """
        fields_str = "summary,status,created,updated,issuetype,assignee,priority,sprint,customfield_10020,customfield_10028,customfield_10016,customfield_10026,storypoints"
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "expand": "changelog",
            "fields": fields_str
        }
        # La API v3 de Jira en GET /search/jql ignora el parámetro fields si no está formateado correctamente, devolviendo solo IDs.
        # Por lo tanto, SIEMPRE utilizamos POST para consultas JQL que requieren campos específicos.
        payload = {
            "jql": jql,
            "maxResults": max_results,
            "expand": "changelog",
            "fields": [f.strip() for f in fields_str.split(",")]
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
            
        print("PAYLOAD ENVIADO A JIRA:", payload)
        res_post = await client.post(f"{base_url}/search/jql", headers=headers, json=payload)
        if res_post.status_code == 200:
            return res_post.json()
        if res_post.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Rate-limiting o falla de Jira Cloud (HTTP {res_post.status_code})")

        # 3. Fallback al endpoint legacy /search
        res_legacy = await client.get(f"{base_url}/search", headers=headers, params=params)
        if res_legacy.status_code == 200:
            return res_legacy.json()

        raise Exception(f"Error al buscar issues con JQL '{jql}': Falló POST ({res_post.text}) y GET Legacy ({res_legacy.text if 'res_legacy' in locals() else 'N/A'})")

    @staticmethod
    @jira_retry_decorator
    async def fetch_issue_changelog(
        client: httpx.AsyncClient, 
        base_url: str, 
        headers: Dict[str, str], 
        issue_id: str
    ) -> Any:
        """Obtiene el registro extenso del historial de cambios (changelog) de un ticket por su ID."""
        res = await client.get(f"{base_url}/issue/{issue_id}/changelog", headers=headers)
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero de Jira changelog ({res.status_code})")
        if res.status_code != 200:
            return {"values": []}
        return res.json()

    @staticmethod
    @jira_retry_decorator
    async def fetch_boards_for_project(
        client: httpx.AsyncClient, 
        base_agile_url: str, 
        headers: Dict[str, str], 
        project_key: str
    ) -> Any:
        """Consulta la API de Jira Agile 1.0 para encontrar los tableros asociados a una clave de proyecto."""
        res = await client.get(f"{base_agile_url}/board?projectKeyOrId={project_key}", headers=headers)
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero de Jira Agile Board ({res.status_code})")
        if res.status_code != 200:
            return {"values": []}
        return res.json()

    @staticmethod
    @jira_retry_decorator
    async def fetch_board_sprints(
        client: httpx.AsyncClient, 
        base_agile_url: str, 
        headers: Dict[str, str], 
        board_id: int
    ) -> Any:
        """Obtiene la totalidad de los sprints (activos, futuros y cerrados) pertenecientes a un tablero específico."""
        res = await client.get(f"{base_agile_url}/board/{board_id}/sprint?state=active,future,closed&maxResults=100", headers=headers)
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero de Jira Agile Sprints ({res.status_code})")
        if res.status_code != 200:
            return {"values": []}
        return res.json()

    @staticmethod
    def get_system_credentials() -> tuple[str, dict]:
        """Obtiene las credenciales administrativas de sistema (Basic Auth con API Token) desde .env."""
        domain = os.getenv("JIRA_DOMAIN", "").strip()
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        from app.core.security import decrypt_jira_token

        if domain and email and api_token:
            if not domain.startswith("http://") and not domain.startswith("https://"):
                domain = f"https://{domain}"
            raw_system_token = decrypt_jira_token(api_token)
            credentials = f"{email}:{raw_system_token}"
            encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            base_url = f"{domain}/rest/api/3"
            headers = {
                "Authorization": f"Basic {encoded_creds}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            return base_url, headers
        raise Exception("No hay credenciales de sistema configuradas en Jira.")

    @staticmethod
    def get_auth_credentials(db: Session, user: models.User) -> tuple[str, dict]:
        """
        Determina de forma transparente el método de autenticación a utilizar:
        1. Prioridad: Token OAuth 2.0 de la sesión activa del usuario (Bearer Token).
        2. Fallback: Basic Auth con credenciales del .env
        Retorna la URL base y la cabecera (headers) HTTP correspondientes.
        """
        # 1. Intentar Bearer Token con OAuth 2.0 de Atlassian
        if user and user.cloud_id and user.access_token:
            base_url = f"https://api.atlassian.com/ex/jira/{user.cloud_id}/rest/api/3"
            headers = {
                "Authorization": f"Bearer {user.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            return base_url, headers

        return JiraDatasource.get_system_credentials()

    @staticmethod
    @jira_retry_decorator
    async def fetch_issue_transitions(
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict[str, str],
        issue_id_or_key: str
    ) -> Any:
        """Obtiene las transiciones de estado disponibles y permitidas actualmente para una issue en Jira."""
        res = await client.get(f"{base_url}/issue/{issue_id_or_key}/transitions?expand=transitions.fields", headers=headers)
        if res.status_code in (401, 403):
            # Si el token OAuth carece de scope o expiró, intentar con credenciales de sistema
            try:
                sys_url, sys_headers = JiraDatasource.get_system_credentials()
                res_sys = await client.get(f"{sys_url}/issue/{issue_id_or_key}/transitions?expand=transitions.fields", headers=sys_headers)
                if res_sys.status_code == 200:
                    return res_sys.json()
            except Exception:
                pass
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero al obtener transiciones de Jira ({res.status_code})")
        if res.status_code != 200:
            raise Exception(f"Error al obtener transiciones para '{issue_id_or_key}' de Jira (HTTP {res.status_code}): {res.text}")
        return res.json()

    @staticmethod
    @jira_retry_decorator
    async def execute_issue_transition(
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict[str, str],
        issue_id_or_key: str,
        transition_id: str
    ) -> Any:
        """Ejecuta una transición de estado en Jira Cloud mediante POST /issue/{key}/transitions."""
        payload = {
            "transition": {
                "id": str(transition_id)
            }
        }
        res = await client.post(f"{base_url}/issue/{issue_id_or_key}/transitions", headers=headers, json=payload)
        
        # Si el token OAuth del usuario tiene solo scope de lectura ("scope does not match"), fallback a credenciales de sistema
        if res.status_code in (401, 403) and ("scope" in res.text.lower() or "unauthorized" in res.text.lower()):
            try:
                sys_url, sys_headers = JiraDatasource.get_system_credentials()
                res_sys = await client.post(f"{sys_url}/issue/{issue_id_or_key}/transitions", headers=sys_headers, json=payload)
                if res_sys.status_code in (200, 204):
                    return {"status": "success", "status_code": res_sys.status_code}
                elif res_sys.status_code not in (429, 502, 503, 504):
                    raise Exception(f"Jira rechazó la transición (HTTP {res_sys.status_code}): {res_sys.text}")
            except Exception as e:
                if not isinstance(e, JiraTransientError):
                    raise e

        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero al ejecutar transición en Jira ({res.status_code})")
        if res.status_code not in (200, 204):
            raise Exception(f"Jira rechazó la transición (HTTP {res.status_code}): {res.text}")
        return {"status": "success", "status_code": res.status_code}

    @staticmethod
    @jira_retry_decorator
    async def fetch_issue_details(
        client: httpx.AsyncClient,
        base_url: str,
        headers: Dict[str, str],
        issue_id_or_key: str
    ) -> Any:
        """Obtiene la información y estado actual de una issue directamente de Jira."""
        res = await client.get(f"{base_url}/issue/{issue_id_or_key}?fields=summary,status,priority,issuetype,assignee,created,updated,resolutiondate", headers=headers)
        if res.status_code in (401, 403):
            try:
                sys_url, sys_headers = JiraDatasource.get_system_credentials()
                res_sys = await client.get(f"{sys_url}/issue/{issue_id_or_key}?fields=summary,status,priority,issuetype,assignee,created,updated,resolutiondate", headers=sys_headers)
                if res_sys.status_code == 200:
                    return res_sys.json()
            except Exception:
                pass
        if res.status_code in (429, 502, 503, 504):
            raise JiraTransientError(f"Error efímero al consultar issue en Jira ({res.status_code})")
        if res.status_code != 200:
            raise Exception(f"Error al consultar issue '{issue_id_or_key}' en Jira (HTTP {res.status_code}): {res.text}")
        return res.json()
