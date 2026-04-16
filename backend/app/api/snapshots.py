"""Agent state snapshots API."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.state_snapshots import state_snapshot_engine
from dataclasses import asdict

router = APIRouter()


@router.post("/{agent_id}/capture")
async def capture_snapshot(agent_id: str, body: dict = None, user_id: str = Depends(get_current_user_id)):
    body = body or {}
    snap = state_snapshot_engine.capture_snapshot(
        agent_id,
        state=body.get("state"),
        config=body.get("config"),
        description=body.get("description", ""),
    )
    return asdict(snap)


@router.post("/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, user_id: str = Depends(get_current_user_id)):
    result = state_snapshot_engine.restore_snapshot(snapshot_id)
    if not result:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return result


@router.get("/{agent_id}")
async def list_snapshots(agent_id: str, user_id: str = Depends(get_current_user_id)):
    snaps = state_snapshot_engine.list_snapshots(agent_id)
    return {"snapshots": [asdict(s) for s in snaps]}


@router.get("/diff")
async def diff_snapshots(id_a: str, id_b: str, user_id: str = Depends(get_current_user_id)):
    result = state_snapshot_engine.diff_snapshots(id_a, id_b)
    if not result:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")
    return result
