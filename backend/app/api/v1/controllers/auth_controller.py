"""Controlador de autenticación (OAuth Atlassian + login local)."""

from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.v1.deps import oauth2_scheme
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.oauth_state import create_oauth_state, verify_oauth_state
from app.core.scopes import SCOPES, scopes_for_role
from app.db.session import get_db
from app.dtos.auth import AuthResponseDTO, LocalLoginRequestDTO, TokenDTO
from app.dtos.common import DataResponseDTO, StatusResponseDTO
from app.services.local_auth_service import LocalAuthError, LocalAuthService
from app.services.oauth_auth_service import OAuthAuthService

logger = logging.getLogger("mchav.auth")


async def oauth_login(request: Request) -> DataResponseDTO[dict]:
    state = create_oauth_state()
    request.session["oauth_state"] = state
    auth_url = OAuthAuthService().build_authorization_url(state)
    return DataResponseDTO(data={"auth_url": auth_url, "available_scopes": SCOPES})


async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if not verify_oauth_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Error de validación CSRF. Vuelve a ejecutar "
                "GET /api/auth/oauth/login y abre el auth_url nuevo."
            ),
        )
    request.session.pop("oauth_state", None)

    try:
        payload = await OAuthAuthService(db).complete_login(code)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("oauth_callback failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de autenticación con Jira: {exc}",
        ) from exc

    if settings.AUTH_RETURN_JSON:
        return DataResponseDTO(data=payload)

    from fastapi.responses import RedirectResponse

    query = urlencode({"token": payload["access_token"]})
    return RedirectResponse(url=f"{settings.CORS_ORIGINS[0]}/auth/callback?{query}")


async def oauth_logout(request: Request) -> StatusResponseDTO:
    request.session.clear()
    return StatusResponseDTO(detail="Sesión OAuth cerrada")


def local_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
) -> TokenDTO:
    username = (form_data.username or "").strip()
    password = form_data.password or ""
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario y contraseña son obligatorios",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = LocalAuthService(db).login(username, password)
    except LocalAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenDTO(
        access_token=payload["access_token"],
        token_type="bearer",
        scopes=payload.get("scopes", []),
        expires_in=payload.get("expires_in"),
    )


def local_login(
    body: LocalLoginRequestDTO,
    db: Session = Depends(get_db),
) -> AuthResponseDTO:
    try:
        return LocalAuthService(db).login(body.username, body.password)
    except LocalAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def local_logout(request: Request) -> StatusResponseDTO:
    request.session.clear()
    return StatusResponseDTO(detail="Sesión local cerrada")


def local_refresh(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> AuthResponseDTO:
    try:
        return LocalAuthService(db).refresh(token)
    except LocalAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def list_scopes() -> DataResponseDTO[dict]:
    return DataResponseDTO(
        data={
            "scopes": SCOPES,
            "role_examples": {
                "Administrador": scopes_for_role("Administrador"),
                "Consultor": scopes_for_role("Consultor"),
            },
            "login_methods": {
                "oauth": {
                    "login": "GET /api/auth/oauth/login",
                    "callback": "GET /api/auth/oauth/callback",
                    "logout": "POST /api/auth/oauth/logout",
                },
                "local": {
                    "token": "POST /api/auth/local/token",
                    "login": "POST /api/auth/local/login",
                    "logout": "POST /api/auth/local/logout",
                    "refresh": "POST /api/auth/local/refresh",
                },
            },
        }
    )
