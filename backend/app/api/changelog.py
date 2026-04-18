from fastapi import APIRouter, Depends
from app.core.changelog import changelog_engine
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/changelog", tags=["growth"])


@router.get("")
async def list_changelog(
    limit: int = 20,
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    return {"entries": changelog_engine.list_entries(limit=limit, category=category)}


@router.get("/latest")
async def latest_version(user_id: str = Depends(get_current_user_id)):
    return {"version": changelog_engine.get_latest_version()}


@router.post("")
async def add_entry(data: dict, user_id: str = Depends(get_current_user_id)):
    return changelog_engine.add_entry(
        version=data["version"],
        title=data["title"],
        description=data.get("description", ""),
        category=data.get("category", "feature"),
        tags=data.get("tags", []),
    )
