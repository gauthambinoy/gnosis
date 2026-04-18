from fastapi import APIRouter, Depends
from app.core.emotion_engine import emotion_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/emotions", tags=["emotions"])


class AnalyzeRequest(BaseModel):
    text: str
    agent_id: str = ""


@router.post("/analyze")
async def analyze_emotion(
    req: AnalyzeRequest, user_id: str = Depends(get_current_user_id)
):
    from dataclasses import asdict

    signal = emotion_engine.analyze_text(req.text, req.agent_id)
    return asdict(signal)


@router.get("/history/{agent_id}")
async def get_emotion_history(
    agent_id: str, limit: int = 50, user_id: str = Depends(get_current_user_id)
):
    return {"history": emotion_engine.get_emotion_history(agent_id, limit)}
