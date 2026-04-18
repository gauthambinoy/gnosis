from fastapi import APIRouter, Depends
from app.core.feature_flags import feature_flag_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/feature-flags", tags=["growth"])

@router.get("")
async def list_flags(user_id: str = Depends(get_current_user_id)):
    return {"flags": feature_flag_engine.list_flags()}

@router.post("")
async def create_flag(data: dict, user_id: str = Depends(get_current_user_id)):
    return feature_flag_engine.create_flag(name=data["name"], description=data.get("description", ""), scope=data.get("scope", "global"), rollout_pct=data.get("rollout_pct", 100.0))

@router.put("/{flag_id}")
async def update_flag(flag_id: str, data: dict, user_id: str = Depends(get_current_user_id)):
    return feature_flag_engine.update_flag(flag_id, **data)

@router.get("/check/{name}")
async def check_flag(name: str, workspace_id: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"name": name, "enabled": feature_flag_engine.is_enabled(name, user_id=user_id, workspace_id=workspace_id)}
