from fastapi import APIRouter, HTTPException, Depends
from app.core.waterfall import waterfall_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict
from typing import Optional

router = APIRouter(prefix="/api/v1/waterfall", tags=["waterfall"])


class SpanRequest(BaseModel):
    execution_id: str
    name: str
    parent_id: Optional[str] = None


class EndSpanRequest(BaseModel):
    span_id: str


@router.get("/{execution_id}")
async def get_waterfall(execution_id: str, user_id: str = Depends(get_current_user_id)):
    spans = waterfall_engine.get_waterfall(execution_id)
    return {"execution_id": execution_id, "spans": spans}


@router.post("/span")
async def create_span(req: SpanRequest, user_id: str = Depends(get_current_user_id)):
    span = waterfall_engine.start_span(req.execution_id, req.name, req.parent_id)
    return asdict(span)


@router.post("/span/end")
async def end_span(req: EndSpanRequest, user_id: str = Depends(get_current_user_id)):
    span = waterfall_engine.end_span(req.span_id)
    if not span:
        raise HTTPException(status_code=404, detail="Span not found")
    return asdict(span)
