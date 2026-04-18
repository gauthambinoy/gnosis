from fastapi import APIRouter, Depends
from app.core.mood_ring import mood_ring_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/mood", tags=["mood"])


class MoodUpdateRequest(BaseModel):
    success: bool


@router.get("/{agent_id}")
async def get_mood(agent_id: str, user_id: str = Depends(get_current_user_id)):
    mood = mood_ring_engine.get_mood(agent_id)
    return asdict(mood)


@router.post("/{agent_id}/update")
async def update_mood(
    agent_id: str, req: MoodUpdateRequest, user_id: str = Depends(get_current_user_id)
):
    mood = mood_ring_engine.update_mood(agent_id, req.success)
    return asdict(mood)
