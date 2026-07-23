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

app = FastAPI(
    title="MCHAV Analytics API",
    description="API para la integración con Jira",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, DOCS_USER)
    correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso a la documentación incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/docs", include_in_schema=False)
async def get_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="MCHAV Analytics API Docs")

@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(username: str = Depends(get_current_username)):
    return get_redoc_html(openapi_url="/openapi.json", title="MCHAV Analytics ReDoc")

@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(get_current_username)):
    return get_openapi(title=app.title, version="1.0.0", description=app.description, routes=app.routes)

@app.on_event("startup")
def startup_event():
    # Auto-migrar esquema de la base de datos para la columna id_board en PostgreSQL y SQLite
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

    db = SessionLocal()
    try:
        # Limpiar cualquier log que haya quedado en estado RUNNING tras reiniciar el servidor
        stuck_logs = db.query(LogsSincronizacion).filter(LogsSincronizacion.resultado == "RUNNING").all()
        for log in stuck_logs:
            log.resultado = "ERROR"
            log.detalle_error = "La sincronización se interrumpió debido a un reinicio del servidor."
        db.commit()
    except Exception as e:
        print(f"Error limpiando logs atascados en inicio: {e}")
    finally:
        db.close()

# Configuración de CORS
origins = [
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Importante para enviar cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MCHAV Analytics"}
