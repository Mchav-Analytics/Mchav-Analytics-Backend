# app/api/v1/api.py
# Router maestro de la versión 1 (v1) de la API REST
# Agrupa e incluye todos los sub-routers de controladores (Autenticación, Jira, Proyectos, Consultas JQL)

from fastapi import APIRouter
from app.api.v1.controllers import auth_router, jira_router, projects_router, jql_router

# Crear la instancia del router maestro para la v1 de la API
api_router = APIRouter()

# Registrar los sub-routers asignándoles prefijos de ruta y etiquetas (tags) para Swagger
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])          # /api/v1/auth
api_router.include_router(jira_router, prefix="/jira", tags=["jira"])          # /api/v1/jira
api_router.include_router(projects_router, prefix="/projects", tags=["projects"]) # /api/v1/projects
api_router.include_router(jql_router, prefix="/jql", tags=["jql"])             # /api/v1/jql
