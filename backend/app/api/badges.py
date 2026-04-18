from fastapi import APIRouter, HTTPException, Depends
from app.core.skill_badges import skill_badge_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/badges", tags=["badges"])


class AwardRequest(BaseModel):
    agent_id: str
    badge_id: str


@router.get("")
async def list_badges(user_id: str = Depends(get_current_user_id)):
    return {"badges": skill_badge_engine.list_badges()}


@router.get("/agent/{agent_id}")
async def list_agent_badges(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return {"badges": skill_badge_engine.list_agent_badges(agent_id)}


@router.post("/award")
async def award_badge(req: AwardRequest, user_id: str = Depends(get_current_user_id)):
    if not skill_badge_engine.award_badge(req.agent_id, req.badge_id):
        raise HTTPException(
            status_code=400, detail="Badge not found or already awarded"
        )
    return {"status": "awarded", "agent_id": req.agent_id, "badge_id": req.badge_id}
