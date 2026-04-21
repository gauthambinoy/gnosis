import os

# Set test environment variables BEFORE any app imports
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault(
    "SECRET_KEY", "test-secret-key-for-testing-only-minimum-32-chars-long"
)

import pytest
import uuid
from unittest.mock import AsyncMock

try:
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    _APP_AVAILABLE = True
except Exception:
    _APP_AVAILABLE = False

pytest_plugins = ["anyio"]


# ---------------------------------------------------------------------------
# LLM network safety net (M14)
#
# By default, NO test is allowed to reach a real LLM provider. The autouse
# fixture below replaces every outbound call path (llm_gateway singleton
# + app.llm.client provider classes + aiohttp.ClientSession.post to known
# LLM hostnames) with deterministic in-memory fakes. Tests that opt in via
# the `live_llm` marker get the real call paths back.
#
# Tests that want to customize the canned response use the `mock_llm`
# fixture (see below).
# ---------------------------------------------------------------------------

_LLM_HOSTS = (
    "openrouter.ai",
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "localhost:11434",  # Ollama
    "127.0.0.1:11434",
)


class _LLMCallBlocked(RuntimeError):
    """Raised if a test tries to reach a real LLM endpoint."""


def _make_canned_response(
    content: str = "[mock-llm] canned test response",
    *,
    model: str = "mock-model",
    provider: str = "mock",
    tokens_prompt: int = 3,
    tokens_completion: int = 7,
    cost_estimate: float = 0.0,
    latency_ms: float = 1.0,
    cached: bool = False,
):
    from app.core.llm_gateway import LLMResponse

    return LLMResponse(
        content=content,
        model=model,
        provider=provider,
        tokens_used=tokens_prompt + tokens_completion,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        latency_ms=latency_ms,
        cost_estimate=cost_estimate,
        cached=cached,
    )


class _MockLLMController:
    """Knob exposed to tests via the `mock_llm` fixture."""

    def __init__(self):
        self._response = _make_canned_response()
        self.call_count = 0
        self.last_request = None

    def set_response(self, **kwargs):
        """Override fields on the canned response. Accepts any LLMResponse field."""
        cur = self._response
        merged = dict(
            content=cur.content,
            model=cur.model,
            provider=cur.provider,
            tokens_prompt=cur.tokens_prompt,
            tokens_completion=cur.tokens_completion,
            cost_estimate=cur.cost_estimate,
            latency_ms=cur.latency_ms,
            cached=cur.cached,
        )
        merged.update(kwargs)
        self._response = _make_canned_response(**merged)
        return self._response

    @property
    def response(self):
        return self._response

    async def _complete(self, request):
        self.call_count += 1
        self.last_request = request
        return self._response


