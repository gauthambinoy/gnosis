from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: str
    agent_id: str
    tier: str
    content: str
    relevance_score: float
    access_count: int
    strength: float
    created_at: str
    metadata: dict = {}


class SearchResponse(BaseModel):
    results: list[MemoryResponse]
    total: int
    query: str


class StoreResponse(BaseModel):
    status: str
    memory: MemoryResponse


class MemoryStatsResponse(BaseModel):
    vectors: dict
    sensory_buffer: int
    embeddings: dict
