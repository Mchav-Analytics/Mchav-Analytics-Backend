# app/main.py
# Punto de entrada principal de la aplicación web FastAPI

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import FRONTEND_URL
from app.core.database import engine, SessionLocal
import app.models as models
from app.models import LogsSincronizacion
from app.core.middleware import AuditMiddleware
from app.models.audit import AuditLog
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
app.add_middleware(AuditMiddleware)

def _run_column_migrations():
    with engine.connect() as conn:
        for sql_if_not_exists, sql_fallback in [
            ("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS id_board INTEGER;", "ALTER TABLE proyectos ADD COLUMN id_board INTEGER;"),
            ("ALTER TABLE roles ADD COLUMN IF NOT EXISTS scopes VARCHAR(500) DEFAULT '';", "ALTER TABLE roles ADD COLUMN scopes VARCHAR(500) DEFAULT '';"),
            ("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);", "ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255);"),
        ]:
            try:
                conn.execute(text(sql_if_not_exists))
                conn.commit()
            except Exception:
                try:
                    conn.execute(text(sql_fallback))
                    conn.commit()
                except Exception:
                    pass

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
    models.Base.metadata.create_all(bind=engine)


def _seed_roles_and_users(db):
    roles_default = [
        {"nombre_rol": "Administrador", "scopes": "jira:read,jira:sync,projects:write,admin"},
        {"nombre_rol": "Planificador", "scopes": "jira:read,jira:sync,projects:write"},
        {"nombre_rol": "Desarrollador", "scopes": "jira:read"},
        {"nombre_rol": "Usuario", "scopes": ""}
    ]
    for r_info in roles_default:
        r_exist = db.query(models.Role).filter(models.Role.nombre_rol == r_info["nombre_rol"]).first()
        if not r_exist:
            db.add(models.Role(nombre_rol=r_info["nombre_rol"], scopes=r_info["scopes"]))
    db.commit()

    from app.core.security import hash_password
    default_pwd_hash = hash_password("Mchav2026!")

    users_seed = [
        {"email": "salamancamai12@gmail.com", "nombre": "Michael Salamanca", "rol": "Administrador"},
        {"email": "valentina1025m@gmail.com", "nombre": "Valentina Montalvo", "rol": "Administrador"},
        {"email": "corredorbeltran592@gmail.com", "nombre": "Camilo Corredor", "rol": "Planificador"},
        {"email": "pipealcala22@gmail.com", "nombre": "Felipe Alcalá", "rol": "Administrador"},
        {"email": "stephanyleon326@gmail.com", "nombre": "Stephany León", "rol": "Desarrollador"},
    ]

    for u_info in users_seed:
        u_exist = db.query(models.User).filter(models.User.email == u_info["email"]).first()
        r_target = db.query(models.Role).filter(models.Role.nombre_rol == u_info["rol"]).first()
        if not u_exist and r_target:
            new_u = models.User(
                email=u_info["email"],
                nombre=u_info["nombre"],
                id_rol=r_target.id_rol,
                password_hash=default_pwd_hash,
                activo=True
            )
            db.add(new_u)
        elif u_exist and r_target:
            u_exist.id_rol = r_target.id_rol
            u_exist.nombre = u_info["nombre"]
            if not u_exist.password_hash:
                u_exist.password_hash = default_pwd_hash
            u_exist.activo = True
    db.commit()

    valid_emails = [u["email"] for u in users_seed]
    db.query(models.User).filter(
        (models.User.email.notin_(valid_emails)) | 
        (models.User.nombre == "Usuario") |
        (models.User.email.in_(["dev@mchav.com", "vhoyos@mchav.com", "cgomez@mchav.com", "aftorres@mchav.com"]))
    ).delete(synchronize_session=False)
    db.commit()


def _cleanup_stuck_syncs(db):
    stuck_logs = db.query(LogsSincronizacion).filter(LogsSincronizacion.resultado == "RUNNING").all()
    for log in stuck_logs:
        log.resultado = "ERROR"
        log.detalle_error = "La sincronización se interrumpió debido a un reinicio del servidor."
    db.commit()

    from app.models.metrics import SyncLock
    db.query(SyncLock).delete()
    db.commit()


@app.on_event("startup")
def startup_event():
    _run_column_migrations()

    db = SessionLocal()
    try:
        _seed_roles_and_users(db)
        _cleanup_stuck_syncs(db)
    except Exception as e:
        print(f"Error en inicio de servidor: {e}")
    finally:
        db.close()

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
    allow_origin_regex=r"https?://.*\.nip\.io(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "OPTIONS":
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "private, no-cache, max-age=2"
    return response

# Registrar el router maestro (soporta tanto /api/v1 como /api)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MCHAV Analytics"}