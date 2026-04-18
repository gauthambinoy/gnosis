from fastapi import APIRouter, HTTPException, Depends
from app.core.config_snapshots import config_snapshot_store
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/config-snapshots", tags=["config-snapshots"])


@router.post("/{agent_id}")
async def create_snapshot(
    agent_id: str,
    config: dict,
    description: str = "",
    user_id: str = Depends(get_current_user_id),
):
    snapshot = config_snapshot_store.create_snapshot(
        agent_id, config, created_by=user_id, description=description
    )
    return asdict(snapshot)


@router.get("/{agent_id}/versions")
async def list_versions(agent_id: str, user_id: str = Depends(get_current_user_id)):
    versions = config_snapshot_store.list_versions(agent_id)
    return {"agent_id": agent_id, "versions": [asdict(v) for v in versions]}


@router.get("/{agent_id}/active")
async def get_active(agent_id: str, user_id: str = Depends(get_current_user_id)):
    snapshot = config_snapshot_store.get_active(agent_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No active config snapshot")
    return asdict(snapshot)


@router.post("/activate/{snapshot_id}")
async def activate_snapshot(
    snapshot_id: str, user_id: str = Depends(get_current_user_id)
):
    if not config_snapshot_store.activate(snapshot_id):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"status": "activated", "snapshot_id": snapshot_id}


@router.get("/diff")
async def diff_snapshots(a: str, b: str, user_id: str = Depends(get_current_user_id)):
    result = config_snapshot_store.diff(a, b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
