from fastapi import APIRouter, HTTPException, Depends
from app.core.collab_editor import collab_editor
from app.core.auth import get_current_user_id
from dataclasses import asdict
from app.core.safe_error import safe_http_error

router = APIRouter(prefix="/api/v1/collab-edit", tags=["collab-edit"])


@router.post("/start")
async def start_session(data: dict, user_id: str = Depends(get_current_user_id)):
    session = collab_editor.start_session(
        agent_id=data.get("agent_id", ""),
        user_id=user_id,
    )
    return asdict(session)


@router.post("/{session_id}/change")
async def apply_change(
    session_id: str, data: dict, user_id: str = Depends(get_current_user_id)
):
    try:
        session = collab_editor.apply_change(
            session_id=session_id,
            field_name=data.get("field", ""),
            old_value=data.get("old", ""),
            new_value=data.get("new", ""),
        )
        return asdict(session)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except ValueError as e:
        safe_http_error(e, "Operation failed", 400)


@router.get("/agent/{agent_id}")
async def list_sessions(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return {"sessions": collab_editor.list_sessions(agent_id)}
