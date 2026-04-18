from pydantic import BaseModel, Field
from typing import TypeVar, Optional

T = TypeVar("T")


class ErrorResponse(BaseModel):
    error: str
    detail: dict = {}


class SuccessResponse(BaseModel):
    status: str
    id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Generic paginated response base."""

    total: int
    page: int = 1
    per_page: int = 20
