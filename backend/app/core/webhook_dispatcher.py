"""Gnosis Webhook Dispatcher — Fire webhooks on key events."""

import uuid
import asyncio
import logging
import time
import hmac
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.webhooks")


@dataclass
class WebhookEndpoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    events: List[str] = field(
        default_factory=list
    )  # ["execution.completed", "agent.error", ...]
    secret: str = ""  # For HMAC signing
    active: bool = True
    workspace_id: str = ""
    created_by: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    failure_count: int = 0
    last_triggered: Optional[str] = None


@dataclass
class WebhookDelivery:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    endpoint_id: str = ""
    event: str = ""
    status: str = "pending"  # pending, delivered, failed
    status_code: int = 0
    response_ms: float = 0
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


ALL_EVENTS = [
    "execution.completed",
    "execution.failed",
    "execution.started",
    "agent.created",
    "agent.error",
    "agent.paused",
    "pipeline.completed",
    "pipeline.failed",
    "budget.warning",
    "budget.exceeded",
    "memory.correction",
    "file.uploaded",
]


class WebhookDispatcher:
    def __init__(self):
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: List[WebhookDelivery] = []
        self._max_deliveries = 5000

    def register(
        self,
        url: str,
        events: List[str],
        secret: str = "",
        workspace_id: str = "",
        created_by: str = "",
    ) -> WebhookEndpoint:
        endpoint = WebhookEndpoint(
            url=url,
            events=events,
            secret=secret,
            workspace_id=workspace_id,
            created_by=created_by,
        )
        self._endpoints[endpoint.id] = endpoint
        logger.info(f"Webhook registered: {endpoint.id} -> {url} for {events}")
        return endpoint

    def unregister(self, endpoint_id: str) -> bool:
        return self._endpoints.pop(endpoint_id, None) is not None

    def list_endpoints(self, workspace_id: str = None) -> List[dict]:
        eps = list(self._endpoints.values())
        if workspace_id:
            eps = [e for e in eps if e.workspace_id == workspace_id]
        return [asdict(e) for e in eps]

    async def dispatch(self, event: str, payload: dict):
        """Fire webhooks for all endpoints subscribed to this event."""
        targets = [
            ep
            for ep in self._endpoints.values()
            if ep.active and (event in ep.events or "*" in ep.events)
        ]
        if not targets:
            return

        tasks = [self._deliver(ep, event, payload) for ep in targets]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver(self, endpoint: WebhookEndpoint, event: str, payload: dict):
        delivery = WebhookDelivery(endpoint_id=endpoint.id, event=event)
        body = json.dumps(
            {
                "event": event,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        headers = {"Content-Type": "application/json", "X-Gnosis-Event": event}
        if endpoint.secret:
            sig = hmac.new(
                endpoint.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Gnosis-Signature"] = f"sha256={sig}"

        start = time.time()
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(endpoint.url, content=body, headers=headers)
                delivery.status_code = resp.status_code
                delivery.status = "delivered" if resp.status_code < 400 else "failed"
                if resp.status_code >= 400:
                    delivery.error = f"HTTP {resp.status_code}"
                    endpoint.failure_count += 1
        except Exception as e:
            delivery.status = "failed"
            delivery.error = str(e)[:200]
            endpoint.failure_count += 1

        delivery.response_ms = round((time.time() - start) * 1000, 1)
        endpoint.last_triggered = datetime.now(timezone.utc).isoformat()

        self._deliveries.append(delivery)
        if len(self._deliveries) > self._max_deliveries:
            self._deliveries = self._deliveries[-self._max_deliveries :]

        # Auto-disable after 10 consecutive failures
        if endpoint.failure_count >= 10:
            endpoint.active = False
            logger.warning(f"Webhook auto-disabled due to failures: {endpoint.id}")

    def get_deliveries(self, endpoint_id: str = None, limit: int = 50) -> List[dict]:
        deliveries = self._deliveries
        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]
        return [asdict(d) for d in deliveries[-limit:][::-1]]

    @property
    def stats(self) -> dict:
        total = len(self._deliveries)
        delivered = sum(1 for d in self._deliveries if d.status == "delivered")
        return {
            "total_endpoints": len(self._endpoints),
            "active_endpoints": sum(1 for e in self._endpoints.values() if e.active),
            "total_deliveries": total,
            "success_rate": round(delivered / max(total, 1) * 100, 1),
        }


webhook_dispatcher = WebhookDispatcher()
