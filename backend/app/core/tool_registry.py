"""Gnosis Tool Registry — Organization-level shared tools with versioning."""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.tools")

@dataclass
class ToolDefinition:
    id: str
    name: str
    description: str
    category: str  # "api", "browser", "file", "code", "custom"
    version: str = "1.0.0"
    schema: dict = field(default_factory=dict)  # JSON Schema for inputs
    implementation: str = ""  # Code or endpoint reference
    workspace_id: Optional[str] = None  # None = global
    created_by: Optional[str] = None
    is_public: bool = False
    usage_count: int = 0
    avg_latency_ms: float = 0
    success_rate: float = 1.0
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deprecated: bool = False
    deprecation_message: str = ""

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._agent_permissions: Dict[str, set] = {}  # agent_id -> {tool_ids}

    def register(self, tool_id: str, name: str, description: str, category: str, **kwargs) -> ToolDefinition:
        tool = ToolDefinition(id=tool_id, name=name, description=description, category=category, **kwargs)
        self._tools[tool_id] = tool
        logger.info(f"Tool registered: {tool_id} ({name})")
        return tool

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def list_tools(self, category: str = None, workspace_id: str = None) -> List[dict]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if workspace_id:
            tools = [t for t in tools if t.workspace_id == workspace_id or t.workspace_id is None]
        return [asdict(t) for t in sorted(tools, key=lambda t: t.name)]

    def grant_access(self, agent_id: str, tool_id: str):
        if agent_id not in self._agent_permissions:
            self._agent_permissions[agent_id] = set()
        self._agent_permissions[agent_id].add(tool_id)

    def revoke_access(self, agent_id: str, tool_id: str):
        if agent_id in self._agent_permissions:
            self._agent_permissions[agent_id].discard(tool_id)

    def check_access(self, agent_id: str, tool_id: str) -> bool:
        tool = self._tools.get(tool_id)
        if not tool:
            return False
        if tool.is_public:
            return True
        return tool_id in self._agent_permissions.get(agent_id, set())

    def record_usage(self, tool_id: str, latency_ms: float, success: bool):
        tool = self._tools.get(tool_id)
        if tool:
            tool.usage_count += 1
            tool.avg_latency_ms = (tool.avg_latency_ms * 0.9) + (latency_ms * 0.1)
            if not success:
                tool.success_rate = (tool.success_rate * 0.95)

    def deprecate(self, tool_id: str, message: str = ""):
        tool = self._tools.get(tool_id)
        if tool:
            tool.deprecated = True
            tool.deprecation_message = message
            tool.updated_at = datetime.now(timezone.utc).isoformat()

    def search(self, query: str) -> List[dict]:
        query_lower = query.lower()
        results = [t for t in self._tools.values() if query_lower in t.name.lower() or query_lower in t.description.lower() or any(query_lower in tag for tag in t.tags)]
        return [asdict(t) for t in sorted(results, key=lambda t: t.usage_count, reverse=True)]

tool_registry = ToolRegistry()
