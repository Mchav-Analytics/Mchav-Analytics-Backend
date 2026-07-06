from fastapi import APIRouter
from app.api.v1.endpoints import auth, jira, projects

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(jira.router, prefix="/jira", tags=["jira"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
