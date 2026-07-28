# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.controllers import auth_controller, jira_router, projects_router # Importa el módulo completo o ajusta el nombre
from app.api.v1.endpoints import jql_queries

api_router = APIRouter()

# Usa auth_controller.router en lugar de auth_router
api_router.include_router(auth_controller.router, prefix="/auth", tags=["auth"])          # /api/v1/auth
api_router.include_router(jira_router, prefix="/jira", tags=["jira"])          # /api/v1/jira
api_router.include_router(projects_router, prefix="/projects", tags=["projects"]) # /api/v1/projects
api_router.include_router(jql_queries.router, prefix="/jql", tags=["jql"])     # /api/v1/jql