from pydantic import BaseModel, Field
from typing import Optional


class MemoryCreate(BaseModel):
    tier: str = Field(..., min_length=1, description="Memory tier: sensory, short_term, long_term, correction")
    content: str = Field(..., min_length=1, description="Memory content")
    metadata: dict = Field(default_factory=dict)


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)


class MemoryResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    agent_id: str
    tier: str
    content: str
    relevance_score: float = 1.0
    access_count: int = 0
    strength: float = 1.0
    created_at: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    last_accessed: Optional[str] = None


class MemoryListResponse(BaseModel):
    agent_id: str
    memories: list[MemoryResponse]
    total: int
    tier: Optional[str] = None
    stats: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    agent_id: str
    query: str
    results: list[MemoryResponse]
    total: int


class StoreResponse(BaseModel):
    status: str
    memory: MemoryResponse


class MemoryStatsResponse(BaseModel):
    model_config = {"extra": "allow"}

    vectors: dict = Field(default_factory=dict)
    sensory_buffer: int = 0
    embeddings: dict = Field(default_factory=dict)
