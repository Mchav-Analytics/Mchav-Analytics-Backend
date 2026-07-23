from fastapi import APIRouter
from app.api.v1.controllers import auth_router, jira_router, projects_router
from app.api.v1.endpoints import jql_queries

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(jira_router, prefix="/jira", tags=["jira"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(jql_queries.router, prefix="/jql", tags=["jql"])
