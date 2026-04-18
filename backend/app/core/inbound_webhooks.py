"""Gnosis Inbound Webhooks — accept external webhooks to trigger agents."""

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
import hashlib
import hmac
import secrets


@dataclass
class InboundWebhook:
    id: str
    name: str
    agent_id: str
    secret: str
    active: bool = True
    trigger_count: int = 0
    last_triggered: str | None = None


class InboundWebhookEngine:
    """Manages inbound webhook registrations and triggers."""

    def __init__(self):
        self._hooks: dict[str, InboundWebhook] = {}
        self._trigger_log: list[dict] = []

    def register_hook(self, name: str, agent_id: str) -> InboundWebhook:
        hook = InboundWebhook(
            id=str(uuid.uuid4()),
            name=name,
            agent_id=agent_id,
            secret=secrets.token_hex(32),
        )
        self._hooks[hook.id] = hook
        return hook

    def list_hooks(self, agent_id: str | None = None) -> list[InboundWebhook]:
        hooks = list(self._hooks.values())
        if agent_id:
            hooks = [h for h in hooks if h.agent_id == agent_id]
        return hooks

    def verify_signature(self, hook_id: str, payload: str, signature: str) -> bool:
        hook = self._hooks.get(hook_id)
        if not hook:
            return False
        expected = hmac.new(
            hook.secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def trigger(self, hook_id: str, payload: dict) -> dict | None:
        hook = self._hooks.get(hook_id)
        if not hook or not hook.active:
            return None
        hook.trigger_count += 1
        hook.last_triggered = datetime.now(timezone.utc).isoformat()
        entry = {
            "hook_id": hook_id,
            "agent_id": hook.agent_id,
            "payload": payload,
            "triggered_at": hook.last_triggered,
        }
        self._trigger_log.append(entry)
        return entry


inbound_webhook_engine = InboundWebhookEngine()
