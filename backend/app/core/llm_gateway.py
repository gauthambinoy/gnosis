"""
Gnosis Universal LLM Gateway
Routes requests to any LLM provider via OpenRouter or direct APIs.
Supports: OpenRouter (100+ models), OpenAI, Anthropic, Google, Mistral, Groq, Cohere, Together
"""

import logging
import aiohttp
import time
import hashlib
from typing import Optional
from dataclasses import dataclass
from app.config import get_settings
from app.core.retry import with_retry

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str = "You are Gnosis, an intelligent AI agent."
    model: str = ""  # Empty = use default
    provider: str = ""  # Empty = use default
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = False
    user_id: str = ""
    validate_as: str = "free_text"  # ContentType value: free_text, tool_parameter, etc.


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int
    tokens_prompt: int
    tokens_completion: int
    latency_ms: float
    cost_estimate: float
    cached: bool = False


class LLMGateway:
    """Universal LLM Gateway with caching, fallback, and cost tracking."""

    PROVIDER_CONFIGS = {
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "models": {
                "default": "meta-llama/llama-3.1-8b-instruct:free",
                "fast": "meta-llama/llama-3.1-8b-instruct:free",
                "balanced": "anthropic/claude-3.5-haiku",
                "powerful": "anthropic/claude-3.5-sonnet",
                "cheap": "meta-llama/llama-3.1-8b-instruct:free",
            },
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "models": {
                "default": "gpt-4o-mini",
                "fast": "gpt-4o-mini",
                "powerful": "gpt-4o",
            },
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "models": {
                "default": "claude-3-5-haiku-20241022",
                "powerful": "claude-3-5-sonnet-20241022",
            },
        },
    }

    # Rough cost per 1M tokens (input/output)
    MODEL_COSTS = {
        "meta-llama/llama-3.1-8b-instruct:free": (0, 0),
        "anthropic/claude-3.5-haiku": (1.0, 5.0),
        "anthropic/claude-3.5-sonnet": (3.0, 15.0),
        "gpt-4o-mini": (0.15, 0.6),
        "gpt-4o": (2.5, 10.0),
    }

    def __init__(self):
        self.settings = get_settings()
        self._cache: dict[str, tuple[LLMResponse, float]] = {}
        self._cache_ttl = 300  # 5 min
        self._max_cache = 500
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._errors = 0
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=25)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _get_api_key(self, provider: str) -> str:
        keys = {
            "openrouter": self.settings.openrouter_api_key,
            "openai": self.settings.openai_api_key,
            "anthropic": self.settings.anthropic_api_key,
        }
        return keys.get(provider, "")

    def _resolve_model(self, provider: str, model: str) -> str:
        if model and "/" in model:
            return model  # Fully qualified model name
        config = self.PROVIDER_CONFIGS.get(
            provider, self.PROVIDER_CONFIGS["openrouter"]
        )
        return config["models"].get(model or "default", config["models"]["default"])

    def _cache_key(self, req: LLMRequest) -> str:
        raw = (
            f"{req.prompt}:{req.system_prompt}:{req.model}:{round(req.temperature, 2)}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[LLMResponse]:
        if key in self._cache:
            resp, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                resp.cached = True
                return resp
            del self._cache[key]
        return None

    def _store_cache(self, key: str, resp: LLMResponse):
        if len(self._cache) >= self._max_cache:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest]
        self._cache[key] = (resp, time.time())

    def _validate_output(self, content: str, content_type_name: str = "free_text") -> str:
        """Run the LLM output validator as a non-blocking defence-in-depth check.

        Validation failures are logged as warnings; the original content is always
        returned so user-facing flows are never broken by the validator.
        """
        try:
            from app.core.llm_output_validator import (
                LLMOutputValidator,
                ContentType,
            )
            try:
                ct = ContentType(content_type_name or "free_text")
            except ValueError:
                ct = ContentType.FREE_TEXT
            LLMOutputValidator.validate(content, ct)
        except Exception as e:  # noqa: BLE001 — non-blocking by design
            logger.warning("LLM output validator flagged response: %s", e)
        return content

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Main entry point — routes to the right provider with caching + fallback."""
        start = time.time()
        self._total_requests += 1

        # Check cache
        cache_key = self._cache_key(request)
        cached = self._check_cache(cache_key)
        if cached:
            return cached

        # Determine provider
        provider = (
            request.provider or self.settings.default_llm_provider or "openrouter"
        )
        model = self._resolve_model(provider, request.model)
        api_key = self._get_api_key(provider)

        # If no API key, try fallback providers
        if not api_key:
            for fallback in ["openrouter", "openai", "anthropic"]:
                fb_key = self._get_api_key(fallback)
                if fb_key:
                    provider = fallback
                    api_key = fb_key
                    model = self._resolve_model(provider, request.model)
                    break

        # If still no key, return helpful error (not mock data)
        if not api_key:
            return LLMResponse(
                content=(
                    "⚠️ No LLM API key configured. Add OPENROUTER_API_KEY to your "
                    ".env file. Get one free at https://openrouter.ai/keys"
                ),
                model="none",
                provider="none",
                tokens_used=0,
                tokens_prompt=0,
                tokens_completion=0,
                latency_ms=(time.time() - start) * 1000,
                cost_estimate=0,
            )

        # Route to provider
        try:
            if provider == "anthropic":
                resp = await self._call_anthropic(api_key, model, request)
            else:
                # OpenRouter and OpenAI both use OpenAI-compatible API
                base_url = self.PROVIDER_CONFIGS.get(provider, {}).get(
                    "base_url", "https://openrouter.ai/api/v1"
                )
                resp = await self._call_openai_compatible(
                    api_key, base_url, model, request, provider
                )

            resp.latency_ms = (time.time() - start) * 1000
            self._total_tokens += resp.tokens_used
            self._total_cost += resp.cost_estimate
            resp.content = self._validate_output(resp.content, request.validate_as)
            self._store_cache(cache_key, resp)
            return resp

        except Exception as e:
            self._errors += 1
            # Try fallback
            if provider != "openrouter" and self._get_api_key("openrouter"):
                try:
                    fb_model = self._resolve_model("openrouter", "fast")
                    resp = await self._call_openai_compatible(
                        self._get_api_key("openrouter"),
                        "https://openrouter.ai/api/v1",
                        fb_model,
                        request,
                        "openrouter",
                    )
                    resp.latency_ms = (time.time() - start) * 1000
                    resp.content = self._validate_output(
                        resp.content, request.validate_as
                    )
                    return resp
                except Exception:
                    logger.warning(
                        "LLM provider %s failed, trying fallback",
                        provider,
                        exc_info=True,
                    )

            return LLMResponse(
                content=f"LLM Error: {str(e)}. Check your API key and try again.",
                model=model,
                provider=provider,
                tokens_used=0,
                tokens_prompt=0,
                tokens_completion=0,
                latency_ms=(time.time() - start) * 1000,
                cost_estimate=0,
            )

    async def _post_and_parse(self, session, url, headers, payload) -> dict:
        """Make an aiohttp POST and return parsed JSON, suitable for with_retry."""
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"API returned {resp.status}: {error_text[:200]}")
            return await resp.json()

    async def _call_openai_compatible(
        self,
        api_key: str,
        base_url: str,
        model: str,
        req: LLMRequest,
        provider: str,
    ) -> LLMResponse:
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://gnosis.ai"
            headers["X-Title"] = "Gnosis AI Platform"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.prompt},
            ],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }

        data = await with_retry(
            self._post_and_parse,
            session,
            f"{base_url}/chat/completions",
            headers,
            payload,
            max_retries=3,
            delay=1.0,
            task_name=f"llm-{provider}",
        )

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        costs = self.MODEL_COSTS.get(model, (0.5, 1.5))
        cost = (prompt_tokens * costs[0] + completion_tokens * costs[1]) / 1_000_000

        return LLMResponse(
            content=choice,
            model=model,
            provider=provider,
            tokens_used=prompt_tokens + completion_tokens,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            latency_ms=0,  # Set by caller
            cost_estimate=cost,
        )

    async def _call_anthropic(
        self, api_key: str, model: str, req: LLMRequest
    ) -> LLMResponse:
        session = await self._get_session()
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": req.max_tokens,
            "system": req.system_prompt,
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": req.temperature,
        }

        data = await with_retry(
            self._post_and_parse,
            session,
            "https://api.anthropic.com/v1/messages",
            headers,
            payload,
            max_retries=3,
            delay=1.0,
            task_name="llm-anthropic",
        )

        content = data["content"][0]["text"]
        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)

        costs = self.MODEL_COSTS.get(model, (3.0, 15.0))
        cost = (prompt_tokens * costs[0] + completion_tokens * costs[1]) / 1_000_000

        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=prompt_tokens + completion_tokens,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            latency_ms=0,
            cost_estimate=cost,
        )

    async def list_available_models(self, provider: str = "") -> list[dict]:
        """List models available for a provider."""
        if not provider:
            provider = self.settings.default_llm_provider or "openrouter"

        if provider == "openrouter" and self._get_api_key("openrouter"):
            try:
                session = await self._get_session()
                headers = {"Authorization": f"Bearer {self._get_api_key('openrouter')}"}
                async with session.get(
                    "https://openrouter.ai/api/v1/models", headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [
                            {
                                "id": m["id"],
                                "name": m.get("name", m["id"]),
                                "context_length": m.get("context_length", 0),
                            }
                            for m in data.get("data", [])[:50]
                        ]
            except Exception:
                logger.debug("LLM cache cleanup failed", exc_info=True)

        config = self.PROVIDER_CONFIGS.get(provider, {})
        return [
            {"id": v, "name": k, "context_length": 0}
            for k, v in config.get("models", {}).items()
        ]

    def get_stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 6),
            "errors": self._errors,
            "cache_size": len(self._cache),
            "cache_hit_rate": 0,
        }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton
llm_gateway = LLMGateway()
