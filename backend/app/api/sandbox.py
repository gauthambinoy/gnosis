from fastapi import APIRouter, HTTPException, Depends
from app.core.sandbox import sandbox_engine
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/sandbox", tags=["growth"])

@router.post("/create")
async def create_sandbox(ttl_minutes: int = 30, user_id: str = Depends(get_current_user_id)):
    return sandbox_engine.create_session(user_id, ttl_minutes)

@router.post("/{session_id}/execute")
async def execute_in_sandbox(session_id: str, action: dict, user_id: str = Depends(get_current_user_id)):
    result = sandbox_engine.execute_in_sandbox(session_id, action)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/{session_id}")
async def get_sandbox(session_id: str, user_id: str = Depends(get_current_user_id)):
    result = sandbox_engine.get_session(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.delete("/{session_id}")
async def destroy_sandbox(session_id: str, user_id: str = Depends(get_current_user_id)):
    if not sandbox_engine.destroy_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}
