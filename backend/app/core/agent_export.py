"""Gnosis Agent Export/Import — Portable agent configurations."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("gnosis.export")

EXPORT_VERSION = "1.0"


def export_agent(agent_config: dict) -> dict:
    """Export agent config as a portable JSON structure."""
    sanitized = {
        k: v
        for k, v in agent_config.items()
        if k not in ("api_keys", "secrets", "internal_id")
    }
    return {
        "gnosis_export": True,
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "agent": sanitized,
    }


def export_agents_bulk(agents: list[dict]) -> dict:
    """Export multiple agents."""
    return {
        "gnosis_export": True,
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "agents": [export_agent(a)["agent"] for a in agents],
        "count": len(agents),
    }


def validate_import(data: dict) -> tuple[bool, str]:
    """Validate import data structure."""
    if not isinstance(data, dict):
        return False, "Invalid format: expected JSON object"
    if not data.get("gnosis_export"):
        return False, "Not a Gnosis export file"
    if "agent" not in data and "agents" not in data:
        return False, "No agent data found"
    return True, "Valid"


def import_agent(data: dict) -> Optional[dict]:
    """Import a single agent from export data."""
    valid, msg = validate_import(data)
    if not valid:
        return None

    agent = data.get("agent", {})
    # Assign new ID
    agent["id"] = str(uuid.uuid4())
    agent["imported_at"] = datetime.now(timezone.utc).isoformat()
    agent["imported_from_version"] = data.get("version", "unknown")
    return agent


def import_agents_bulk(data: dict) -> list[dict]:
    """Import multiple agents from bulk export."""
    valid, msg = validate_import(data)
    if not valid:
        return []

    agents = data.get("agents", [])
    result = []
    for agent in agents:
        agent["id"] = str(uuid.uuid4())
        agent["imported_at"] = datetime.now(timezone.utc).isoformat()
        result.append(agent)
    return result
