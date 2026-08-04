# app/api/v1/api.py
from fastapi import APIRouter, Depends
from app.api.v1.controllers import auth_router, jira_router, projects_router, jql_router
from app.core.security import get_current_user

api_router = APIRouter()

# Registrar los sub-routers asignándoles prefijos de ruta y etiquetas (tags) para Swagger
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

api_router.include_router(
    jira_router, 
    prefix="/jira", 
    tags=["jira"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    projects_router, 
    prefix="/projects", 
    tags=["projects"],
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(
    jql_router, 
    prefix="/jql", 
    tags=["jql"],
    dependencies=[Depends(get_current_user)]
)
