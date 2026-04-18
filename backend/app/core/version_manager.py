"""Gnosis Version Manager — Track and rollback agent configuration versions."""

import uuid
import copy
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.versions")


@dataclass
class AgentVersion:
    id: str
    agent_id: str
    version_number: int
    config_snapshot: dict  # Full agent config at this point
    change_summary: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_by: Optional[str] = None
    is_current: bool = False


class VersionManager:
    """Manages agent configuration versions with auto-save and rollback."""

    def __init__(self):
        self._versions: Dict[str, List[AgentVersion]] = {}  # agent_id -> versions list

    def save_version(
        self,
        agent_id: str,
        config: dict,
        change_summary: str = "",
        created_by: str = None,
    ) -> AgentVersion:
        """Auto-save a new version when agent config changes."""
        if agent_id not in self._versions:
            self._versions[agent_id] = []

        # Mark all previous as not current
        for v in self._versions[agent_id]:
            v.is_current = False

        version = AgentVersion(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            version_number=len(self._versions[agent_id]) + 1,
            config_snapshot=copy.deepcopy(config),
            change_summary=change_summary,
            created_by=created_by,
            is_current=True,
        )
        self._versions[agent_id].append(version)
        logger.info(f"Version {version.version_number} saved for agent {agent_id}")
        return version

    def get_versions(self, agent_id: str) -> List[AgentVersion]:
        return list(reversed(self._versions.get(agent_id, [])))

    def get_version(self, agent_id: str, version_id: str) -> Optional[AgentVersion]:
        for v in self._versions.get(agent_id, []):
            if v.id == version_id:
                return v
        return None

    def get_version_by_number(
        self, agent_id: str, version_number: int
    ) -> Optional[AgentVersion]:
        for v in self._versions.get(agent_id, []):
            if v.version_number == version_number:
                return v
        return None

    def get_current(self, agent_id: str) -> Optional[AgentVersion]:
        for v in reversed(self._versions.get(agent_id, [])):
            if v.is_current:
                return v
        return None

    def rollback(self, agent_id: str, version_id: str) -> Optional[AgentVersion]:
        """Rollback to a specific version (creates a new version with old config)."""
        target = self.get_version(agent_id, version_id)
        if not target:
            return None

        new_version = self.save_version(
            agent_id=agent_id,
            config=target.config_snapshot,
            change_summary=f"Rollback to version {target.version_number}",
        )
        logger.info(f"Agent {agent_id} rolled back to version {target.version_number}")
        return new_version

    def diff(self, agent_id: str, version_a_id: str, version_b_id: str) -> dict:
        """Compare two versions and return differences."""
        va = self.get_version(agent_id, version_a_id)
        vb = self.get_version(agent_id, version_b_id)
        if not va or not vb:
            return {"error": "Version not found"}

        added, removed, changed = {}, {}, {}
        all_keys = set(
            list(va.config_snapshot.keys()) + list(vb.config_snapshot.keys())
        )

        for key in all_keys:
            a_val = va.config_snapshot.get(key)
            b_val = vb.config_snapshot.get(key)
            if a_val is None and b_val is not None:
                added[key] = b_val
            elif a_val is not None and b_val is None:
                removed[key] = a_val
            elif a_val != b_val:
                changed[key] = {"from": a_val, "to": b_val}

        return {
            "version_a": va.version_number,
            "version_b": vb.version_number,
            "added": added,
            "removed": removed,
            "changed": changed,
            "total_changes": len(added) + len(removed) + len(changed),
        }

    def delete_old_versions(self, agent_id: str, keep: int = 20) -> int:
        """Prune old versions, keeping the most recent N."""
        versions = self._versions.get(agent_id, [])
        if len(versions) <= keep:
            return 0
        removed = len(versions) - keep
        self._versions[agent_id] = versions[-keep:]
        return removed

    @property
    def stats(self) -> dict:
        total_agents = len(self._versions)
        total_versions = sum(len(v) for v in self._versions.values())
        return {
            "total_agents_versioned": total_agents,
            "total_versions": total_versions,
        }


version_manager = VersionManager()
