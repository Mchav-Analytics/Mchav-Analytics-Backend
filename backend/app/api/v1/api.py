"""Agregador de routers API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    health,
    jira,
    jira_queries,
    kpis,
    projects,
)

api_router = APIRouter()
api_router.include_router(auth.oauth_router)
api_router.include_router(auth.local_router)
api_router.include_router(auth.router)
api_router.include_router(jira.router)
api_router.include_router(jira_queries.router)
api_router.include_router(projects.router)
api_router.include_router(kpis.router)
api_router.include_router(admin.router)
