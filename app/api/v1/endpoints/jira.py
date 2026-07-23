"""
Modulo legacy de endpoints de Jira. Re-exporta todos los simbolos para compatibilidad con la suite de pruebas.
"""
from app.api.v1.controllers.jira_controller import (
    router, 
    get_jira_metrics, 
    trigger_jira_sync, 
    get_sync_logs, 
    jira_webhook,
    metrics_cache
)
from app.api.v1.deps import get_current_user_id, check_user_exists
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, log_repo
from app.services.jira_sync import run_jira_sync as run_jira_sync_task, get_jira_auth_credentials
from app.services.kpi import calculate_and_save_kpis

__all__ = [
    "router", 
    "get_jira_metrics", 
    "trigger_jira_sync", 
    "get_sync_logs", 
    "jira_webhook",
    "metrics_cache",
    "get_current_user_id",
    "check_user_exists",
    "user_repo",
    "project_repo",
    "sprint_repo",
    "issue_repo",
    "transition_repo",
    "log_repo",
    "run_jira_sync_task",
    "get_jira_auth_credentials",
    "calculate_and_save_kpis"
]
