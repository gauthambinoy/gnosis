from fastapi import APIRouter, Depends
from app.core.prompt_compressor import prompt_compressor_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/prompt", tags=["prompt-compression"])


class CompressRequest(BaseModel):
    text: str
    max_tokens: int = 0


class EstimateRequest(BaseModel):
    text: str


@router.post("/compress")
async def compress_prompt(req: CompressRequest, user_id: str = Depends(get_current_user_id)):
    return prompt_compressor_engine.compress(req.text, req.max_tokens)


@router.post("/estimate-tokens")
async def estimate_tokens(req: EstimateRequest, user_id: str = Depends(get_current_user_id)):
    tokens = prompt_compressor_engine.estimate_tokens(req.text)
    return {"text_length": len(req.text), "estimated_tokens": tokens}
