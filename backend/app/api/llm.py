from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.llm.router import model_router, TIER_CONFIG
from app.core.cost_tracker import cost_tracker
from app.core.llm_gateway import llm_gateway, LLMRequest
from app.core.auth import get_current_user_id
from app.core.quota_engine import quota_engine
from app.core.error_handling import QuotaExceededError

router = APIRouter()


def _enforce_token_quota(user_id: str, requested_tokens: int) -> None:
    """Reject request if it would push the user over their daily token quota."""
    check = quota_engine.check_quota(user_id, "tokens", max(1, int(requested_tokens)))
    if not check["allowed"]:
        raise QuotaExceededError(
            "Daily token quota exceeded",
            detail=check,
        )


class CompletionRequest(BaseModel):
    prompt: str
    system_prompt: str = "You are Gnosis, an intelligent AI agent."
    model: str = ""
    provider: str = ""
    max_tokens: int = 1024
    temperature: float = 0.7


class TestRequest(BaseModel):
    prompt: str = "Say hello in one sentence."
    provider: str = ""


@router.get("/models")
async def list_models(provider: str = ""):
    """List available models from the configured provider."""
    models = await llm_gateway.list_available_models(provider)
    return {
        "models": models,
        "provider": provider
        or llm_gateway.settings.default_llm_provider
        or "openrouter",
    }


@router.post("/complete")
async def complete(
    request: CompletionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Direct LLM completion endpoint via the universal gateway."""
    _enforce_token_quota(user_id, request.max_tokens)
    llm_req = LLMRequest(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        model=request.model,
        provider=request.provider,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    response = await llm_gateway.complete(llm_req)
    quota_engine.record_usage(user_id, "tokens", int(response.tokens_used or 0))
    return {
        "content": response.content,
        "model": response.model,
        "provider": response.provider,
        "tokens_used": response.tokens_used,
        "tokens_prompt": response.tokens_prompt,
        "tokens_completion": response.tokens_completion,
        "latency_ms": round(response.latency_ms, 1),
        "cost_estimate": response.cost_estimate,
        "cached": response.cached,
    }


@router.get("/stats")
async def get_llm_stats():
    return {
        "router": model_router.stats,
        "gateway": llm_gateway.get_stats(),
    }


@router.post("/test")
async def test_connection(
    request: TestRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Test LLM connection with a simple prompt."""
    _enforce_token_quota(user_id, 100)
    llm_req = LLMRequest(
        prompt=request.prompt,
        system_prompt="You are a helpful assistant. Be very brief.",
        model="fast",
        provider=request.provider,
        max_tokens=100,
        temperature=0.5,
    )
    response = await llm_gateway.complete(llm_req)
    quota_engine.record_usage(user_id, "tokens", int(response.tokens_used or 0))
    return {
        "status": "ok" if response.provider != "none" else "no_api_key",
        "content": response.content,
        "model": response.model,
        "provider": response.provider,
        "latency_ms": round(response.latency_ms, 1),
    }


@router.get("/tiers")
async def get_tiers():
    return {"tiers": TIER_CONFIG}


@router.get("/providers")
async def get_providers():
    return {
        "providers": [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "description": "200+ models via single API",
                "recommended": True,
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "description": "Claude models direct",
            },
            {"id": "openai", "name": "OpenAI", "description": "GPT models direct"},
            {"id": "google", "name": "Google AI", "description": "Gemini models"},
            {"id": "groq", "name": "Groq", "description": "Ultra-fast inference"},
            {
                "id": "ollama",
                "name": "Ollama",
                "description": "Local models, zero cost",
            },
            {
                "id": "together",
                "name": "Together AI",
                "description": "Open source models",
            },
            {
                "id": "custom",
                "name": "Custom Endpoint",
                "description": "Any OpenAI-compatible API",
            },
        ]
    }


@router.get("/costs")
async def get_costs():
    return {"today": cost_tracker.today_stats, "total": cost_tracker.total_stats}


@router.get("/costs/{agent_id}")
async def get_agent_costs(agent_id: str):
    return cost_tracker.agent_stats(agent_id)


@router.get("/costs/recent/records")
async def get_recent_cost_records(limit: int = 50):
    return {"records": cost_tracker.recent_records(limit)}
