from fastapi import APIRouter, Depends
from app.core.user_preferences import user_preferences_engine
from app.core.auth import get_current_user_id
from pydantic import BaseModel
from dataclasses import asdict
from typing import Optional
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


class PreferencesUpdate(BaseModel):
    preferred_language: Optional[str] = None
    response_length: Optional[str] = None
    code_style: Optional[str] = None
    timezone: Optional[str] = None
    notifications_enabled: Optional[bool] = None


@router.get("")
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    prefs = user_preferences_engine.get_preferences(user_id)
    return asdict(prefs)


@router.put("")
async def update_preferences(req: PreferencesUpdate, user_id: str = Depends(get_current_user_id)):
    updates = {k: v for k, v in req.dict().items() if v is not None}
    try:
        prefs = user_preferences_engine.set_preferences(user_id, **updates)
        return asdict(prefs)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)
