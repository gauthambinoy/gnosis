from fastapi import APIRouter, Depends
from app.core.query_analyzer import query_analyzer
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/query-analyzer", tags=["performance"])

@router.get("/summary")
async def get_summary(user_id: str = Depends(get_current_user_id)):
    return query_analyzer.get_summary()

@router.get("/slow")
async def get_slow_queries(threshold_ms: Optional[float] = None, limit: int = 20, user_id: str = Depends(get_current_user_id)):
    return {"queries": query_analyzer.get_slow_queries(threshold_ms=threshold_ms, limit=limit)}

@router.get("/patterns")
async def get_top_patterns(by: str = "total_ms", limit: int = 20, user_id: str = Depends(get_current_user_id)):
    return {"patterns": query_analyzer.get_top_patterns(by=by, limit=limit)}

@router.post("/reset")
async def reset_analyzer(user_id: str = Depends(get_current_user_id)):
    query_analyzer.reset()
    return {"status": "reset"}
