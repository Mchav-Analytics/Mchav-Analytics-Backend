# app/main.py
# Punto de entrada principal de la aplicación web FastAPI

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import FRONTEND_URL
from app.core.database import engine, SessionLocal
import app.models as models
from app.models import LogsSincronizacion
from app.api.v1.api import api_router
from fastapi import APIRouter
from app.api.v1.controllers import auth_controller
# Inicialización de FastAPI con las rutas de documentación estándar (libres de HTTP Basic)
app = FastAPI(
    title="MCHAV Analytics API",
    description="API para la integración con Jira y cálculo de métricas ágiles"
)

# -----------------------------------------------------------------------------
# EVENTO DE INICIALIZACIÓN DE LA APLICACIÓN (STARTUP EVENT)
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
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
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE roles ADD COLUMN IF NOT EXISTS scopes VARCHAR(500) DEFAULT '';"))
            conn.commit()
        except Exception:
            try:
                conn.execute(text("ALTER TABLE roles ADD COLUMN scopes VARCHAR(500) DEFAULT '';"))
                conn.commit()
            except Exception:
                pass
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
            conn.commit()
        except Exception:
            try:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255);"))
                conn.commit()
            except Exception:
                pass
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
# CONFIGURACIÓN DE MIDDLEWARE DE CORS
# -----------------------------------------------------------------------------
origins = [
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar el router maestro
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MCHAV Analytics"}