from fastapi import APIRouter, Depends, Query
from app.core.command_registry import command_registry
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/commands", tags=["growth"])

@router.get("")
async def list_commands(category: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"commands": command_registry.list_commands(category=category)}

@router.get("/search")
async def search_commands(q: str = Query(..., min_length=1), user_id: str = Depends(get_current_user_id)):
    return {"results": command_registry.search_commands(q)}
