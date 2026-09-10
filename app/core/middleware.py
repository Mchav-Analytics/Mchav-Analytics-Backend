# app/core/middleware.py
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import SESSION_SECRET_KEY
from app.core.security import JWT_ALGORITHM
from app.models.audit import AuditLog

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if response.status_code < 400 and request.method != "OPTIONS":
            path = request.url.path
            if path.startswith("/api/v1") and "/users/" not in path: # Evitar loopear el propio log
                user_email = "Anónimo"
                
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        payload = jwt.decode(token, SESSION_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                        user_email = payload.get("sub", "Anónimo")
                    except Exception:
                        pass
                
                description = f"Ejecutó {request.method} en {path}"
                action_type = "SYSTEM"
                
                if "/auth/login" in path:
                    description = "Inició sesión en la plataforma"
                    action_type = "LOGIN"
                elif "/projects" in path and request.method == "GET":
                    description = "Consultó el listado de proyectos y métricas"
                    action_type = "USER"
                elif "/jira/sync" in path:
                    description = "Ejecutó sincronización ETL de Jira"
                    action_type = "SYSTEM"
                elif "/users" in path and request.method == "PUT":
                    description = "Modificó configuración o rol de usuario"
                    action_type = "SYSTEM"

                db: Session = SessionLocal()
                try:
                    log = AuditLog(
                        user_email=user_email,
                        action_path=path,
                        method=request.method,
                        description=description,
                        type=action_type
                    )
                    db.add(log)
                    db.commit()
                except Exception as e:
                    pass
                finally:
                    db.close()

        return response
