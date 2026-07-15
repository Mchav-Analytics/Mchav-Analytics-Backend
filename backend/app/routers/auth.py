import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.schemas.common import DataResponse, StatusResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])
logger = logging.getLogger("mchav.auth")


@router.get("/login", response_model=DataResponse[dict])
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    auth_url = auth_service.build_authorization_url(state)
    return DataResponse(data={"auth_url": auth_url})


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    stored_state = request.session.get("oauth_state")
    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Error de validación CSRF")
    request.session.pop("oauth_state", None)

    try:
        token_data = await auth_service.exchange_code_for_token(code)
        atlassian_profile = await auth_service.get_atlassian_user_info(token_data["access_token"])
        email = atlassian_profile.get("email")
        user = auth_service.get_or_validate_local_user(db, email)
        auth_service.save_or_update_oauth_token(db, user, token_data)
        jwt_token = auth_service.create_jwt_token(user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("auth_callback failed")
        raise HTTPException(status_code=502, detail=f"Error de autenticación con Jira: {exc}") from exc

    query = urlencode({"token": jwt_token})
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{query}")


@router.post("/logout", response_model=StatusResponse)
async def logout(request: Request):
    request.session.clear()
    return StatusResponse(detail="Sesión cerrada")
