"""Gnosis Config Snapshots — Immutable versioned agent configurations."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional, List

logger = logging.getLogger("gnosis.config_snapshots")


@dataclass
class ConfigSnapshot:
    id: str  # SHA-256 hash of the config content
    agent_id: str
    version: int
    config: dict  # The frozen config
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_by: Optional[str] = None
    description: str = ""
    is_active: bool = False


class ConfigSnapshotStore:
    def __init__(self):
        self._snapshots: Dict[str, ConfigSnapshot] = {}  # id -> snapshot
        self._agent_versions: Dict[
            str, List[str]
        ] = {}  # agent_id -> [snapshot_ids ordered by version]
        self._active: Dict[str, str] = {}  # agent_id -> active snapshot_id

    def create_snapshot(
        self, agent_id: str, config: dict, created_by: str = None, description: str = ""
    ) -> ConfigSnapshot:
        config_json = json.dumps(config, sort_keys=True, default=str)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:16]

        # Check for duplicate
        if config_hash in self._snapshots:
            logger.info(f"Config snapshot already exists: {config_hash}")
            return self._snapshots[config_hash]

        versions = self._agent_versions.get(agent_id, [])
        version = len(versions) + 1

        snapshot = ConfigSnapshot(
            id=config_hash,
            agent_id=agent_id,
            version=version,
            config=config,
            created_by=created_by,
            description=description or f"v{version}",
        )

        self._snapshots[config_hash] = snapshot
        if agent_id not in self._agent_versions:
            self._agent_versions[agent_id] = []
        self._agent_versions[agent_id].append(config_hash)

        logger.info(
            f"Config snapshot created: agent={agent_id}, version={version}, hash={config_hash}"
        )
        return snapshot

    def activate(self, snapshot_id: str) -> bool:
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        # Deactivate current
        current = self._active.get(snapshot.agent_id)
        if current and current in self._snapshots:
            self._snapshots[current].is_active = False
        snapshot.is_active = True
        self._active[snapshot.agent_id] = snapshot_id
        return True

    def get(self, snapshot_id: str) -> Optional[ConfigSnapshot]:
        return self._snapshots.get(snapshot_id)

    def get_active(self, agent_id: str) -> Optional[ConfigSnapshot]:
        sid = self._active.get(agent_id)
        return self._snapshots.get(sid) if sid else None

    def list_versions(self, agent_id: str) -> List[ConfigSnapshot]:
        ids = self._agent_versions.get(agent_id, [])
        return [self._snapshots[sid] for sid in ids if sid in self._snapshots]

    def diff(self, snapshot_a_id: str, snapshot_b_id: str) -> dict:
        a = self._snapshots.get(snapshot_a_id)
        b = self._snapshots.get(snapshot_b_id)
        if not a or not b:
            return {"error": "Snapshot not found"}

        added, removed, changed = {}, {}, {}
        all_keys = set(a.config.keys()) | set(b.config.keys())
        for key in all_keys:
            va, vb = a.config.get(key), b.config.get(key)
            if va is None:
                added[key] = vb
            elif vb is None:
                removed[key] = va
            elif va != vb:
                changed[key] = {"old": va, "new": vb}

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "total_changes": len(added) + len(removed) + len(changed),
        }


config_snapshot_store = ConfigSnapshotStore()
