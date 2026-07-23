"""
Modulo legacy de endpoints de proyectos. Re-exporta todos los simbolos para compatibilidad con la suite de pruebas.
"""
from app.api.v1.controllers.projects_controller import (
    router, 
    get_projects, 
    get_project_kpis, 
    get_project_sprints, 
    get_project_unique_statuses, 
    get_project_mappings, 
    save_project_mappings
)
from app.api.v1.deps import get_current_user_id, check_user_exists
from app.repositories import user_repo, project_repo, kpi_repo, sprint_repo, issue_repo, transition_repo, mapping_repo
from app.services.kpi import calculate_and_save_kpis

__all__ = [
    "router", 
    "get_projects", 
    "get_project_kpis", 
    "get_project_sprints", 
    "get_project_unique_statuses", 
    "get_project_mappings", 
    "save_project_mappings",
    "get_current_user_id",
    "check_user_exists",
    "user_repo",
    "project_repo",
    "kpi_repo",
    "sprint_repo",
    "issue_repo",
    "transition_repo",
    "mapping_repo",
    "calculate_and_save_kpis"
]