@pytest.fixture(autouse=True)
def _block_real_llm_calls(request, monkeypatch):
    """Default-deny outbound LLM calls across the entire test suite.

    Skipped when a test is marked with ``@pytest.mark.live_llm``.
    """
    if request.node.get_closest_marker("live_llm"):
        yield None
        return

    controller = _MockLLMController()

    # 1) Patch the core gateway singleton `complete` method.
    try:
        from app.core import llm_gateway as _gw_mod

        monkeypatch.setattr(
            _gw_mod.llm_gateway, "complete", controller._complete, raising=True
        )

        async def _blocked_openai(*a, **kw):  # pragma: no cover - safety net
            raise _LLMCallBlocked(
                "LLMGateway._call_openai_compatible hit during tests"
            )

        async def _blocked_anthropic(*a, **kw):  # pragma: no cover - safety net
            raise _LLMCallBlocked("LLMGateway._call_anthropic hit during tests")

        async def _blocked_post(*a, **kw):  # pragma: no cover - safety net
            raise _LLMCallBlocked("LLMGateway._post_and_parse hit during tests")

        monkeypatch.setattr(
            _gw_mod.LLMGateway, "_call_openai_compatible", _blocked_openai, raising=True
        )
        monkeypatch.setattr(
            _gw_mod.LLMGateway, "_call_anthropic", _blocked_anthropic, raising=True
        )
        monkeypatch.setattr(
            _gw_mod.LLMGateway, "_post_and_parse", _blocked_post, raising=True
        )
    except Exception:
        pass

    # 2) Patch each provider class in app.llm.client so streaming `complete`
    #    yields a canned token instead of opening a real session.
    try:
        from app.llm import client as _client_mod

        async def _fake_stream(self, messages, **kwargs):  # noqa: ARG001
            yield controller.response.content

        for cls_name in (
            "OpenRouterProvider",
            "AnthropicProvider",
            "OllamaProvider",
            "OpenAIProvider",
            "GoogleProvider",
        ):
            cls = getattr(_client_mod, cls_name, None)
            if cls is not None:
                monkeypatch.setattr(cls, "complete", _fake_stream, raising=True)
    except Exception:
        pass

    # 3) URL-aware safety net on aiohttp: any POST/GET to a known LLM host
    #    inside tests must raise. Non-LLM aiohttp traffic (e.g. integrations)
    #    is left untouched.
    try:
        import aiohttp

        real_post = aiohttp.ClientSession.post
        real_get = aiohttp.ClientSession.get

        def _guard(method_name, real):
            def _wrapper(self, url, *args, **kwargs):
                u = str(url)
                if any(h in u for h in _LLM_HOSTS):
                    raise _LLMCallBlocked(
                        f"Blocked aiohttp.{method_name} to LLM host: {u}"
                    )
                return real(self, url, *args, **kwargs)

            return _wrapper

        monkeypatch.setattr(
            aiohttp.ClientSession, "post", _guard("post", real_post), raising=True
        )
        monkeypatch.setattr(
            aiohttp.ClientSession, "get", _guard("get", real_get), raising=True
        )
    except Exception:
        pass

    # 4) Defense in depth for httpx — some code paths may adopt httpx later.
    try:
        import httpx

        real_async_send = httpx.AsyncClient.send
        real_sync_send = httpx.Client.send

        def _httpx_async_guard(self, request, *a, **kw):
            u = str(getattr(request, "url", ""))
            if any(h in u for h in _LLM_HOSTS):
                raise _LLMCallBlocked(f"Blocked httpx.AsyncClient to LLM host: {u}")
            return real_async_send(self, request, *a, **kw)

        def _httpx_sync_guard(self, request, *a, **kw):
            u = str(getattr(request, "url", ""))
            if any(h in u for h in _LLM_HOSTS):
                raise _LLMCallBlocked(f"Blocked httpx.Client to LLM host: {u}")
            return real_sync_send(self, request, *a, **kw)

        monkeypatch.setattr(
            httpx.AsyncClient, "send", _httpx_async_guard, raising=True
        )
        monkeypatch.setattr(httpx.Client, "send", _httpx_sync_guard, raising=True)
    except Exception:
        pass

    # Stash controller so the `mock_llm` fixture can expose it.
    request.node._llm_mock_controller = controller
    yield controller


@pytest.fixture
def mock_llm(request):
    """Handle to the autouse LLM mock.

    Usage::

        def test_something(mock_llm):
            mock_llm.set_response(content="hi", tokens_prompt=1, tokens_completion=2)
            ...
    """
    controller = getattr(request.node, "_llm_mock_controller", None)
    if controller is None:
        pytest.skip("LLM mock not installed (likely @pytest.mark.live_llm)")
    return controller


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear in-memory rate limiter state between tests to avoid cross-test bleed."""
    try:
        from app.core.rate_limiter import rate_limiter
        rate_limiter.windows.clear()
    except Exception:
        pass
    # Reset Starlette security middleware counts if present
    try:
        from app.main import app
        for mw in app.user_middleware:
            inst = getattr(mw, "kwargs", {})
            # No direct access — walk app.middleware_stack at runtime
        # Walk middleware stack to clear per-IP counters
        stack = getattr(app, "middleware_stack", None)
        seen = set()
        while stack is not None and id(stack) not in seen:
            seen.add(id(stack))
            for attr in (
                "request_counts",
                "_windows",
                "_buckets",
                "_blocked_ips",
                "_attempts",
                "_locked",
            ):
                d = getattr(stack, attr, None)
                if isinstance(d, dict):
                    d.clear()
            rl = getattr(stack, "rate_limiter", None)
            if rl is not None:
                for attr in (
                    "requests",
                    "_windows",
                    "request_counts",
                    "_buckets",
                    "_blocked_ips",
                    "_attempts",
                    "_locked",
                ):
                    d = getattr(rl, attr, None)
                    if isinstance(d, dict):
                        d.clear()
            stack = getattr(stack, "app", None)
    except Exception:
        pass
    yield


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


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_agent():
    """Sample agent data for testing."""
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "system_prompt": "You are a helpful assistant.",
        "model": "gpt-4",
        "tools": [],
        "temperature": 0.7,
    }


@pytest.fixture
def auth_headers():
    """Generate test auth headers with a valid JWT."""
    from app.core.auth import create_access_token

    token = create_access_token(
        {"sub": "00000000-0000-0000-0000-000000000001", "type": "access"}
    )
    return {"Authorization": f"Bearer {token}"}
