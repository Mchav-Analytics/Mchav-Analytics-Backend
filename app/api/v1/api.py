# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.controllers import auth_router, jira_router, projects_router, jql_router, users_router, reports_router, developers_router

api_router = APIRouter()

# Registrar los sub-routers asignándoles prefijos de ruta y etiquetas (tags) para Swagger
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])          # /api/v1/auth
api_router.include_router(users_router, prefix="/users", tags=["users"])        # /api/v1/users
api_router.include_router(jira_router, prefix="/jira", tags=["jira"])          # /api/v1/jira
api_router.include_router(projects_router, prefix="/projects", tags=["projects"]) # /api/v1/projects
api_router.include_router(jql_router, prefix="/jql", tags=["jql"])             # /api/v1/jql
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])  # /api/v1/reports
api_router.include_router(developers_router, prefix="/developers", tags=["developers"]) # /api/v1/developers



