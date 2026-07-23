# app/main.py
# Punto de entrada principal de la aplicación web FastAPI
# Configura el servidor, middleware de CORS, autenticación básica de /docs, router API y eventos de inicio (startup)

import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from app.core.config import FRONTEND_URL, DOCS_USER, DOCS_PASSWORD
from app.core.database import engine, SessionLocal
import app.models as models
from app.models import LogsSincronizacion
from app.api.v1.api import api_router

# Inicialización de la aplicación FastAPI desacoplando las URLs de documentación predeterminadas
app = FastAPI(
    title="MCHAV Analytics API",
    description="API para la integración con Jira y cálculo de métricas ágiles",
    docs_url=None,       # Desactivar la ruta pública /docs por defecto
    redoc_url=None,      # Desactivar la ruta pública /redoc por defecto
    openapi_url=None     # Desactivar el esquema público /openapi.json por defecto
)

# Instancia del esquema de seguridad HTTP Basic Auth para la documentación
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verifica las credenciales HTTP Basic Auth requeridas para visualizar la documentación Swagger/ReDoc.
    Compara en tiempo constante (compare_digest) contra DOCS_USER y DOCS_PASSWORD del .env.
    """
    correct_username = secrets.compare_digest(credentials.username, DOCS_USER)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso a la documentación incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# -----------------------------------------------------------------------------
# RUTAS PROTEGIDAS PARA DOCUMENTACIÓN INTERACTIVA CON SWAGGER Y REDOC
# -----------------------------------------------------------------------------
@app.get("/docs", include_in_schema=False)
async def get_documentation(username: str = Depends(get_current_username)):
    """Ruta protegida por contraseña para renderizar la interfaz gráfica de Swagger UI."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title="MCHAV Analytics API Docs")

@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(username: str = Depends(get_current_username)):
    """Ruta protegida por contraseña para renderizar la interfaz de ReDoc."""
    return get_redoc_html(openapi_url="/openapi.json", title="MCHAV Analytics ReDoc")

@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(get_current_username)):
    """Ruta protegida que expone la especificación en formato JSON OpenAPI 3.0."""
    return get_openapi(title=app.title, version="1.0.0", description=app.description, routes=app.routes)

# -----------------------------------------------------------------------------
# EVENTO DE INICIALIZACIÓN DE LA APLICACIÓN (STARTUP EVENT)
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """
    Ejecutado automáticamente al iniciar el servidor Uvicorn:
    1. Ejecuta migraciones ligeras de esquema de BD (Asegura columna id_board en PostgreSQL/SQLite).
    2. Limpia los logs de sincronización que hayan quedado atascados en estado 'RUNNING' tras un reinicio inesperado.
    """
    # 1. Migración liviana de columnas faltantes
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS id_board INTEGER;"))
            conn.commit()
        except Exception:
            try:
                conn.execute(text("ALTER TABLE proyectos ADD COLUMN id_board INTEGER;"))
                conn.commit()
            except Exception:
                pass

    # 2. Limpieza de logs incompletos
    db = SessionLocal()
    try:
        stuck_logs = db.query(LogsSincronizacion).filter(LogsSincronizacion.resultado == "RUNNING").all()
        for log in stuck_logs:
            log.resultado = "ERROR"
            log.detalle_error = "La sincronización se interrumpió debido a un reinicio del servidor."
        db.commit()
    except Exception as e:
        print(f"Error limpiando logs atascados en inicio: {e}")
    finally:
        db.close()

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE MIDDLEWARE DE CORS (CROSS-ORIGIN RESOURCE SHARING)
# -----------------------------------------------------------------------------
origins = [
    FRONTEND_URL, # Permite peticiones desde la URL del Frontend React
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Permitir envío de cookies HTTP-Only de sesión
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar el router maestro con los prefijos /api/v1 (Versión 1) y /api (compatibilidad)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    """Endpoint de bienvenida e inspección de salud básica (Health Check)."""
    return {"message": "Bienvenido a la API de MCHAV Analytics"}
