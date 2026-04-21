"""Concurrent-safety tests for the WebSocket ConnectionManager."""

import asyncio
import pytest

from app.ws.manager import ConnectionManager


class FakeWS:
    def __init__(self, fail_send: bool = False):
        self.accepted = False
        self.sent: list[str] = []
        self.fail_send = fail_send

    async def accept(self):
        self.accepted = True

    async def send_text(self, msg: str):
        if self.fail_send:
            raise RuntimeError("boom")
        self.sent.append(msg)


@pytest.mark.anyio
async def test_concurrent_connect_disconnect_dashboard():
    mgr = ConnectionManager()
    sockets = [FakeWS() for _ in range(50)]

    await asyncio.gather(
        *(mgr.connect_dashboard(ws, user_id=f"u{i}") for i, ws in enumerate(sockets))
    )
    assert mgr.dashboard_count == 50
    assert mgr.total_connections == 50

    await asyncio.gather(*(mgr.disconnect(ws) for ws in sockets))
    assert mgr.dashboard_count == 0
    assert mgr.total_connections == 0


@pytest.mark.anyio
async def test_concurrent_agent_watchers_connect_disconnect():
    mgr = ConnectionManager()
    sockets = [FakeWS() for _ in range(30)]
    agent_id = "agent-x"

    await asyncio.gather(
        *(mgr.connect_agent_watcher(ws, agent_id) for ws in sockets)
    )
    assert mgr.agent_watcher_count(agent_id) == 30

    # Disconnect half concurrently with new connects
    extra = [FakeWS() for _ in range(10)]

    await asyncio.gather(
        *(mgr.disconnect(ws) for ws in sockets[:15]),
        *(mgr.connect_agent_watcher(ws, agent_id) for ws in extra),
    )
    assert mgr.agent_watcher_count(agent_id) == 30 - 15 + 10
    assert mgr.total_connections == mgr.agent_watcher_count(agent_id)


@pytest.mark.anyio
async def test_broadcast_prunes_dead_connections():
    mgr = ConnectionManager()
    good = [FakeWS() for _ in range(5)]
    bad = [FakeWS(fail_send=True) for _ in range(3)]
    for ws in good + bad:
        await mgr.connect_dashboard(ws, user_id="u")

    await mgr.broadcast_dashboard("ping", {"x": 1})

    assert mgr.dashboard_count == 5
    assert all(len(ws.sent) == 1 for ws in good)


@pytest.mark.anyio
async def test_concurrent_broadcast_and_disconnect_no_error():
    mgr = ConnectionManager()
    sockets = [FakeWS() for _ in range(20)]
    for ws in sockets:
        await mgr.connect_dashboard(ws, user_id="u")

    async def broadcaster():
        for _ in range(10):
            await mgr.broadcast_dashboard("evt", {"i": 1})
            await asyncio.sleep(0)

    async def disconnector():
        for ws in sockets:
            await mgr.disconnect(ws)
            await asyncio.sleep(0)

    await asyncio.gather(broadcaster(), disconnector())
    assert mgr.dashboard_count == 0
