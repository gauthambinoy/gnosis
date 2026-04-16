"""Gnosis Delegated Agent Permissions — Role-based access control for agents."""
import uuid, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.agent_permissions")

ROLE_HIERARCHY = {"viewer": 0, "operator": 1, "editor": 2, "admin": 3}
ACTION_REQUIREMENTS = {"view": "viewer", "execute": "operator", "edit": "editor", "manage": "admin"}


@dataclass
class AgentPermission:
    id: str
    agent_id: str
    user_id: str
    role: str
    granted_by: str
    granted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentPermissionEngine:
    def __init__(self):
        self._permissions: Dict[str, AgentPermission] = {}

    def grant_permission(self, agent_id: str, user_id: str, role: str, granted_by: str) -> AgentPermission:
        if role not in ROLE_HIERARCHY:
            raise ValueError(f"Invalid role. Must be one of {list(ROLE_HIERARCHY.keys())}")
        # Replace existing permission for same agent+user
        for pid, perm in list(self._permissions.items()):
            if perm.agent_id == agent_id and perm.user_id == user_id:
                del self._permissions[pid]
        permission = AgentPermission(
            id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            user_id=user_id,
            role=role,
            granted_by=granted_by,
        )
        self._permissions[permission.id] = permission
        logger.info(f"Permission {permission.id}: {user_id} granted {role} on {agent_id}")
        return permission

    def revoke_permission(self, permission_id: str) -> bool:
        if permission_id not in self._permissions:
            raise KeyError("Permission not found")
        del self._permissions[permission_id]
        logger.info(f"Permission {permission_id} revoked")
        return True

    def check_permission(self, agent_id: str, user_id: str, action: str) -> bool:
        if action not in ACTION_REQUIREMENTS:
            raise ValueError(f"Invalid action. Must be one of {list(ACTION_REQUIREMENTS.keys())}")
        required_role = ACTION_REQUIREMENTS[action]
        required_level = ROLE_HIERARCHY[required_role]
        for perm in self._permissions.values():
            if perm.agent_id == agent_id and perm.user_id == user_id:
                user_level = ROLE_HIERARCHY.get(perm.role, -1)
                return user_level >= required_level
        return False

    def list_permissions(self, agent_id: str) -> List[AgentPermission]:
        return [p for p in self._permissions.values() if p.agent_id == agent_id]


agent_permission_engine = AgentPermissionEngine()
