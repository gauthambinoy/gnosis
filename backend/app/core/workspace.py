"""Gnosis Workspaces — Multi-user organizations with role-based access."""
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger("gnosis.workspace")


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


ROLE_PERMISSIONS = {
    Role.OWNER: {"read", "write", "delete", "manage_members", "manage_workspace", "billing"},
    Role.ADMIN: {"read", "write", "delete", "manage_members"},
    Role.EDITOR: {"read", "write"},
    Role.VIEWER: {"read"},
}


@dataclass
class WorkspaceMember:
    user_id: str
    email: str
    role: Role
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    invited_by: Optional[str] = None


@dataclass
class WorkspaceInvite:
    id: str
    workspace_id: str
    email: str
    role: Role
    status: str = "pending"  # pending, accepted, expired
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None


@dataclass
class Workspace:
    id: str
    name: str
    slug: str
    description: str = ""
    owner_id: str = ""
    members: List[WorkspaceMember] = field(default_factory=list)
    agent_ids: List[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkspaceEngine:
    def __init__(self):
        self._workspaces: Dict[str, Workspace] = {}
        self._user_workspaces: Dict[str, List[str]] = {}  # user_id -> workspace_ids
        self._invites: Dict[str, WorkspaceInvite] = {}

    def create(self, name: str, owner_id: str, owner_email: str, description: str = "") -> Workspace:
        slug = name.lower().replace(" ", "-")[:50]
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name=name, slug=slug, description=description,
            owner_id=owner_id,
            members=[WorkspaceMember(user_id=owner_id, email=owner_email, role=Role.OWNER)],
        )
        self._workspaces[workspace.id] = workspace
        self._user_workspaces.setdefault(owner_id, []).append(workspace.id)
        logger.info(f"Workspace created: {workspace.id} by {owner_id}")
        return workspace

    def get(self, workspace_id: str) -> Optional[Workspace]:
        return self._workspaces.get(workspace_id)

    def list_user_workspaces(self, user_id: str) -> List[Workspace]:
        ws_ids = self._user_workspaces.get(user_id, [])
        return [self._workspaces[wid] for wid in ws_ids if wid in self._workspaces]

    def update(self, workspace_id: str, **kwargs) -> Optional[Workspace]:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return None
        for k, v in kwargs.items():
            if hasattr(ws, k) and k not in ('id', 'created_at', 'owner_id'):
                setattr(ws, k, v)
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        return ws

    def delete(self, workspace_id: str) -> bool:
        ws = self._workspaces.pop(workspace_id, None)
        if ws:
            for member in ws.members:
                if workspace_id in self._user_workspaces.get(member.user_id, []):
                    self._user_workspaces[member.user_id].remove(workspace_id)
            return True
        return False

    def invite_member(self, workspace_id: str, email: str, role: Role, invited_by: str) -> Optional[WorkspaceInvite]:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return None
        invite = WorkspaceInvite(
            id=str(uuid.uuid4()), workspace_id=workspace_id,
            email=email, role=role,
        )
        self._invites[invite.id] = invite
        return invite

    def accept_invite(self, invite_id: str, user_id: str) -> Optional[Workspace]:
        invite = self._invites.get(invite_id)
        if not invite or invite.status != "pending":
            return None

        ws = self._workspaces.get(invite.workspace_id)
        if not ws:
            return None

        member = WorkspaceMember(user_id=user_id, email=invite.email, role=invite.role)
        ws.members.append(member)
        self._user_workspaces.setdefault(user_id, []).append(ws.id)
        invite.status = "accepted"
        return ws

    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False
        ws.members = [m for m in ws.members if m.user_id != user_id]
        if workspace_id in self._user_workspaces.get(user_id, []):
            self._user_workspaces[user_id].remove(workspace_id)
        return True

    def update_member_role(self, workspace_id: str, user_id: str, new_role: Role) -> bool:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False
        for member in ws.members:
            if member.user_id == user_id:
                member.role = new_role
                return True
        return False

    def check_permission(self, workspace_id: str, user_id: str, permission: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False
        for member in ws.members:
            if member.user_id == user_id:
                return permission in ROLE_PERMISSIONS.get(member.role, set())
        return False

    def get_member_role(self, workspace_id: str, user_id: str) -> Optional[Role]:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return None
        for member in ws.members:
            if member.user_id == user_id:
                return member.role
        return None

    @property
    def stats(self) -> dict:
        total_members = sum(len(ws.members) for ws in self._workspaces.values())
        return {"total_workspaces": len(self._workspaces), "total_members": total_members}


workspace_engine = WorkspaceEngine()
