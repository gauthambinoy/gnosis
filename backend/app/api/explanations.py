from fastapi import APIRouter, HTTPException, Depends
from app.core.explanation_engine import explanation_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/explanations", tags=["explanations"])


@router.get("/{execution_id}")
async def get_explanation(
    execution_id: str, user_id: str = Depends(get_current_user_id)
):
    results = explanation_engine.get_explanation(execution_id)
    if not results:
        raise HTTPException(status_code=404, detail="No explanation found")
    return {"explanations": results}


@router.post("/generate")
async def generate_explanation(data: dict, user_id: str = Depends(get_current_user_id)):
    explanation = explanation_engine.generate_explanation(
        execution_id=data.get("execution_id", ""),
        response_text=data.get("response_text", ""),
    )
    return asdict(explanation)
