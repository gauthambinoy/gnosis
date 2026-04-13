"""Slack connector — UAP compliant, real Slack Web API integration."""
import time

import aiohttp

from app.integrations.base import BaseConnector, ActionDefinition, ActionResult
from app.integrations.oauth import oauth_manager

SLACK_API = "https://slack.com/api"


class SlackConnector(BaseConnector):
    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(
                service="slack", capability="send_message",
                description="Send a message to a Slack channel",
                inputs={"channel": {"type": "string"}, "text": {"type": "string"}, "thread_ts": {"type": "string"}},
                outputs={"ts": {"type": "string"}, "channel": {"type": "string"}},
            ),
            ActionDefinition(
                service="slack", capability="list_channels",
                description="List Slack channels",
                inputs={},
                outputs={"channels": {"type": "array"}},
            ),
            ActionDefinition(
                service="slack", capability="get_channel_history",
                description="Read messages from a channel",
                inputs={"channel": {"type": "string"}, "limit": {"type": "integer"}},
                outputs={"messages": {"type": "array"}},
            ),
            ActionDefinition(
                service="slack", capability="add_reaction",
                description="Add emoji reaction to a message",
                inputs={"channel": {"type": "string"}, "timestamp": {"type": "string"}, "emoji": {"type": "string"}},
                outputs={"ok": {"type": "boolean"}},
            ),
            ActionDefinition(
                service="slack", capability="search_messages",
                description="Search Slack messages",
                inputs={"query": {"type": "string"}},
                outputs={"messages": {"type": "array"}},
            ),
        ]

    async def _get_headers(self, user_id: str) -> dict:
        token = await oauth_manager.get_valid_token("slack", user_id)
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    # ------------------------------------------------------------------
    # Real Slack API methods
    # ------------------------------------------------------------------

    async def send_message(
        self, user_id: str, channel: str, text: str, thread_ts: str | None = None
    ) -> dict:
        headers = await self._get_headers(user_id)
        payload: dict = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{SLACK_API}/chat.postMessage", headers=headers, json=payload) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error', 'unknown')}")
        return {"ts": data.get("ts"), "channel": data.get("channel")}

    async def list_channels(self, user_id: str) -> list[dict]:
        headers = await self._get_headers(user_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SLACK_API}/conversations.list",
                headers=headers,
                params={"types": "public_channel,private_channel", "limit": 200},
            ) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error', 'unknown')}")
        return [
            {"id": ch["id"], "name": ch.get("name", ""), "is_member": ch.get("is_member", False), "topic": ch.get("topic", {}).get("value", "")}
            for ch in data.get("channels", [])
        ]

    async def get_channel_history(
        self, user_id: str, channel: str, limit: int = 20
    ) -> list[dict]:
        headers = await self._get_headers(user_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SLACK_API}/conversations.history",
                headers=headers,
                params={"channel": channel, "limit": limit},
            ) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error', 'unknown')}")
        return [
            {"ts": m.get("ts"), "user": m.get("user"), "text": m.get("text", ""), "type": m.get("type")}
            for m in data.get("messages", [])
        ]

    async def add_reaction(
        self, user_id: str, channel: str, timestamp: str, emoji: str
    ) -> dict:
        headers = await self._get_headers(user_id)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SLACK_API}/reactions.add",
                headers=headers,
                json={"channel": channel, "timestamp": timestamp, "name": emoji},
            ) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error', 'unknown')}")
        return {"ok": True}

    async def search_messages(self, user_id: str, query: str) -> list[dict]:
        headers = await self._get_headers(user_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SLACK_API}/search.messages",
                headers=headers,
                params={"query": query, "count": 20},
            ) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error', 'unknown')}")
        raw_matches = data.get("messages", {}).get("matches", [])
        return [
            {"ts": m.get("ts"), "channel": m.get("channel", {}).get("name", ""), "user": m.get("user"), "text": m.get("text", "")}
            for m in raw_matches
        ]

    # ------------------------------------------------------------------
    # UAP interface
    # ------------------------------------------------------------------

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        start = time.time()
        try:
            dispatch = {
                "send_message": lambda: self.send_message(
                    inputs["user_id"], inputs["channel"], inputs["text"], inputs.get("thread_ts")
                ),
                "list_channels": lambda: self.list_channels(inputs["user_id"]),
                "get_channel_history": lambda: self.get_channel_history(
                    inputs["user_id"], inputs["channel"], inputs.get("limit", 20)
                ),
                "add_reaction": lambda: self.add_reaction(
                    inputs["user_id"], inputs["channel"], inputs["timestamp"], inputs["emoji"]
                ),
                "search_messages": lambda: self.search_messages(inputs["user_id"], inputs["query"]),
            }
            handler = dispatch.get(capability)
            if not handler:
                return ActionResult(success=False, data={}, error=f"Unknown capability: {capability}")
            result = await handler()
            latency = (time.time() - start) * 1000
            return ActionResult(
                success=True,
                data=result if isinstance(result, dict) else {"items": result},
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.time() - start) * 1000
            return ActionResult(success=False, data={}, error=str(exc), latency_ms=latency)

    async def test_connection(self) -> bool:
        try:
            token = await oauth_manager.get_valid_token("slack", "default")
            return bool(token)
        except Exception:
            return False
