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

    # Migración dinámica de columnas para la tabla issues (Fase 5 y 6)
    issue_columns = [
        ("assignee_id", "VARCHAR(100)"),
        ("assignee_name", "VARCHAR(150)"),
        ("assignee_email", "VARCHAR(200)"),
        ("issue_type", "VARCHAR(50) DEFAULT 'Story'"),
        ("priority", "VARCHAR(30) DEFAULT 'Medium'"),
        ("epic_key", "VARCHAR(50)"),
        ("epic_name", "VARCHAR(150)"),
        ("components", "TEXT")
    ]
    with engine.connect() as conn:
        for col_name, col_type in issue_columns:
            try:
                conn.execute(text(f"ALTER TABLE issues ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                conn.commit()
            except Exception:
                try:
                    conn.execute(text(f"ALTER TABLE issues ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
                except Exception:
                    pass

    # Creación automática de la tabla usuario_proyecto si no existe (HU-005)
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seeding de roles estándar del sistema (HU-004)
        roles_default = [
            {"nombre_rol": "Administrador", "scopes": "jira:read,jira:sync,projects:write,admin"},
            {"nombre_rol": "Líder Técnico", "scopes": "jira:read,jira:sync,projects:write"},
            {"nombre_rol": "Desarrollador", "scopes": "jira:read"}
        ]
        for r_info in roles_default:
            r_exist = db.query(models.Role).filter(models.Role.nombre_rol == r_info["nombre_rol"]).first()
            if not r_exist:
                db.add(models.Role(nombre_rol=r_info["nombre_rol"], scopes=r_info["scopes"]))
            elif not r_exist.scopes:
                r_exist.scopes = r_info["scopes"]
        db.commit()

        stuck_logs = db.query(LogsSincronizacion).filter(LogsSincronizacion.resultado == "RUNNING").all()
        for log in stuck_logs:
            log.resultado = "ERROR"
            log.detalle_error = "La sincronización se interrumpió debido a un reinicio del servidor."
        db.commit()
    except Exception as e:
        print(f"Error en inicio de servidor: {e}")
    finally:
        db.close()

    # Iniciar motor de sincronización automática en segundo plano (HU-010)
    try:
        from app.core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"Error iniciando scheduler: {e}")

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE MIDDLEWARE DE CORS
# -----------------------------------------------------------------------------
origins = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if FRONTEND_URL == "*" else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar el router maestro
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MCHAV Analytics"}