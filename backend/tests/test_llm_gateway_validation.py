"""Verify that the LLM gateway invokes the output validator on every completion."""

from unittest.mock import patch, AsyncMock

import pytest

from app.core.llm_gateway import LLMGateway, LLMRequest, LLMResponse


def _fake_response(content: str = "hello world") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="test-model",
        provider="openrouter",
        tokens_used=5,
        tokens_prompt=2,
        tokens_completion=3,
        latency_ms=0,
        cost_estimate=0.0,
    )


@pytest.mark.asyncio
async def test_validator_invoked_on_completion():
    gw = LLMGateway()
    gw.settings.openrouter_api_key = "test-key"

    fake = _fake_response("safe response text")

    with patch.object(
        gw, "_call_openai_compatible", new=AsyncMock(return_value=fake)
    ), patch(
        "app.core.llm_output_validator.LLMOutputValidator.validate",
        return_value="safe response text",
    ) as mock_validate:
        resp = await gw.complete(LLMRequest(prompt="hello"))

    assert mock_validate.call_count >= 1
    assert resp.content == "safe response text"


@pytest.mark.asyncio
async def test_validator_failure_is_non_blocking():
    """If the validator raises, the original response must still pass through."""
    gw = LLMGateway()
    gw.settings.openrouter_api_key = "test-key"

    fake = _fake_response("rm -rf / dangerous content")

    with patch.object(
        gw, "_call_openai_compatible", new=AsyncMock(return_value=fake)
    ), patch(
        "app.core.llm_output_validator.LLMOutputValidator.validate",
        side_effect=RuntimeError("validator exploded"),
    ) as mock_validate:
        resp = await gw.complete(LLMRequest(prompt="hello"))

    assert mock_validate.call_count >= 1
    assert resp.content == "rm -rf / dangerous content"


@pytest.mark.asyncio
async def test_validator_uses_tool_parameter_content_type():
    gw = LLMGateway()
    gw.settings.openrouter_api_key = "test-key"

    fake = _fake_response('{"x": 1}')

    with patch.object(
        gw, "_call_openai_compatible", new=AsyncMock(return_value=fake)
    ), patch(
        "app.core.llm_output_validator.LLMOutputValidator.validate",
        return_value='{"x": 1}',
    ) as mock_validate:
        await gw.complete(
            LLMRequest(prompt="hello", validate_as="tool_parameter")
        )

    assert mock_validate.call_count >= 1
    args, kwargs = mock_validate.call_args
    from app.core.llm_output_validator import ContentType

    assert args[1] == ContentType.TOOL_PARAMETER
