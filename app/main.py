import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.exceptions import AppError
from app.routers import admin, auth, health, jira, kpis, projects

app = FastAPI(
    title="MCHAV Analytics Backend",
    version="1.1.0",
    description="Capa intermedia sobre Jira para métricas y calidad operativa.",
)

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="lax",
    https_only=settings.ENV == "prod",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.message},
    )


app.include_router(auth.router)
app.include_router(jira.router)
app.include_router(projects.router)
app.include_router(kpis.router)
app.include_router(admin.router)
app.include_router(health.router)
