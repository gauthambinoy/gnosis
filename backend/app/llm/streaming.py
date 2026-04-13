"""SSE streaming utilities for the Gnosis API."""

import json
from typing import AsyncIterator


async def sse_stream(events: AsyncIterator[dict]):
    """Convert an async iterator of events to SSE format."""
    async for event in events:
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"


def sse_event(event_type: str, content: str = "", metadata: dict | None = None) -> dict:
    """Create a standardized SSE event."""
    return {
        "type": event_type,
        "content": content,
        "metadata": metadata or {},
    }
