"""Gnosis Delegated Agent Permissions — API routes."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.agent_permissions import agent_permission_engine

router = APIRouter(prefix="/api/v1/agent-permissions", tags=["agent-permissions"])


class GrantPermissionRequest(BaseModel):
    agent_id: str
    user_id: str
    role: str


class RevokePermissionRequest(BaseModel):
    permission_id: str


@router.post("/grant")
async def grant_permission(body: GrantPermissionRequest, user_id: str = Depends(get_current_user_id)):
    try:
        perm = agent_permission_engine.grant_permission(
            agent_id=body.agent_id,
            user_id=body.user_id,
            role=body.role,
            granted_by=user_id,
        )
        return asdict(perm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/revoke")
async def revoke_permission(body: RevokePermissionRequest):
    try:
        agent_permission_engine.revoke_permission(body.permission_id)
        return {"status": "revoked"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_id}")
async def list_permissions(agent_id: str):
    perms = agent_permission_engine.list_permissions(agent_id)
    return [asdict(p) for p in perms]


@router.get("/{agent_id}/check")
async def check_permission(agent_id: str, user_id: str = Query(...), action: str = Query(...)):
    try:
        allowed = agent_permission_engine.check_permission(agent_id, user_id, action)
        return {"allowed": allowed}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
