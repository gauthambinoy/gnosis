"""Universal Action Protocol — base interface for all connectors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ActionDefinition:
    service: str
    capability: str
    description: str
    inputs: dict
    outputs: dict
    auth_type: str = "oauth2"


@dataclass
class ActionResult:
    success: bool
    data: dict
    error: str | None = None
    latency_ms: float = 0.0


class BaseConnector(ABC):
    @abstractmethod
    def get_actions(self) -> list[ActionDefinition]: ...

    @abstractmethod
    async def execute(self, capability: str, inputs: dict) -> ActionResult: ...

    @abstractmethod
    async def test_connection(self) -> bool: ...
