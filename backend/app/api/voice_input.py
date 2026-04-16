from fastapi import APIRouter, Depends
from app.core.voice_input import voice_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe(data: dict, user_id: str = Depends(get_current_user_id)):
    cmd = voice_engine.parse_intent(
        transcript=data.get("transcript", ""),
        user_id=user_id,
        confidence=data.get("confidence", 1.0),
    )
    return asdict(cmd)


@router.get("/history")
async def voice_history(user_id: str = Depends(get_current_user_id)):
    return {"commands": voice_engine.history(user_id)}
