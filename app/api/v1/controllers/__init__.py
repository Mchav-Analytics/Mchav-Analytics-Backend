# Modulo de Controladores HTTP de FastAPI para la API v1
from app.api.v1.controllers.auth_controller import router as auth_router
from app.api.v1.controllers.jira_controller import router as jira_router
from app.api.v1.controllers.projects_controller import router as projects_router
from app.api.v1.controllers.jql_controller import router as jql_router
from app.api.v1.controllers.users_controller import router as users_router
from app.api.v1.controllers.reports_controller import router as reports_router
from app.api.v1.controllers.developers_controller import router as developers_router
from app.api.v1.controllers.alerts_controller import router as alerts_router

__all__ = ["auth_router", "jira_router", "projects_router", "jql_router", "users_router", "reports_router", "developers_router", "alerts_router"]
