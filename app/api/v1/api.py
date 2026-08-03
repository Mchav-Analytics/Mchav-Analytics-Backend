# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.controllers import auth_controller, jira_router, projects_router
from app.api.v1.controllers import jql_controller  # <-- Cambiar la importación al controlador correcto

api_router = APIRouter()

api_router.include_router(auth_controller.router, prefix="/auth", tags=["auth"])          # /api/v1/auth
api_router.include_router(jira_router, prefix="/jira", tags=["jira"])          # /api/v1/jira
api_router.include_router(projects_router, prefix="/projects", tags=["projects"]) # /api/v1/projects
api_router.include_router(jql_controller.router, prefix="/jql", tags=["jql"])     # <-- Usar jql_controller.router