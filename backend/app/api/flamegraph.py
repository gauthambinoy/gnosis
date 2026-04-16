from fastapi import APIRouter, HTTPException, Depends
from app.core.flamegraph import flame_profiler
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/flamegraph", tags=["observability"])

@router.get("/profiles")
async def list_profiles(agent_id: Optional[str] = None, limit: int = 20, user_id: str = Depends(get_current_user_id)):
    return {"profiles": flame_profiler.list_profiles(agent_id=agent_id, limit=limit)}

@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str, user_id: str = Depends(get_current_user_id)):
    profile = flame_profiler.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Flame profile not found")
    return profile
