from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from app.core.llm_gateway import llm_gateway, LLMRequest

router = APIRouter()


class AwakenRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/chat")
async def awaken_chat(data: AwakenRequest):
    """Conversational agent creation via streaming SSE — powered by LLM Gateway."""

    async def stream():
        request = LLMRequest(
            prompt=data.message,
            system_prompt=(
                "You are Gnosis, an intelligent AI agent builder. "
                "Help the user design and create AI agents. Be concise, "
                "helpful, and suggest specific agent configurations when appropriate."
            ),
            model="fast",
            max_tokens=1024,
            temperature=0.7,
        )

        try:
            response = await llm_gateway.complete(request)
            content = response.content

            # Stream in small chunks for responsive SSE without artificial delay
            chunk_size = 8
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'meta', 'model': response.model, 'provider': response.provider, 'tokens': response.tokens_used, 'latency_ms': round(response.latency_ms, 1)})}\n\n"
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            for char in error_msg:
                yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
