"""Ollama local LLM bridge API."""

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.ollama_bridge import ollama_bridge

router = APIRouter()


@router.get("/status")
async def ollama_status(user_id: str = Depends(get_current_user_id)):
    available = await ollama_bridge.check_available()
    status = ollama_bridge.get_status()
    status["available"] = available
    return status


@router.get("/models")
async def ollama_models(user_id: str = Depends(get_current_user_id)):
    models = await ollama_bridge.list_models()
    return {"models": models}


@router.post("/generate")
async def ollama_generate(body: dict, user_id: str = Depends(get_current_user_id)):
    prompt = body.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    model = body.get("model")
    result = await ollama_bridge.generate(prompt, model)
    return {"response": result, "model": model or ollama_bridge.config.model}
