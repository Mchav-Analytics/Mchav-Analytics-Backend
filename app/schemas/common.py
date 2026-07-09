from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StatusResponse(BaseModel):
    status: str = "success"
    detail: str | None = None


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str


class DataResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T


class PaginatedMeta(BaseModel):
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)


class PaginatedResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: list[T]
    meta: PaginatedMeta
