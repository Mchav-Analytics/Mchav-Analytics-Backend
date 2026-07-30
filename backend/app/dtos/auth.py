"""DTOs de autenticación (JWT, OAuth y login local)."""

from pydantic import BaseModel, Field


class TokenDTO(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    scopes: list[str] = Field(default_factory=list)
    expires_in: int | None = None


class TokenDataDTO(BaseModel):
    """Datos extraídos del JWT para autorización por scopes."""

    sub: str | None = None
    scopes: list[str] = Field(default_factory=list)
    email: str | None = None
    role: str | None = None


class UserPublicDTO(BaseModel):
    id_user: int
    email: str
    full_name: str
    status: str
    role: str


class LocalLoginRequestDTO(BaseModel):
    username: str = Field(..., description="Email del usuario registrado")
    password: str = Field(..., min_length=1)


class AuthResponseDTO(BaseModel):
    """Respuesta unificada de login OAuth y local."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scopes: list[str] = Field(default_factory=list)
    user: UserPublicDTO
