from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from dataclasses import asdict

from app.core.workspace import workspace_engine, Role
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


# ── Pydantic models ──────────────────────────────────────────────────────────


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    settings: Optional[dict] = None


class InviteMemberRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    role: str = Field(default="editor")


class UpdateRoleRequest(BaseModel):
    role: str


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("")
async def create_workspace(
    body: CreateWorkspaceRequest, user_id: str = Depends(get_current_user_id)
):
    ws = workspace_engine.create(
        name=body.name,
        owner_id=user_id,
        owner_email=f"{user_id}@gnosis.ai",
        description=body.description,
    )
    return {"workspace": asdict(ws)}


@router.get("")
async def list_workspaces(user_id: str = Depends(get_current_user_id)):
    workspaces = workspace_engine.list_user_workspaces(user_id)
    return {"workspaces": [asdict(ws) for ws in workspaces]}


@router.get("/stats")
async def workspace_stats(user_id: str = Depends(get_current_user_id)):
    return workspace_engine.stats


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    ws = workspace_engine.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"workspace": asdict(ws)}


@router.patch("/{workspace_id}")
async def update_workspace(workspace_id: str, body: UpdateWorkspaceRequest, user_id: str = Depends(get_current_user_id)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ws = workspace_engine.update(workspace_id, **updates)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"workspace": asdict(ws)}


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    if not workspace_engine.delete(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"deleted": True}


@router.post("/{workspace_id}/invite")
async def invite_member(
    workspace_id: str,
    body: InviteMemberRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    invite = workspace_engine.invite_member(
        workspace_id, body.email, role, invited_by=user_id
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"invite": asdict(invite)}


@router.post("/invites/{invite_id}/accept")
async def accept_invite(invite_id: str, user_id: str = Depends(get_current_user_id)):
    ws = workspace_engine.accept_invite(invite_id, user_id=user_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Invite not found or already used")
    return {"workspace": asdict(ws)}


@router.delete("/{workspace_id}/members/{member_user_id}")
async def remove_member(workspace_id: str, member_user_id: str, user_id: str = Depends(get_current_user_id)):
    if not workspace_engine.remove_member(workspace_id, member_user_id):
        raise HTTPException(status_code=404, detail="Workspace or member not found")
    return {"removed": True}


@router.patch("/{workspace_id}/members/{member_user_id}/role")
async def update_member_role(
    workspace_id: str,
    member_user_id: str,
    body: UpdateRoleRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    if not workspace_engine.update_member_role(workspace_id, member_user_id, role):
        raise HTTPException(status_code=404, detail="Workspace or member not found")
    return {"updated": True}


@router.get("/{workspace_id}/members")
async def list_members(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    ws = workspace_engine.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"members": [asdict(m) for m in ws.members]}
