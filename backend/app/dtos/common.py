"""DTOs de envelope / respuestas comunes."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StatusResponseDTO(BaseModel):
    status: str = "success"
    detail: str | None = None


class ErrorResponseDTO(BaseModel):
    status: str = "error"
    detail: str


class DataResponseDTO(BaseModel, Generic[T]):
    status: str = "success"
    data: T


class PaginatedMetaDTO(BaseModel):
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class PaginatedResponseDTO(BaseModel, Generic[T]):
    status: str = "success"
    data: list[T]
    meta: PaginatedMetaDTO
