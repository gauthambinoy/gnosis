from fastapi import APIRouter, Depends
from app.core.tutorials import tutorial_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/tutorials", tags=["growth"])

@router.get("")
async def list_tutorials(category: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"tutorials": tutorial_engine.list_tutorials(category=category)}

@router.post("/{tutorial_id}/start")
async def start_tutorial(tutorial_id: str, user_id: str = Depends(get_current_user_id)):
    return tutorial_engine.start_tutorial(user_id, tutorial_id)

@router.post("/{tutorial_id}/advance")
async def advance_step(tutorial_id: str, user_id: str = Depends(get_current_user_id)):
    return tutorial_engine.advance_step(user_id, tutorial_id)

@router.get("/progress")
async def get_progress(user_id: str = Depends(get_current_user_id)):
    return {"progress": tutorial_engine.get_progress(user_id)}
