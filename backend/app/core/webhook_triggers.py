"""Gnosis Webhook Triggers — Inbound webhooks that auto-trigger agents."""
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional, List

logger = logging.getLogger("gnosis.webhook_triggers")


@dataclass
class WebhookTrigger:
    id: str
    agent_id: str
    name: str
    secret: str  # For signature verification
    url_path: str  # /api/v1/webhooks/trigger/{id}
    active: bool = True
    total_invocations: int = 0
    last_invoked: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    allowed_sources: List[str] = field(default_factory=list)  # IP allowlist (empty = allow all)


@dataclass
class WebhookInvocation:
    id: str
    trigger_id: str
    agent_id: str
    payload: dict
    headers: dict
    source_ip: str
    status: str = "pending"  # pending, executing, completed, failed
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WebhookTriggerManager:
    def __init__(self):
        self._triggers: Dict[str, WebhookTrigger] = {}
        self._invocations: Dict[str, WebhookInvocation] = {}
        self._execute_fn = None
    
    def set_executor(self, fn):
        self._execute_fn = fn
    
    def create_trigger(self, agent_id: str, name: str, allowed_sources: list = None) -> WebhookTrigger:
        trigger_id = str(uuid.uuid4())
        secret = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]
        
        trigger = WebhookTrigger(
            id=trigger_id,
            agent_id=agent_id,
            name=name,
            secret=secret,
            url_path=f"/api/v1/webhooks/trigger/{trigger_id}",
            allowed_sources=allowed_sources or [],
        )
        self._triggers[trigger_id] = trigger
        logger.info(f"Webhook trigger created: {trigger_id} for agent {agent_id}")
        return trigger
    
    def get_trigger(self, trigger_id: str) -> Optional[WebhookTrigger]:
        return self._triggers.get(trigger_id)
    
    def list_triggers(self, agent_id: str = None) -> List[WebhookTrigger]:
        triggers = list(self._triggers.values())
        if agent_id:
            triggers = [t for t in triggers if t.agent_id == agent_id]
        return sorted(triggers, key=lambda t: t.created_at, reverse=True)
    
    def delete_trigger(self, trigger_id: str) -> bool:
        return self._triggers.pop(trigger_id, None) is not None
    
    def toggle_trigger(self, trigger_id: str) -> Optional[bool]:
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.active = not trigger.active
            return trigger.active
        return None
    
    def verify_signature(self, trigger_id: str, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return False
        expected = hmac.new(trigger.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    async def invoke(self, trigger_id: str, payload: dict, headers: dict, source_ip: str) -> WebhookInvocation:
        trigger = self._triggers.get(trigger_id)
        if not trigger:
            raise ValueError("Trigger not found")
        if not trigger.active:
            raise ValueError("Trigger is disabled")
        if trigger.allowed_sources and source_ip not in trigger.allowed_sources:
            raise ValueError(f"Source IP {source_ip} not allowed")
        
        invocation = WebhookInvocation(
            id=str(uuid.uuid4()),
            trigger_id=trigger_id,
            agent_id=trigger.agent_id,
            payload=payload,
            headers={k: v for k, v in headers.items() if k.lower().startswith(('x-', 'content-'))},
            source_ip=source_ip,
        )
        self._invocations[invocation.id] = invocation
        
        # Execute agent
        try:
            invocation.status = "executing"
            if self._execute_fn:
                result = await self._execute_fn(trigger.agent_id, payload)
                invocation.result = result if isinstance(result, dict) else {"output": str(result)}
            invocation.status = "completed"
        except Exception as e:
            invocation.status = "failed"
            invocation.error = str(e)
            logger.error(f"Webhook invocation {invocation.id} failed: {e}")
        
        trigger.total_invocations += 1
        trigger.last_invoked = datetime.now(timezone.utc).isoformat()
        
        return invocation
    
    def get_invocations(self, trigger_id: str = None, limit: int = 50) -> List[WebhookInvocation]:
        invocations = list(self._invocations.values())
        if trigger_id:
            invocations = [i for i in invocations if i.trigger_id == trigger_id]
        return sorted(invocations, key=lambda i: i.created_at, reverse=True)[:limit]
    
    @property
    def stats(self) -> dict:
        return {
            "total_triggers": len(self._triggers),
            "active_triggers": sum(1 for t in self._triggers.values() if t.active),
            "total_invocations": len(self._invocations),
        }


webhook_trigger_manager = WebhookTriggerManager()
