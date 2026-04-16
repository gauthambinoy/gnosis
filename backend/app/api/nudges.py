from fastapi import APIRouter, Depends
from app.core.upgrade_nudges import nudge_engine
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/nudges", tags=["growth"])

@router.get("")
async def get_nudges(user_id: str = Depends(get_current_user_id)):
    return {"nudges": nudge_engine.evaluate_nudges(user_id)}

@router.post("/{nudge_id}/dismiss")
async def dismiss_nudge(nudge_id: str, user_id: str = Depends(get_current_user_id)):
    nudge_engine.dismiss_nudge(user_id, nudge_id)
    return {"dismissed": True}
