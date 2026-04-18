from fastapi import APIRouter, HTTPException, Depends
from app.core.comment_threads import comment_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/comments", tags=["comments"])


@router.get("/{execution_id}")
async def list_comments(execution_id: str, user_id: str = Depends(get_current_user_id)):
    return {"comments": comment_engine.list_thread(execution_id)}


@router.post("/{execution_id}")
async def add_comment(
    execution_id: str, data: dict, user_id: str = Depends(get_current_user_id)
):
    comment = comment_engine.add_comment(
        execution_id=execution_id,
        user_id=user_id,
        text=data.get("text", ""),
    )
    return asdict(comment)


@router.post("/{comment_id}/reply")
async def reply_to_comment(
    comment_id: str, data: dict, user_id: str = Depends(get_current_user_id)
):
    try:
        comment = comment_engine.reply(
            parent_id=comment_id,
            user_id=user_id,
            text=data.get("text", ""),
        )
        return asdict(comment)
    except KeyError:
        raise HTTPException(status_code=404, detail="Parent comment not found")


@router.post("/{comment_id}/react")
async def add_reaction(
    comment_id: str, data: dict, user_id: str = Depends(get_current_user_id)
):
    try:
        comment = comment_engine.add_reaction(
            comment_id=comment_id,
            emoji=data.get("emoji", "👍"),
            user_id=user_id,
        )
        return asdict(comment)
    except KeyError:
        raise HTTPException(status_code=404, detail="Comment not found")
