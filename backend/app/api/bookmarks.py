from fastapi import APIRouter, HTTPException, Depends
from app.core.bookmarks import bookmark_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from typing import Optional

router = APIRouter(prefix="/api/v1/bookmarks", tags=["bookmarks"])


@router.get("")
async def list_bookmarks(
    tag: Optional[str] = None,
    q: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    if q:
        return {"bookmarks": bookmark_engine.search_bookmarks(q)}
    if tag:
        return {"bookmarks": bookmark_engine.list_by_tag(tag)}
    return {"bookmarks": bookmark_engine.list_all()}


@router.post("")
async def create_bookmark(data: dict, user_id: str = Depends(get_current_user_id)):
    bm = bookmark_engine.create(
        user_id=user_id,
        execution_id=data.get("execution_id", ""),
        title=data.get("title", ""),
        note=data.get("note", ""),
        tags=data.get("tags", []),
    )
    return asdict(bm)


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str, user_id: str = Depends(get_current_user_id)
):
    if not bookmark_engine.delete(bookmark_id):
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"status": "deleted"}


@router.get("/tags")
async def list_tags(user_id: str = Depends(get_current_user_id)):
    return {"tags": bookmark_engine.all_tags()}
