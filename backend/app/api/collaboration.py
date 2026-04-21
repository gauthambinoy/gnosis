from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from app.core.collaboration import collaboration_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/collaboration", tags=["collaboration"])


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=1000)
    agent_ids: List[str] = Field(min_length=2)
    agent_names: Dict[str, str] = Field(default_factory=dict)
    max_rounds: int = Field(5, ge=1, le=20)


class AddMessageRequest(BaseModel):
    agent_id: str
    content: str = Field(min_length=1, max_length=2000)
    message_type: str = "discussion"
    in_reply_to: Optional[str] = None


class ResolveRequest(BaseModel):
    conclusion: str = Field(min_length=1, max_length=1000)


@router.post("/rooms")
async def create_room(
    req: CreateRoomRequest, user_id: str = Depends(get_current_user_id)
):
    room = collaboration_engine.create_room(
        name=req.name,
        topic=req.topic,
        agent_ids=req.agent_ids,
        agent_names=req.agent_names,
        max_rounds=req.max_rounds,
    )
    return asdict(room)


@router.get("/rooms")
async def list_rooms(
    status: Optional[str] = None, user_id: str = Depends(get_current_user_id)
):
    rooms = collaboration_engine.list_rooms(status=status)
    summaries = [
        {
            "id": r.id,
            "name": r.name,
            "topic": r.topic,
            "agent_count": len(r.agent_ids),
            "message_count": len(r.messages),
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rooms
    ]
    return {"rooms": summaries, "total": len(summaries)}


@router.get("/rooms/{room_id}")
async def get_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = collaboration_engine.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return asdict(room)


@router.post("/rooms/{room_id}/messages")
async def add_message(
    room_id: str,
    req: AddMessageRequest,
    user_id: str = Depends(get_current_user_id),
):
    msg = collaboration_engine.add_message(
        room_id, req.agent_id, req.content, req.message_type, req.in_reply_to
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Room not found")
    return asdict(msg)


@router.post("/rooms/{room_id}/discuss")
async def run_discussion(room_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        room = await collaboration_engine.run_discussion(room_id)
        return asdict(room)
    except ValueError as e:
        safe_http_error(e, "Operation failed", 404)


@router.post("/rooms/{room_id}/resolve")
async def resolve_room(
    room_id: str,
    req: ResolveRequest,
    user_id: str = Depends(get_current_user_id),
):
    room = collaboration_engine.resolve_room(room_id, req.conclusion)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return asdict(room)


@router.post("/rooms/{room_id}/archive")
async def archive_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    if not collaboration_engine.archive_room(room_id):
        raise HTTPException(status_code=404, detail="Room not found")
    return {"archived": True}


@router.get("/stats")
async def collab_stats(user_id: str = Depends(get_current_user_id)):
    return collaboration_engine.stats
