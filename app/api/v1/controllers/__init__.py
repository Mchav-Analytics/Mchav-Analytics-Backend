# Modulo de Controladores HTTP de FastAPI para la API v1
from app.api.v1.controllers.auth_controller import router as auth_router
from app.api.v1.controllers.jira_controller import router as jira_router
from app.api.v1.controllers.projects_controller import router as projects_router

__all__ = ["auth_router", "jira_router", "projects_router"]
