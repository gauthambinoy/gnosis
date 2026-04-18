"""Tests for feature flag system.

The ``FeatureFlagEngine`` is fully async (all public methods are coroutines).
These tests use the ``anyio`` plugin (already registered in ``conftest.py``)
so each test can ``await`` the engine directly.

When the application database is unavailable (the default in unit tests),
``engine_state_store`` no-ops, so we can exercise the engine's in-memory
behaviour without spinning up a real database.
"""
import pytest

from app.core.feature_flags import FeatureFlagEngine


@pytest.fixture
def engine() -> FeatureFlagEngine:
    """Fresh engine per test to keep state isolated."""
    return FeatureFlagEngine()


@pytest.mark.anyio
async def test_create_flag(engine):
    flag = await engine.create_flag("test-flag", "A test flag")
    assert flag["name"] == "test-flag"
    assert flag["enabled"] is True
    assert flag["description"] == "A test flag"


@pytest.mark.anyio
async def test_is_enabled_nonexistent(engine):
    assert await engine.is_enabled("nonexistent") is False


@pytest.mark.anyio
async def test_is_enabled_after_create(engine):
    await engine.create_flag("my-flag")
    assert await engine.is_enabled("my-flag") is True


@pytest.mark.anyio
async def test_update_flag_disable(engine):
    flag = await engine.create_flag("toggle-flag")
    await engine.update_flag(flag["id"], enabled=False)
    assert await engine.is_enabled("toggle-flag") is False


@pytest.mark.anyio
async def test_list_flags(engine):
    await engine.create_flag("flag-1")
    await engine.create_flag("flag-2")
    flags = await engine.list_flags()
    assert len(flags) == 2
    names = {f["name"] for f in flags}
    assert names == {"flag-1", "flag-2"}


@pytest.mark.anyio
async def test_user_scope_targeting(engine):
    flag = await engine.create_flag("user-flag", scope="user")
    await engine.update_flag(flag["id"], target_ids=["user-1"])
    assert await engine.is_enabled("user-flag", user_id="user-1") is True
    assert await engine.is_enabled("user-flag", user_id="user-2") is False


@pytest.mark.anyio
async def test_workspace_scope_targeting(engine):
    flag = await engine.create_flag("ws-flag", scope="workspace")
    await engine.update_flag(flag["id"], target_ids=["ws-1"])
    assert await engine.is_enabled("ws-flag", workspace_id="ws-1") is True
    assert await engine.is_enabled("ws-flag", workspace_id="ws-2") is False


@pytest.mark.anyio
async def test_update_nonexistent_flag(engine):
    result = await engine.update_flag("no-such-id", enabled=False)
    assert "error" in result


@pytest.mark.anyio
async def test_create_flag_with_description(engine):
    flag = await engine.create_flag("desc-flag", description="My description")
    assert flag["description"] == "My description"
