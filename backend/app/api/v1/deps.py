"""Dependencias compartidas API v1 (inyección de abstracciones)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, scopes_from_payload
from app.datasources.atlassian_oauth_client import AtlassianOAuthClient
from app.datasources.jira_client import JiraClient
from app.db.session import get_db
from app.dtos.auth import TokenDataDTO
from app.models import User
from app.ports.jira_gateway import JiraGateway
from app.ports.oauth_gateway import AtlassianOAuthGateway
from app.repositories import UserRepository
from app.services.jira_query_service import JiraQueryService
from app.services.kpi_service import KpiService
from app.services.project_service import ProjectService
from app.services.sync_service import SyncService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/local/token",
    auto_error=True,
)


def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenDataDTO(
            sub=str(user_id),
            scopes=scopes_from_payload(payload),
            email=payload.get("email"),
            role=payload.get("role"),
        )
    except (ValueError, ValidationError) as exc:
        raise credentials_exception from exc

    user = UserRepository(db).get_by_id(int(token_data.sub))
    if not user:
        raise credentials_exception

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Permisos insuficientes (scope requerido)",
                headers={"WWW-Authenticate": authenticate_value},
            )

    user.token_scopes = token_data.scopes  # type: ignore[attr-defined]
    return user


def get_current_active_user(
    current_user: Annotated[User, Security(get_current_user, scopes=["me"])],
) -> User:
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo",
        )
    return current_user


def get_jira_gateway() -> JiraGateway:
    return JiraClient()


def get_oauth_gateway() -> AtlassianOAuthGateway:
    return AtlassianOAuthClient()


def get_jira_query_service(
    jira: JiraGateway = Depends(get_jira_gateway),
) -> JiraQueryService:
    return JiraQueryService(jira=jira)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def get_kpi_service(db: Session = Depends(get_db)) -> KpiService:
    return KpiService(db)


def get_sync_service(
    db: Session = Depends(get_db),
    jira: JiraGateway = Depends(get_jira_gateway),
) -> SyncService:
    return SyncService(db=db, jira=jira)
