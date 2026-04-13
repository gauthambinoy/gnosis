"""HTTP Universal connector — allows agents to call any API."""
import time

import aiohttp

from app.integrations.base import BaseConnector, ActionDefinition, ActionResult


class HTTPUniversalConnector(BaseConnector):
    """Execute arbitrary HTTP requests — allows agents to call any API."""

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(
                service="http",
                capability="request",
                description="Execute an arbitrary HTTP request to any URL",
                inputs={
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                    "timeout": {"type": "integer"},
                },
                outputs={
                    "status": {"type": "integer"},
                    "headers": {"type": "object"},
                    "body": {"type": "any"},
                },
                auth_type="none",
            ),
        ]

    async def execute(
        self,
        method: str = "GET",
        url: str = "",
        headers: dict | None = None,
        body: dict | None = None,
        timeout: int = 30,
        *,
        capability: str = "request",
        inputs: dict | None = None,
    ) -> ActionResult:
        """Execute an HTTP request.

        Can be called directly with explicit params or via the UAP
        interface (capability + inputs dict).
        """
        # Support UAP-style invocation
        if inputs:
            method = inputs.get("method", method)
            url = inputs.get("url", url)
            headers = inputs.get("headers", headers)
            body = inputs.get("body", body)
            timeout = inputs.get("timeout", timeout)

        if not url:
            return ActionResult(success=False, data={}, error="URL is required")

        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                kwargs: dict = {"headers": headers or {}, "timeout": aiohttp.ClientTimeout(total=timeout)}
                if body and method.upper() in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = body

                async with session.request(method.upper(), url, **kwargs) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        resp_body = await resp.json()
                    else:
                        resp_body = await resp.text()

                    latency = (time.time() - start) * 1000
                    return ActionResult(
                        success=200 <= resp.status < 400,
                        data={
                            "status": resp.status,
                            "headers": dict(resp.headers),
                            "body": resp_body,
                        },
                        latency_ms=latency,
                    )
        except Exception as exc:
            latency = (time.time() - start) * 1000
            return ActionResult(success=False, data={}, error=str(exc), latency_ms=latency)

    async def test_connection(self) -> bool:
        """HTTP connector is always available."""
        return True
