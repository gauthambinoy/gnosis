"""Wire the event bus to WebSocket broadcasts."""
from app.core.event_bus import event_bus, Events
from app.ws.manager import ws_manager


async def _on_agent_event(event: dict):
    await ws_manager.broadcast_dashboard(event["type"], event["payload"])


async def _on_execution_event(event: dict):
    payload = event["payload"]
    await ws_manager.broadcast_dashboard(event["type"], payload)
    if agent_id := payload.get("agent_id"):
        await ws_manager.broadcast_agent(agent_id, event["type"], payload)


async def _on_insight_event(event: dict):
    await ws_manager.broadcast_dashboard(event["type"], event["payload"])


def setup_event_wiring():
    """Register all event handlers. Call this at startup."""
    event_bus.on(Events.AGENT_CREATED, _on_agent_event)
    event_bus.on(Events.AGENT_UPDATED, _on_agent_event)
    event_bus.on(Events.AGENT_DELETED, _on_agent_event)
    event_bus.on(Events.EXECUTION_STARTED, _on_execution_event)
    event_bus.on(Events.EXECUTION_COMPLETED, _on_execution_event)
    event_bus.on(Events.EXECUTION_FAILED, _on_execution_event)
    event_bus.on(Events.TRUST_CHANGED, _on_agent_event)
    event_bus.on(Events.INSIGHT_GENERATED, _on_insight_event)
