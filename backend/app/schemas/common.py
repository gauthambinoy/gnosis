from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    detail: dict = {}


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
