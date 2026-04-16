from fastapi import APIRouter, HTTPException, Depends
from app.core.retention_engine import retention_engine
from app.core.auth import get_current_user_id
from dataclasses import asdict

router = APIRouter(prefix="/api/v1/retention", tags=["compliance"])

@router.get("/{workspace_id}")
async def get_policy(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    return asdict(retention_engine.get_policy(workspace_id))

@router.post("/{workspace_id}")
async def set_policy(workspace_id: str, data: dict, user_id: str = Depends(get_current_user_id)):
    policy = retention_engine.set_policy(workspace_id, **data)
    return asdict(policy)

@router.get("/{workspace_id}/simulate")
async def simulate_purge(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    return retention_engine.simulate_purge(workspace_id)

@router.get("")
async def list_policies(user_id: str = Depends(get_current_user_id)):
    return {"policies": retention_engine.list_policies()}

@router.get("/{workspace_id}/history")
async def purge_history(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    return {"history": retention_engine.get_purge_history(workspace_id)}
