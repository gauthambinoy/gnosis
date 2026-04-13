from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from app.core.prompt_optimizer import prompt_optimizer
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class OptimizeRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    agent_id: Optional[str] = None


@router.post("/optimize")
async def optimize_prompt(req: OptimizeRequest):
    result = prompt_optimizer.optimize(req.prompt, agent_id=req.agent_id)
    return asdict(result)


@router.get("/history/{agent_id}")
async def prompt_history(agent_id: str):
    history = prompt_optimizer.get_history(agent_id)
    return {"history": history, "total": len(history)}


@router.get("/stats")
async def prompt_stats():
    return prompt_optimizer.stats
