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
            {"nombre_rol": "Planificador", "scopes": "jira:read,jira:sync,projects:write"},
            {"nombre_rol": "Desarrollador", "scopes": "jira:read"}
        ]
        for r_info in roles_default:
            r_exist = db.query(models.Role).filter(models.Role.nombre_rol == r_info["nombre_rol"]).first()
            if not r_exist:
                db.add(models.Role(nombre_rol=r_info["nombre_rol"], scopes=r_info["scopes"]))
        db.commit()

        # Seeding de los 5 usuarios principales del sistema con sus roles respectivos
        from app.core.security import hash_password
        default_pwd_hash = hash_password("Mchav2026!")

        users_seed = [
            {"email": "salamancamai12@gmail.com", "nombre": "Michael Salamanca", "rol": "Administrador"},
            {"email": "valentina1025m@gmail.com", "nombre": "Valentina Martínez", "rol": "Administrador"},
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

        # Eliminar usuarios obsoletos/legados para que queden ÚNICAMENTE las 5 cuentas oficiales
        valid_emails = [u["email"] for u in users_seed]
        db.query(models.User).filter(
            (models.User.email.notin_(valid_emails)) | 
            (models.User.nombre == "Usuario") |
            (models.User.email.in_(["dev@mchav.com", "vhoyos@mchav.com", "cgomez@mchav.com", "aftorres@mchav.com"]))
        ).delete(synchronize_session=False)
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

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

# Registrar el router maestro (soporta tanto /api/v1 como /api)
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de MCHAV Analytics"}