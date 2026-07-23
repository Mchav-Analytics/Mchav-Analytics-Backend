# app/datasources/jira_datasource.py
# Fuente de datos de bajo nivel para la comunicación HTTP asíncrona con la API REST v3 y API Agile 1.0 de Jira Cloud
# Encapsula autenticación por credenciales directas (API Token Basic Auth) o tokens OAuth 2.0 (Bearer)

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
        """
        Determina de forma transparente el método de autenticación a utilizar:
        1. Prioridad: Credenciales de API Token directo configuradas en el sistema / .env (Basic Auth).
        2. Fallback: Token OAuth 2.0 de la sesión activa del usuario (Bearer Token).
        Retorna la URL base y la cabecera (headers) HTTP correspondientes.
        """
        domain = os.getenv("JIRA_DOMAIN", "").strip()
        email = os.getenv("JIRA_EMAIL", "").strip()
        api_token = os.getenv("JIRA_API_TOKEN", "").strip()

        # 1. Intentar Basic Auth con API Token de administrador
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

        # 2. Intentar Bearer Token con OAuth 2.0 de Atlassian
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
        """Envía una petición GET al endpoint /project de Jira para obtener los proyectos accesibles."""
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
        Ejecuta una consulta JQL parametrizada con expansión de historial de cambios (expand=changelog).
        Implementa estrategia de 3 capas para compatibilidad total con Atlassian Change 2046:
        1. GET /search/jql (Endpoint recomendado para nuevas versiones)
        2. POST /search/jql (Payload estructurado)
        3. GET /search (Endpoint legacy con fallback automático)
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
        """Obtiene el registro extenso del historial de cambios (changelog) de un ticket por su ID."""
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
        """Consulta la API de Jira Agile 1.0 para encontrar los tableros asociados a una clave de proyecto."""
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
        """Obtiene la totalidad de los sprints (activos, futuros y cerrados) pertenecientes a un tablero específico."""
        res = await client.get(f"{base_agile_url}/board/{board_id}/sprint?state=active,future,closed&maxResults=100", headers=headers)
        if res.status_code != 200:
            return {"values": []}
        return res.json()
