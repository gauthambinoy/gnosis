from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional
from app.core.auth import get_current_user_id
from app.core.knowledge_graph import knowledge_graph_engine
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["knowledge-graph"])


class AddEntityRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    entity_type: str = Field(min_length=1)
    agent_id: Optional[str] = None
    properties: dict = Field(default_factory=dict)


class AddRelationRequest(BaseModel):
    source_name: str
    target_name: str
    relation_type: str
    context: str = ""


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    agent_id: Optional[str] = None


@router.post("/entities")
async def add_entity(req: AddEntityRequest, user_id: str = Depends(get_current_user_id)):
    entity = knowledge_graph_engine.add_entity(
        req.name, req.entity_type, req.agent_id, req.properties
    )
    return asdict(entity)


@router.post("/relationships")
async def add_relationship(req: AddRelationRequest, user_id: str = Depends(get_current_user_id)):
    rel = knowledge_graph_engine.add_relationship(
        req.source_name, req.target_name, req.relation_type, req.context
    )
    if not rel:
        raise HTTPException(status_code=400, detail="Source or target entity not found")
    return asdict(rel)


@router.post("/extract")
async def extract_from_text(req: ExtractRequest, user_id: str = Depends(get_current_user_id)):
    result = knowledge_graph_engine.extract_from_text(req.text, req.agent_id)
    return result


@router.get("/graph")
async def get_graph(agent_id: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return knowledge_graph_engine.get_graph(agent_id)


@router.get("/entities/search")
async def search_entities(query: str, entity_type: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    results = knowledge_graph_engine.search_entities(query, entity_type)
    return {"entities": [asdict(e) for e in results[:50]], "total": len(results)}


@router.get("/entities/{entity_name}/neighborhood")
async def entity_neighborhood(entity_name: str, depth: int = Query(1, ge=1, le=3), user_id: str = Depends(get_current_user_id)):
    return knowledge_graph_engine.get_entity_neighborhood(entity_name, depth)


@router.get("/stats")
async def kg_stats(user_id: str = Depends(get_current_user_id)):
    return knowledge_graph_engine.stats
