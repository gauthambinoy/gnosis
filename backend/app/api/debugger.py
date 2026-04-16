from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.time_travel import time_travel_debugger
from app.core.auth import get_current_user_id
from typing import Optional

router = APIRouter(prefix="/api/v1/debugger", tags=["observability"])

@router.get("/sessions")
async def list_debug_sessions(agent_id: Optional[str] = None, limit: int = 20, user_id: str = Depends(get_current_user_id)):
    return {"sessions": time_travel_debugger.list_sessions(agent_id=agent_id, limit=limit)}

@router.get("/sessions/{session_id}")
async def get_debug_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    session = time_travel_debugger.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debug session not found")
    return session

@router.get("/sessions/{session_id}/frames")
async def get_frames(session_id: str, start: int = 0, end: int = -1, user_id: str = Depends(get_current_user_id)):
    return {"frames": time_travel_debugger.get_frames_range(session_id, start=start, end=end)}

@router.get("/sessions/{session_id}/frames/{frame_index}")
async def get_frame(session_id: str, frame_index: int, user_id: str = Depends(get_current_user_id)):
    frame = time_travel_debugger.get_frame(session_id, frame_index)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")
    return frame

@router.get("/sessions/{session_id}/search")
async def search_frames(session_id: str, phase: Optional[str] = None, label: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    return {"frames": time_travel_debugger.search_frames(session_id, phase=phase, label_contains=label)}
