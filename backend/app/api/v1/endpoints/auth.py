"""Rutas de autenticación (OAuth + local + legacy)."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.controllers import auth_controller
from app.db.session import get_db
from app.dtos.auth import AuthResponseDTO, TokenDTO
from app.dtos.common import DataResponseDTO, StatusResponseDTO

oauth_router = APIRouter(prefix="/auth/oauth", tags=["Auth OAuth"])
local_router = APIRouter(prefix="/auth/local", tags=["Auth Local"])
router = APIRouter(prefix="/auth", tags=["Auth"])

oauth_router.add_api_route(
    "/login",
    auth_controller.oauth_login,
    methods=["GET"],
    response_model=DataResponseDTO[dict],
    summary="Iniciar login OAuth (Jira/Atlassian)",
)
oauth_router.add_api_route(
    "/callback",
    auth_controller.oauth_callback,
    methods=["GET"],
    summary="Callback OAuth (Jira/Atlassian)",
)
oauth_router.add_api_route(
    "/logout",
    auth_controller.oauth_logout,
    methods=["POST"],
    response_model=StatusResponseDTO,
    summary="Cerrar sesión OAuth",
)

local_router.add_api_route(
    "/token",
    auth_controller.local_token,
    methods=["POST"],
    response_model=TokenDTO,
    summary="Login OAuth2 password (Swagger Authorize)",
)
local_router.add_api_route(
    "/login",
    auth_controller.local_login,
    methods=["POST"],
    response_model=AuthResponseDTO,
    summary="Login local (JSON)",
)
local_router.add_api_route(
    "/logout",
    auth_controller.local_logout,
    methods=["POST"],
    response_model=StatusResponseDTO,
    summary="Cerrar sesión local",
)
local_router.add_api_route(
    "/refresh",
    auth_controller.local_refresh,
    methods=["POST"],
    response_model=AuthResponseDTO,
    summary="Refrescar JWT local",
)

router.add_api_route(
    "/scopes",
    auth_controller.list_scopes,
    methods=["GET"],
    response_model=DataResponseDTO[dict],
    summary="Listar scopes OAuth2 de la API",
)


@router.get("/login", include_in_schema=False)
async def legacy_oauth_login(request: Request):
    return await auth_controller.oauth_login(request)


@router.get("/callback", include_in_schema=False)
async def legacy_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    return await auth_controller.oauth_callback(
        request, code=code, state=state, db=db
    )


@router.post("/logout", include_in_schema=False, response_model=StatusResponseDTO)
async def legacy_logout(request: Request):
    return await auth_controller.oauth_logout(request)
