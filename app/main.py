import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import FRONTEND_URL
from app.core.database import engine
import app.models as models
from app.api.v1.api import api_router

# Crear tablas en la base de datos si no existen
# AHORA GESTIONADO POR ALEMBIC
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MCHAV Analytics API", description="API para la integración con Jira")

from app.core.database import SessionLocal
from app.models import LogsSincronizacion

@app.on_event("startup")
def startup_event():
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
