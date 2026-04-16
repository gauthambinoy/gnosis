from fastapi import APIRouter, HTTPException, Depends
from app.core.voice_profiles import voice_profile_engine, VoiceProfile
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional, List

router = APIRouter(prefix="/api/v1/voice-profiles", tags=["voice-profiles"])


@router.get("")
async def list_profiles(user_id: str = Depends(get_current_user_id)):
    return {"profiles": voice_profile_engine.list_profiles()}


@router.post("")
async def create_profile(name: str, tone: str = "friendly", vocabulary_level: str = "intermediate",
                         response_style: str = "balanced", example_phrases: List[str] = None,
                         user_id: str = Depends(get_current_user_id)):
    try:
        profile = voice_profile_engine.create_profile(name, tone, vocabulary_level, response_style, example_phrases)
        return asdict(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{profile_id}")
async def get_profile(profile_id: str, user_id: str = Depends(get_current_user_id)):
    profile = voice_profile_engine.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return asdict(profile)


@router.post("/{profile_id}/assign/{agent_id}")
async def assign_to_agent(profile_id: str, agent_id: str, user_id: str = Depends(get_current_user_id)):
    if not voice_profile_engine.assign_to_agent(profile_id, agent_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "assigned", "profile_id": profile_id, "agent_id": agent_id}
