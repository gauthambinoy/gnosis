"""Tests for oracle insights and health endpoints.

Oracle endpoints query PostgreSQL directly. We mock _load_agents to avoid DB hits.
"""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_oracle_db():
    """Patch OracleEngine._load_agents so it doesn't touch the real DB."""
    with patch(
        "app.core.oracle_engine.OracleEngine._load_agents",
        new_callable=AsyncMock,
        return_value=[],
    ):
        yield


async def test_oracle_health(client, api_prefix, mock_oracle_db):
    resp = await client.get(f"{api_prefix}/oracle/health")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "overall" in data or "score" in data or len(data) > 0


async def test_oracle_insights(client, api_prefix, mock_oracle_db):
    resp = await client.get(f"{api_prefix}/oracle/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert "insights" in data
    assert isinstance(data["insights"], list)


async def test_oracle_recommendations(client, api_prefix, mock_oracle_db):
    resp = await client.get(f"{api_prefix}/oracle/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
