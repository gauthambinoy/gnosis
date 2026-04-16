from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.help_system import help_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/help", tags=["growth"])

@router.get("/tips")
async def list_tips(category: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"tips": help_engine.list_tips(category=category)}

@router.get("/tips/{element_id}")
async def get_tip(element_id: str, user_id: str = Depends(get_current_user_id)):
    tip = help_engine.get_tip(element_id)
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    return tip

@router.get("/search")
async def search_tips(q: str = Query(..., min_length=1), user_id: str = Depends(get_current_user_id)):
    return {"results": help_engine.search_tips(q)}
