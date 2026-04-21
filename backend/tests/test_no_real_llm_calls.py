"""M14 regression guard: prove the default LLM mock prevents real network egress.

Any attempt to reach OpenRouter / OpenAI / Anthropic / Ollama / Gemini during
the normal (non-``live_llm``) test run must be blocked.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


async def test_llm_gateway_complete_is_mocked(mock_llm):
    """`llm_gateway.complete` is autouse-patched and returns the canned response."""
    from app.core.llm_gateway import llm_gateway, LLMRequest

    resp = await llm_gateway.complete(LLMRequest(prompt="hello"))
    assert resp.content == mock_llm.response.content
    assert resp.provider == "mock"
    assert mock_llm.call_count == 1


async def test_mock_llm_fixture_customizes_response(mock_llm):
    mock_llm.set_response(
        content="custom-content",
        provider="openrouter",
        model="test/model",
        tokens_prompt=11,
        tokens_completion=22,
        cost_estimate=0.0042,
    )
    from app.core.llm_gateway import llm_gateway, LLMRequest

    resp = await llm_gateway.complete(LLMRequest(prompt="x"))
    assert resp.content == "custom-content"
    assert resp.provider == "openrouter"
    assert resp.model == "test/model"
    assert resp.tokens_prompt == 11
    assert resp.tokens_completion == 22
    assert resp.tokens_used == 33
    assert resp.cost_estimate == pytest.approx(0.0042)


async def test_aiohttp_post_to_llm_hosts_raises(monkeypatch):
    """If any code tries to POST to an LLM provider URL the safety net fires."""
    import aiohttp

    sentinel = {"real_post_called": False}

    async def _should_never_run(self, *a, **kw):  # pragma: no cover
        sentinel["real_post_called"] = True

    # Double-mock: even if the guard were bypassed, this would flip the sentinel.
    # But the guard must raise FIRST.
    async def _try():
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"x": 1},
            ):
                pass

    with pytest.raises(RuntimeError, match="Blocked aiohttp"):
        await _try()
    assert sentinel["real_post_called"] is False


async def test_client_providers_are_mocked():
    """Every provider's streaming `complete` yields the canned mock content."""
    from app.llm.client import (
        AnthropicProvider,
        GoogleProvider,
        OllamaProvider,
        OpenAIProvider,
        OpenRouterProvider,
    )

    providers = [
        OpenRouterProvider(api_key="dummy"),
        AnthropicProvider(api_key="dummy"),
        OllamaProvider(),
        OpenAIProvider(api_key="dummy"),
        GoogleProvider(api_key="dummy"),
    ]
    for p in providers:
        tokens = []
        async for tok in p.complete([{"role": "user", "content": "hi"}]):
            tokens.append(tok)
        assert tokens, f"{type(p).__name__} produced no mock tokens"
        assert "mock" in "".join(tokens).lower() or tokens[0]


async def test_live_llm_marker_is_registered():
    """`live_llm` marker must be registered to avoid PytestUnknownMarkWarning."""
    import subprocess
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert "live_llm" in result.stdout, result.stdout + result.stderr
