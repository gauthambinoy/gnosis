"""Gnosis Edge Deployment — manage lightweight edge deployment configs."""
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


VALID_TARGETS = {"raspberry_pi", "jetson", "lambda", "cloudflare"}


@dataclass
class EdgeDeployment:
    id: str
    agent_id: str
    target: str
    config: dict
    status: str = "pending"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class EdgeDeployEngine:
    """Manages edge deployment configurations."""

    def __init__(self):
        self._deployments: dict[str, EdgeDeployment] = {}

    def create_deployment(self, agent_id: str, target: str, config: dict | None = None) -> EdgeDeployment:
        if target not in VALID_TARGETS:
            raise ValueError(f"Invalid target '{target}'. Must be one of {VALID_TARGETS}")
        dep = EdgeDeployment(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            target=target,
            config=config or {},
        )
        self._deployments[dep.id] = dep
        return dep

    def list_deployments(self, agent_id: str | None = None) -> list[EdgeDeployment]:
        deps = list(self._deployments.values())
        if agent_id:
            deps = [d for d in deps if d.agent_id == agent_id]
        return deps

    def get_deployment(self, deployment_id: str) -> EdgeDeployment | None:
        return self._deployments.get(deployment_id)

    def generate_edge_config(self, agent_id: str, target: str) -> dict:
        base = {"agent_id": agent_id, "target": target, "runtime": "python3.11"}
        configs = {
            "raspberry_pi": {"memory_limit": "512MB", "cpu_cores": 4, "arch": "arm64", "runtime": "python3.11-slim"},
            "jetson": {"memory_limit": "4GB", "gpu": True, "cuda": "11.8", "arch": "arm64"},
            "lambda": {"memory_limit": "256MB", "timeout": 30, "runtime": "python3.11", "handler": "main.handler"},
            "cloudflare": {"runtime": "workers", "memory_limit": "128MB", "cpu_time_ms": 50},
        }
        base.update(configs.get(target, {}))
        return base


edge_deploy_engine = EdgeDeployEngine()
