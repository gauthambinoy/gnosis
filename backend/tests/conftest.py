import os

# Set test environment variables BEFORE any app imports
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-minimum-32-chars-long")

import pytest
import uuid

try:
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    _APP_AVAILABLE = True
except Exception:
    _APP_AVAILABLE = False

pytest_plugins = ["anyio"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client using httpx."""
    if not _APP_AVAILABLE:
        pytest.skip("App could not be loaded")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def api_prefix():
    return "/api/v1"


@pytest.fixture
async def registered_user(client, api_prefix):
    """Register a fresh user and return tokens + info."""
    email = f"test-{uuid.uuid4().hex[:8]}@gnosis.ai"
    payload = {"email": email, "password": "SecurePass123!", "full_name": "Test User"}
    resp = await client.post(f"{api_prefix}/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
        "email": email,
        "password": "SecurePass123!",
    }


@pytest.fixture
async def created_agent(client, api_prefix):
    """Create and return a test agent."""
    payload = {
        "name": "Test Agent",
        "description": "A test agent for automated testing",
        "personality": "professional",
        "avatar_emoji": "🧪",
        "trigger_type": "manual",
        "integrations": ["gmail"],
        "guardrails": ["no-mass-email"],
    }
    resp = await client.post(f"{api_prefix}/agents", json=payload)
    assert resp.status_code == 201
    return resp.json()
