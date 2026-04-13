from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

router = APIRouter()


class AwakenRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/chat")
async def awaken_chat(data: AwakenRequest):
    """Conversational agent creation via streaming SSE."""

    async def stream():
        # Placeholder — will be powered by LLM Gateway in Phase 2
        response = f"I understand you need help with: '{data.message}'. Let me design an agent for this..."
        for char in response:
            yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"
            await asyncio.sleep(0.02)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
