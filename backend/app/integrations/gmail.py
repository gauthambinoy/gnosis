"""Gmail connector — UAP compliant, real Gmail API v1 integration."""
import base64
import time
from email.mime.text import MIMEText

import aiohttp

from app.integrations.base import BaseConnector, ActionDefinition, ActionResult
from app.integrations.oauth import oauth_manager

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def _parse_headers(headers: list[dict]) -> dict:
    """Extract common headers into a clean dict."""
    wanted = {"From", "To", "Subject", "Date", "Message-ID", "In-Reply-To"}
    return {h["name"]: h["value"] for h in headers if h["name"] in wanted}


def _parse_message(raw: dict) -> dict:
    """Parse a Gmail API message resource into a clean dict."""
    payload = raw.get("payload", {})
    headers = _parse_headers(payload.get("headers", []))
    snippet = raw.get("snippet", "")

    # Try to extract plain-text body
    body = ""
    parts = payload.get("parts", [])
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                break
    elif payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    return {
        "id": raw.get("id"),
        "threadId": raw.get("threadId"),
        "labelIds": raw.get("labelIds", []),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "snippet": snippet,
        "body": body,
    }


class GmailConnector(BaseConnector):
    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(
                service="gmail", capability="list_messages",
                description="List emails from inbox",
                inputs={"query": {"type": "string"}, "max_results": {"type": "integer"}},
                outputs={"emails": {"type": "array"}},
            ),
            ActionDefinition(
                service="gmail", capability="get_message",
                description="Get a single email by ID",
                inputs={"message_id": {"type": "string"}},
                outputs={"email": {"type": "object"}},
            ),
            ActionDefinition(
                service="gmail", capability="send_email",
                description="Send an email",
                inputs={"to": {"type": "email"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                outputs={"message_id": {"type": "string"}},
            ),
            ActionDefinition(
                service="gmail", capability="reply_message",
                description="Reply to an email",
                inputs={"message_id": {"type": "string"}, "body": {"type": "string"}},
                outputs={"message_id": {"type": "string"}},
            ),
            ActionDefinition(
                service="gmail", capability="search_messages",
                description="Search emails",
                inputs={"query": {"type": "string"}},
                outputs={"emails": {"type": "array"}},
            ),
            ActionDefinition(
                service="gmail", capability="modify_labels",
                description="Add/remove labels on a message",
                inputs={"message_id": {"type": "string"}, "add": {"type": "array"}, "remove": {"type": "array"}},
                outputs={"labelIds": {"type": "array"}},
            ),
        ]

    async def _get_headers(self, user_id: str) -> dict:
        token = await oauth_manager.get_valid_token("google", user_id)
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Real Gmail API methods
    # ------------------------------------------------------------------

    async def list_messages(self, user_id: str, query: str = "", max_results: int = 10) -> list[dict]:
        headers = await self._get_headers(user_id)
        params: dict = {"maxResults": max_results}
        if query:
            params["q"] = query

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{GMAIL_API}/messages", headers=headers, params=params) as resp:
                data = await resp.json()

            messages = data.get("messages", [])
            results = []
            for msg_stub in messages:
                async with session.get(
                    f"{GMAIL_API}/messages/{msg_stub['id']}", headers=headers, params={"format": "full"}
                ) as resp2:
                    raw = await resp2.json()
                results.append(_parse_message(raw))
        return results

    async def get_message(self, user_id: str, message_id: str) -> dict:
        headers = await self._get_headers(user_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GMAIL_API}/messages/{message_id}", headers=headers, params={"format": "full"}
            ) as resp:
                raw = await resp.json()
        return _parse_message(raw)

    async def send_message(self, user_id: str, to: str, subject: str, body: str) -> dict:
        headers = await self._get_headers(user_id)
        mime = MIMEText(body)
        mime["to"] = to
        mime["subject"] = subject
        raw_b64 = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GMAIL_API}/messages/send",
                headers={**headers, "Content-Type": "application/json"},
                json={"raw": raw_b64},
            ) as resp:
                data = await resp.json()
        return {"id": data.get("id"), "threadId": data.get("threadId")}

    async def reply_message(self, user_id: str, message_id: str, body: str) -> dict:
        original = await self.get_message(user_id, message_id)
        headers = await self._get_headers(user_id)

        mime = MIMEText(body)
        mime["to"] = original.get("from", "")
        mime["subject"] = f"Re: {original.get('subject', '')}"
        mime["In-Reply-To"] = original.get("id", "")
        raw_b64 = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GMAIL_API}/messages/send",
                headers={**headers, "Content-Type": "application/json"},
                json={"raw": raw_b64, "threadId": original.get("threadId")},
            ) as resp:
                data = await resp.json()
        return {"id": data.get("id"), "threadId": data.get("threadId")}

    async def search_messages(self, user_id: str, query: str) -> list[dict]:
        return await self.list_messages(user_id, query=query, max_results=20)

    async def modify_labels(
        self, user_id: str, message_id: str, add: list | None = None, remove: list | None = None
    ) -> dict:
        headers = await self._get_headers(user_id)
        payload = {
            "addLabelIds": add or [],
            "removeLabelIds": remove or [],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GMAIL_API}/messages/{message_id}/modify",
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                data = await resp.json()
        return {"id": data.get("id"), "labelIds": data.get("labelIds", [])}

    # ------------------------------------------------------------------
    # UAP interface
    # ------------------------------------------------------------------

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        start = time.time()
        try:
            dispatch = {
                "list_messages": lambda: self.list_messages(
                    inputs["user_id"], inputs.get("query", ""), inputs.get("max_results", 10)
                ),
                "get_message": lambda: self.get_message(inputs["user_id"], inputs["message_id"]),
                "send_email": lambda: self.send_message(
                    inputs["user_id"], inputs["to"], inputs["subject"], inputs["body"]
                ),
                "reply_message": lambda: self.reply_message(inputs["user_id"], inputs["message_id"], inputs["body"]),
                "search_messages": lambda: self.search_messages(inputs["user_id"], inputs["query"]),
                "modify_labels": lambda: self.modify_labels(
                    inputs["user_id"], inputs["message_id"], inputs.get("add"), inputs.get("remove")
                ),
            }
            handler = dispatch.get(capability)
            if not handler:
                return ActionResult(success=False, data={}, error=f"Unknown capability: {capability}")
            result = await handler()
            latency = (time.time() - start) * 1000
            return ActionResult(success=True, data=result if isinstance(result, dict) else {"items": result}, latency_ms=latency)
        except Exception as exc:
            latency = (time.time() - start) * 1000
            return ActionResult(success=False, data={}, error=str(exc), latency_ms=latency)

    async def test_connection(self) -> bool:
        try:
            token = await oauth_manager.get_valid_token("google", "default")
            return bool(token)
        except Exception:
            return False
