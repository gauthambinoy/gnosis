from fastapi import APIRouter, Depends
from app.core.quality_scorer import quality_scorer_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


class ScoreRequest(BaseModel):
    prompt: str
    response: str
    execution_id: str = ""
    agent_id: str = ""


@router.post("/score")
async def score_response(
    req: ScoreRequest, user_id: str = Depends(get_current_user_id)
):
    score = quality_scorer_engine.score_response(
        req.prompt, req.response, req.execution_id, req.agent_id
    )
    return asdict(score)


@router.get("/history/{agent_id}")
async def get_quality_history(
    agent_id: str, limit: int = 50, user_id: str = Depends(get_current_user_id)
):
    return {"history": quality_scorer_engine.get_history(agent_id, limit)}
