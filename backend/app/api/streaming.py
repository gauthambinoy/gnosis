from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.core.llm_streamer import llm_streamer
from app.core.auth import get_current_user_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])

class StreamRequest(BaseModel):
    prompt: str
    model: str = "openai/gpt-4o-mini"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    provider: str = "openrouter"

@router.post("/completion")
async def stream_completion(req: StreamRequest, user_id: str = Depends(get_current_user_id)):
    return StreamingResponse(
        llm_streamer.stream_completion(
            prompt=req.prompt,
            model=req.model,
            system_prompt=req.system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            provider=req.provider,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

@router.get("/metrics")
async def stream_metrics(user_id: str = Depends(get_current_user_id)):
    return llm_streamer.metrics
