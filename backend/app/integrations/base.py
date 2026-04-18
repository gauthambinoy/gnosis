"""Universal Action Protocol — base interface and central registry for all connectors."""

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


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
    data: Any
    error: str | None = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    retryable: bool = False


class BaseConnector(ABC):
    @abstractmethod
    def get_actions(self) -> list[ActionDefinition]: ...

    @abstractmethod
    async def execute(self, capability: str, inputs: dict) -> ActionResult: ...

    @abstractmethod
    async def test_connection(self) -> bool: ...


# ---------------------------------------------------------------------------
# Universal Action Protocol — central registry
# ---------------------------------------------------------------------------


class UniversalActionProtocol:
    """Central registry for all agent actions across all integrations."""

    def __init__(self):
        self.connectors: dict[str, BaseConnector] = {}
        self.action_registry: dict[str, Callable] = {}  # "gmail.send_email" → method
        self._action_definitions: dict[
            str, ActionDefinition
        ] = {}  # "gmail.send_email" → def
        self._action_connector_map: dict[str, str] = {}  # "gmail.send_email" → "gmail"

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_connector(self, name: str, connector: BaseConnector):
        """Register an integration connector and index all its actions."""
        self.connectors[name] = connector

        # Index actions from get_actions() definitions
        for action_def in connector.get_actions():
            action_key = f"{name}.{action_def.capability}"
            self._action_definitions[action_key] = action_def
            self._action_connector_map[action_key] = name

        # Auto-discover async methods that aren't private/abstract/inherited from ABC
        self._autodiscover_methods(name, connector)

    def _autodiscover_methods(self, name: str, connector: BaseConnector):
        """Introspect connector to find all public async methods and register them."""
        base_methods = {"execute", "test_connection", "get_actions"}

        for method_name, method in inspect.getmembers(
            connector, predicate=inspect.ismethod
        ):
            if method_name.startswith("_"):
                continue
            if method_name in base_methods:
                continue
            if not asyncio.iscoroutinefunction(method):
                continue

            action_key = f"{name}.{method_name}"
            self.action_registry[action_key] = method

            # Build a schema from the method signature if no definition exists
            if action_key not in self._action_definitions:
                sig = inspect.signature(method)
                inputs = {}
                for param_name, param in sig.parameters.items():
                    if param_name in ("self", "user_id"):
                        continue
                    annotation = param.annotation
                    type_str = "string"
                    if annotation != inspect.Parameter.empty:
                        type_str = getattr(annotation, "__name__", str(annotation))
                    inputs[param_name] = {
                        "type": type_str,
                        "required": param.default is inspect.Parameter.empty,
                    }

                self._action_definitions[action_key] = ActionDefinition(
                    service=name,
                    capability=method_name,
                    description=f"{name}.{method_name}",
                    inputs=inputs,
                    outputs={},
                )
                self._action_connector_map[action_key] = name

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    async def execute_action(
        self, action: str, params: dict, user_id: str
    ) -> ActionResult:
        """Execute any action by name: 'gmail.send_email', 'slack.send_message', etc."""
        start = time.time()

        # Resolve connector and capability
        connector_name = self._action_connector_map.get(action)
        if not connector_name:
            return ActionResult(
                success=False,
                data=None,
                error=f"Unknown action: {action}",
                latency_ms=(time.time() - start) * 1000,
            )

        connector = self.connectors.get(connector_name)
        if not connector:
            return ActionResult(
                success=False,
                data=None,
                error=f"Connector not found: {connector_name}",
                latency_ms=(time.time() - start) * 1000,
            )

        # Try direct method from action_registry first
        direct_method = self.action_registry.get(action)
        if direct_method:
            try:
                # Inject user_id if the method accepts it
                sig = inspect.signature(direct_method)
                if "user_id" in sig.parameters:
                    result = await direct_method(user_id=user_id, **params)
                else:
                    result = await direct_method(**params)

                latency = (time.time() - start) * 1000
                if isinstance(result, ActionResult):
                    result.latency_ms = latency
                    return result
                return ActionResult(
                    success=True,
                    data=result if isinstance(result, dict) else {"result": result},
                    latency_ms=latency,
                )
            except Exception as exc:
                latency = (time.time() - start) * 1000
                return ActionResult(
                    success=False,
                    data=None,
                    error=str(exc),
                    latency_ms=latency,
                    retryable=_is_retryable(exc),
                )

        # Fallback to connector.execute()
        capability = action.split(".", 1)[1] if "." in action else action
        try:
            result = await connector.execute(
                capability=capability,
                inputs={**params, "user_id": user_id},
            )
            result.latency_ms = (time.time() - start) * 1000
            return result
        except Exception as exc:
            latency = (time.time() - start) * 1000
            return ActionResult(
                success=False,
                data=None,
                error=str(exc),
                latency_ms=latency,
                retryable=_is_retryable(exc),
            )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    def list_actions(self) -> list[dict]:
        """List all available actions with their parameter schemas."""
        actions = []
        for key, defn in self._action_definitions.items():
            actions.append(
                {
                    "action": key,
                    "service": defn.service,
                    "capability": defn.capability,
                    "description": defn.description,
                    "inputs": defn.inputs,
                    "outputs": defn.outputs,
                    "auth_type": defn.auth_type,
                }
            )
        return actions

    def get_action_schema(self, action: str) -> dict:
        """Get parameter schema for an action (for LLM function calling)."""
        defn = self._action_definitions.get(action)
        if not defn:
            return {"error": f"Unknown action: {action}"}

        # Build an OpenAI-compatible function schema
        properties = {}
        required = []
        for param_name, param_info in defn.inputs.items():
            prop: dict = {"type": param_info.get("type", "string")}
            if "enum" in param_info:
                prop["enum"] = param_info["enum"]
            if "description" in param_info:
                prop["description"] = param_info["description"]
            properties[param_name] = prop
            if param_info.get("required", True):
                required.append(param_name)

        return {
            "name": action,
            "description": defn.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def list_connectors(self) -> dict[str, bool]:
        """List all registered connectors and their status."""
        return {name: True for name in self.connectors}


def _is_retryable(exc: Exception) -> bool:
    """Heuristic: network/timeout errors are retryable."""
    msg = str(exc).lower()
    return any(kw in msg for kw in ("timeout", "connection", "503", "429", "rate"))


# Global singleton
action_protocol = UniversalActionProtocol()
