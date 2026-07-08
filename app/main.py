import logging
import secrets
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.jira import JiraService
from app.database import check_db_connection, get_db
from app.dependencies import get_current_user, require_role
from app.services import auth as auth_service

app = FastAPI(
    title="MCHAV Analytics Backend",
    version="1.0.0",
)

# logger for debugging
logger = logging.getLogger("mchav.auth")
logging.basicConfig(level=logging.INFO)

# Sesión temporal solo para guardar el 'state' anti-CSRF durante el login.
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

jira_service = JiraService()


# ---------------------------------------------------------------------------
# 1. Login: genera el 'state' y devuelve la URL real de Atlassian
# ---------------------------------------------------------------------------
@app.get("/api/auth/login")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    auth_url = auth_service.build_authorization_url(state)
    return {"auth_url": auth_url}


# ---------------------------------------------------------------------------
# 2. Callback: valida state, intercambia el code, valida el usuario local,
#    guarda el token de Jira y emite el JWT interno.
# ---------------------------------------------------------------------------
@app.get("/api/auth/callback")
async def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    # Debug: registrar el estado almacenado, el estado entrante y la cookie de sesión.
    stored_state = request.session.get("oauth_state")
    try:
        cookie_val = request.cookies.get("session")
    except Exception:
        cookie_val = None
    logger.info("auth_callback called - stored_state=%s, incoming_state=%s, session_cookie=%s", stored_state, state, cookie_val)
    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Error de validación CSRF")
    request.session.pop("oauth_state", None)

    try:
        token_data = await auth_service.exchange_code_for_token(code)
        atlassian_profile = await auth_service.get_atlassian_user_info(
            token_data["access_token"]
        )
        email = atlassian_profile.get("email")

        # CA-03/CA-04/CA-05 HU-001: valida dominio, existencia y estado del usuario
        user = auth_service.get_or_validate_local_user(db, email)
        auth_service.save_or_update_oauth_token(db, user, token_data)
        jwt_token = auth_service.create_jwt_token(user)

    except PermissionError as e:
        # Usuario no registrado / dominio inválido / cuenta inactiva
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error de autenticación con Jira: {e}")

    # Desarrollo: entregamos el JWT al callback del frontend para cerrar el flujo.
    # Producción: preferir cookie HttpOnly/Secure para evitar tokens en URLs.
    query = urlencode({"token": jwt_token})
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{query}")


# ---------------------------------------------------------------------------
# 3. Logout (HU-002)
# ---------------------------------------------------------------------------
@app.post("/api/auth/logout")
async def logout(request: Request):
    # El JWT es stateless: la invalidación real ocurre en el cliente al
    # descartar el token (CA-02 HU-002). Si necesitas invalidación server-side
    # (por ejemplo ante robo de token), agrega una blacklist en Redis/BD.
    request.session.clear()
    return {"status": "success", "detail": "Sesión cerrada"}


# ---------------------------------------------------------------------------
# 4. Endpoint de Jira protegido: usa el token guardado del usuario autenticado
# ---------------------------------------------------------------------------
@app.get("/api/jira/proyecto/{project_key}")
async def obtener_proyecto_jira(
    project_key: str,
    current_user=Depends(get_current_user),
):
    # La consulta a Jira usa la ÚNICA conexión configurada por el Administrador
    # (API Token, HU-006). El JWT del usuario solo controla que esté autenticado
    # y, si se necesita, qué proyectos tiene asignados (HU-005).
    try:
        datos = jira_service.verificar_proyecto(project_key)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not datos:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"status": "success", "data": datos}


# ---------------------------------------------------------------------------
# 5. Ejemplo de endpoint restringido solo a Administrador (HU-003)
# ---------------------------------------------------------------------------
@app.get("/api/admin/ping", dependencies=[Depends(require_role("Administrador"))])
async def admin_ping():
    return {"status": "ok", "detail": "Acceso de administrador confirmado"}


# ---------------------------------------------------------------------------
# 6. Probar la conexión con Jira (HU-006 CA-01/CA-02), solo Administrador
# ---------------------------------------------------------------------------
@app.get(
    "/api/admin/jira/test-connection",
    dependencies=[Depends(require_role("Administrador"))],
)
async def probar_conexion_jira():
    resultado = jira_service.probar_conexion()
    if not resultado["ok"]:
        raise HTTPException(status_code=400, detail=resultado["detail"])
    return {"status": "success", "detail": resultado["detail"], "cuenta": resultado.get("cuenta")}


@app.get("/health")
async def health_check():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
    }