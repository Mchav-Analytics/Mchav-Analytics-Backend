"""Scopes OAuth2 de la API MCHAV (permisos de aplicación).

Siguen el estándar OAuth2 / OpenAPI documentado por FastAPI:
https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/
"""

from __future__ import annotations

# Declaración de scopes disponibles (aparecen en /docs → Authorize).
SCOPES: dict[str, str] = {
    "me": "Leer información del usuario autenticado",
    "projects:read": "Listar y consultar proyectos, sprints e issues locales",
    "projects:sync": "Sincronizar proyectos desde Jira hacia MCHAV",
    "jira:read": "Consultar Jira en vivo (proyectos, JQL y métricas)",
    "kpis:read": "Consultar KPIs de sprints",
    "kpis:compute": "Calcular y persistir KPIs",
    "admin": "Acceso a endpoints administrativos",
}

# Mapeo rol interno → scopes emitidos en el JWT.
ROLE_SCOPES: dict[str, list[str]] = {
    "Administrador": list(SCOPES.keys()),
    "Consultor": [
        "me",
        "projects:read",
        "jira:read",
        "kpis:read",
    ],
}


def scopes_for_role(role_name: str) -> list[str]:
    return list(ROLE_SCOPES.get(role_name, ["me"]))
