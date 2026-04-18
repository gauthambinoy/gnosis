"""Reliable webhook delivery with retries, signing, and delivery tracking."""

import hmac
import hashlib
import json
import uuid
import asyncio
import aiohttp
from datetime import datetime, timezone
from app.core.logger import get_logger

logger = get_logger("webhooks")


class WebhookManager:
    def __init__(self):
        self.subscriptions: list[dict] = []  # {id, url, events, secret, active}
        self.delivery_log: list[dict] = []
        self.max_log = 1000

    def subscribe(self, url: str, events: list[str], secret: str = None) -> dict:
        sub = {
            "id": str(uuid.uuid4()),
            "url": url,
            "events": events,
            "secret": secret or uuid.uuid4().hex,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deliveries": 0,
            "failures": 0,
        }
        self.subscriptions.append(sub)
        return sub

    def unsubscribe(self, sub_id: str):
        self.subscriptions = [s for s in self.subscriptions if s["id"] != sub_id]

    def _sign_payload(self, payload: str, secret: str) -> str:
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def deliver(self, event_type: str, payload: dict):
        """Deliver webhook to all matching subscriptions."""
        matching = [
            s for s in self.subscriptions if s["active"] and event_type in s["events"]
        ]
        tasks = [self._deliver_one(sub, event_type, payload) for sub in matching]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver_one(
        self, sub: dict, event_type: str, payload: dict, attempt: int = 1
    ):
        body = json.dumps(
            {
                "event": event_type,
                "data": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        signature = self._sign_payload(body, sub["secret"])
        headers = {
            "Content-Type": "application/json",
            "X-Gnosis-Signature": f"sha256={signature}",
            "X-Gnosis-Event": event_type,
            "X-Gnosis-Delivery": str(uuid.uuid4()),
        }

        delivery = {
            "subscription_id": sub["id"],
            "event": event_type,
            "url": sub["url"],
            "attempt": attempt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    sub["url"],
                    data=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    delivery["status"] = resp.status
                    delivery["success"] = 200 <= resp.status < 300
                    sub["deliveries"] += 1
        except Exception as e:
            delivery["status"] = 0
            delivery["success"] = False
            delivery["error"] = str(e)
            sub["failures"] += 1

            # Retry up to 3 times with backoff
            if attempt < 3:
                await asyncio.sleep(attempt * 2)
                await self._deliver_one(sub, event_type, payload, attempt + 1)
                return

        self.delivery_log.append(delivery)
        if len(self.delivery_log) > self.max_log:
            self.delivery_log = self.delivery_log[-self.max_log :]

    def get_subscriptions(self) -> list[dict]:
        return self.subscriptions

    def get_delivery_log(self, limit: int = 50) -> list[dict]:
        return list(reversed(self.delivery_log[-limit:]))


webhook_manager = WebhookManager()
