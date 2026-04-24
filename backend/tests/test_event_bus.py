"""Tests for the in-process event bus, particularly handler error logging
(regression for H5: previously used print()).
"""

from __future__ import annotations

import logging

import pytest

from app.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_emit_calls_registered_handler():
    bus = EventBus()
    received: list[dict] = []

    async def handler(event):
        received.append(event)

    bus.on("agent.created", handler)
    await bus.emit("agent.created", {"id": "a1"})

    assert len(received) == 1
    assert received[0]["type"] == "agent.created"
    assert received[0]["payload"] == {"id": "a1"}


@pytest.mark.asyncio
async def test_failing_handler_does_not_break_others_and_logs(monkeypatch):
    bus = EventBus()
    fired: list[str] = []
    logged: list[str] = []

    import app.core.event_bus as ebmod

    def _capture(*args, **kwargs):
        logged.append(args[0] if args else "")

    monkeypatch.setattr(ebmod.logger, "exception", _capture)

    async def boom(event):
        raise RuntimeError("kaboom")

    async def ok(event):
        fired.append("ok")

    bus.on("x", boom)
    bus.on("x", ok)

    await bus.emit("x", {})

    assert fired == ["ok"], "second handler must run even if first raises"
    assert any("event_bus.handler_failed" in m for m in logged)


@pytest.mark.asyncio
async def test_wildcard_handler_receives_all_events():
    bus = EventBus()
    seen: list[str] = []

    async def star(event):
        seen.append(event["type"])

    bus.on("*", star)
    await bus.emit("a.one", {})
    await bus.emit("b.two", {})
    assert seen == ["a.one", "b.two"]


@pytest.mark.asyncio
async def test_history_capped_at_max():
    bus = EventBus()
    bus._max_history = 5

    async def noop(_):
        pass

    bus.on("e", noop)
    for i in range(20):
        await bus.emit("e", {"i": i})
    assert len(bus._history) == 5
    assert bus._history[-1]["payload"]["i"] == 19


@pytest.mark.asyncio
async def test_recent_events_returns_tail():
    bus = EventBus()

    async def noop(_):
        pass

    bus.on("e", noop)
    for i in range(10):
        await bus.emit("e", {"i": i})
    tail = bus.recent_events(limit=3)
    assert [e["payload"]["i"] for e in tail] == [7, 8, 9]
