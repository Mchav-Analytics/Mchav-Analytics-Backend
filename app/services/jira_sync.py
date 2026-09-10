# app/services/jira_sync.py
# Módulo de compatibilidad y delegación para la sincronización de Jira.
# Re-exporta las funciones principales de 'jira_sync_service.py' para evitar romper importaciones existentes.

from app.services.jira_sync_service import (
    run_jira_sync,
    run_jira_sync_task,
    sync_projects,
    sync_issues_for_project,
    get_jira_auth_credentials,
    refresh_user_token
)

# Exportar símbolos de la interfaz del servicio
__all__ = [
    "run_jira_sync",
    "run_jira_sync_task",
    "sync_projects",
    "sync_issues_for_project",
    "get_jira_auth_credentials",
    "refresh_user_token"
]
