"""Aplicación FastAPI — punto de entrada (Bigger Applications)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.api import api_router
from app.api.v1.endpoints import health
from app.core.config import settings
from app.core.exceptions import AppError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mchav")

# Solo ocultar client_id / client_secret / client credentials location.
# NO tocar username / password (si se ocultan, Swagger “autoriza” vacío).
_SWAGGER_HIDE_CLIENT_FIELDS_CSS = """
<style>
  .swagger-ui .auth-container [id$="client_id"],
  .swagger-ui .auth-container [id$="client_secret"],
  .swagger-ui .auth-container label[for$="client_id"],
  .swagger-ui .auth-container label[for$="client_secret"] {
    display: none !important;
  }
</style>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    const hideClientFields = () => {
      document.querySelectorAll('.swagger-ui .auth-container').forEach((box) => {
        box.querySelectorAll('label').forEach((label) => {
          const t = (label.textContent || '').trim().toLowerCase();
          if (
            t === 'client_id:' ||
            t === 'client_secret:' ||
            t.startsWith('client credentials location')
          ) {
            let row = label.parentElement;
            if (row) row.style.display = 'none';
          }
        });
        box.querySelectorAll('select').forEach((sel) => {
          const row = sel.parentElement;
          if (row) row.style.display = 'none';
        });
      });
    };
    const obs = new MutationObserver(hideClientFields);
    obs.observe(document.body, { childList: true, subtree: true });
    hideClientFields();
  });
</script>
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting MCHAV Analytics Backend (env=%s)", settings.ENV)
    yield
    logger.info("Shutting down MCHAV Analytics Backend")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API intermedia sobre Jira para sincronización ETL y métricas ágiles "
        "(Velocity, Throughput, Lead/Cycle Time).\n\n"
        "**Swagger Authorize:** usuario (email) + contraseña "
        "(`POST /api/auth/local/token`, flujo OAuth2 de FastAPI). "
        "Alternativa JSON: `POST /api/auth/local/login`. "
        "OAuth Jira: `GET /api/auth/oauth/login`."
    ),
    lifespan=lifespan,
    contact={"name": "MCHAV Analytics"},
    docs_url=None,
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="lax",
    https_only=settings.ENV == "prod",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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


@app.get("/docs", include_in_schema=False)
async def swagger_ui() -> HTMLResponse:
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{settings.PROJECT_NAME} - Docs",
        swagger_ui_parameters={"persistAuthorization": True},
    )
    body = html.body
    if isinstance(body, memoryview):
        body = body.tobytes()
    content = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)
    content = content.replace("</head>", f"{_SWAGGER_HIDE_CLIENT_FIELDS_CSS}</head>", 1)
    return HTMLResponse(content=content)


app.include_router(health.router)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
