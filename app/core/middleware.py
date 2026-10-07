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
    def _extract_user_email(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return "Anónimo"
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SESSION_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload.get("sub", "Anónimo")
        except Exception:
            return "Anónimo"

    def _get_action_details(self, path: str, method: str) -> tuple[str, str]:
        if "/auth/login" in path:
            return "Inició sesión en la plataforma", "LOGIN"
        if "/projects" in path and method == "GET":
            return "Consultó el listado de proyectos y métricas", "USER"
        if "/jira/sync" in path:
            return "Ejecutó sincronización ETL de Jira", "SYSTEM"
        if "/users" in path and method == "PUT":
            return "Modificó configuración o rol de usuario", "SYSTEM"
        return f"Ejecutó {method} en {path}", "SYSTEM"

    def _save_audit_log(self, user_email: str, path: str, method: str, description: str, action_type: str) -> None:
        db: Session = SessionLocal()
        try:
            log = AuditLog(
                user_email=user_email,
                action_path=path,
                method=method,
                description=description,
                type=action_type
            )
            db.add(log)
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if response.status_code < 400 and request.method != "OPTIONS":
            path = request.url.path
            if path.startswith("/api/v1") and "/users/" not in path:
                user_email = self._extract_user_email(request)
                description, action_type = self._get_action_details(path, request.method)
                self._save_audit_log(user_email, path, request.method, description, action_type)

        return response

