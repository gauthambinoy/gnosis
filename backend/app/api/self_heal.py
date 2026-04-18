from fastapi import APIRouter, Depends
from app.core.self_healer import self_healer_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/self-heal", tags=["self-heal"])


class MatchRequest(BaseModel):
    error_msg: str


class PatternCreate(BaseModel):
    pattern: str
    fix_description: str
    auto_fixable: bool = False
    category: str = "general"


@router.get("/patterns")
async def list_patterns(user_id: str = Depends(get_current_user_id)):
    return {"patterns": self_healer_engine.list_patterns()}


@router.post("/match")
async def match_error(req: MatchRequest, user_id: str = Depends(get_current_user_id)):
    matches = self_healer_engine.match_error(req.error_msg)
    return {"error_msg": req.error_msg, "matches": matches, "match_count": len(matches)}


@router.post("/patterns")
async def create_pattern(req: PatternCreate, user_id: str = Depends(get_current_user_id)):
    try:
        from dataclasses import asdict
        pattern = self_healer_engine.register_pattern(req.pattern, req.fix_description,
                                                       req.auto_fixable, req.category)
        return asdict(pattern)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)
