"""
Universal LLM Gateway — supports any provider.
All Gnosis code calls this gateway, never providers directly.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass, field
import asyncio
import json
import time
import aiohttp


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    latency_ms: float


class LLMProvider(ABC):
    """Base interface all providers implement."""

    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Stream completion tokens."""
        ...

    @abstractmethod
    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        """Return structured JSON output."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens for cost tracking."""
        ...

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD."""
        ...


# ---------------------------------------------------------------------------
# Existing providers
# ---------------------------------------------------------------------------

class OpenRouterProvider(LLMProvider):
    """200+ models via OpenRouter."""

    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        **kwargs,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    async for line in resp.content:
                        text = line.decode().strip()
                        if text.startswith("data: ") and text != "data: [DONE]":
                            chunk = json.loads(text[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
        except Exception:
            return

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.003 + output_tokens * 0.015) / 1000


class AnthropicProvider(LLMProvider):
    """Direct Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            async with aiohttp.ClientSession() as session:
                system = ""
                chat_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system = msg["content"]
                    else:
                        chat_messages.append(msg)

                async with session.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": kwargs.get("max_tokens", 4096),
                        "system": system,
                        "messages": chat_messages,
                        "stream": True,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    async for line in resp.content:
                        text = line.decode().strip()
                        if text.startswith("data: "):
                            try:
                                chunk = json.loads(text[6:])
                                if chunk.get("type") == "content_block_delta":
                                    yield chunk["delta"].get("text", "")
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception:
            return

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.003 + output_tokens * 0.015) / 1000


class OllamaProvider(LLMProvider):
    """Local models via Ollama. Zero cost."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": True},
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    async for line in resp.content:
                        text = line.decode().strip()
                        if text:
                            try:
                                chunk = json.loads(text)
                                if content := chunk.get("message", {}).get("content"):
                                    yield content
                            except json.JSONDecodeError:
                                pass
        except Exception:
            return

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # free!


# ---------------------------------------------------------------------------
# New providers — OpenAI and Google
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    """OpenAI API (GPT-4o, GPT-4, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        **kwargs,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    async for line in resp.content:
                        text = line.decode().strip()
                        if text.startswith("data: ") and text != "data: [DONE]":
                            try:
                                chunk = json.loads(text[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if content := delta.get("content"):
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                pass
        except Exception:
            return

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.005 + output_tokens * 0.015) / 1000


class GoogleProvider(LLMProvider):
    """Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        try:
            # Convert OpenAI-style messages to Gemini format
            contents = []
            for msg in messages:
                role = "user" if msg["role"] in ("user", "system") else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

            async with aiohttp.ClientSession() as session:
                url = (
                    f"{self.base_url}/models/{self.model}:streamGenerateContent"
                    f"?alt=sse&key={self.api_key}"
                )
                async with session.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": contents},
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    async for line in resp.content:
                        text = line.decode().strip()
                        if text.startswith("data: "):
                            try:
                                chunk = json.loads(text[6:])
                                parts = (
                                    chunk.get("candidates", [{}])[0]
                                    .get("content", {})
                                    .get("parts", [])
                                )
                                for part in parts:
                                    if t := part.get("text"):
                                        yield t
                            except (json.JSONDecodeError, KeyError, IndexError):
                                pass
        except Exception:
            return

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.00025 + output_tokens * 0.001) / 1000


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

@dataclass
class _CircuitState:
    failures: list[float] = field(default_factory=list)  # timestamps
    open_until: float = 0.0  # time.time() when circuit re-closes

    FAILURE_WINDOW: float = 300.0  # 5 minutes
    FAILURE_THRESHOLD: int = 3
    COOLDOWN: float = 120.0  # 2 minutes

    def record_failure(self):
        now = time.time()
        self.failures.append(now)
        # Prune old failures
        cutoff = now - self.FAILURE_WINDOW
        self.failures = [t for t in self.failures if t > cutoff]
        if len(self.failures) >= self.FAILURE_THRESHOLD:
            self.open_until = now + self.COOLDOWN

    def record_success(self):
        self.failures.clear()
        self.open_until = 0.0

    @property
    def is_open(self) -> bool:
        if self.open_until == 0.0:
            return False
        if time.time() >= self.open_until:
            # half-open: allow retry
            self.open_until = 0.0
            self.failures.clear()
            return False
        return True


# ---------------------------------------------------------------------------
# Fallback Chain
# ---------------------------------------------------------------------------

class FallbackChain:
    """Wraps multiple LLMProviders with retry + circuit-breaker logic.

    Tries providers in order. Each provider gets 1 retry (2 s timeout)
    before moving to the next. Providers that fail 3× in 5 min are
    skipped for 2 min (circuit breaker).
    """

    RETRY_TIMEOUT: float = 2.0  # seconds per retry attempt

    def __init__(self, providers: list[LLMProvider]):
        self._providers = providers
        self._circuits: dict[int, _CircuitState] = {
            i: _CircuitState() for i in range(len(providers))
        }

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Stream from the first healthy provider in chain."""
        last_error: Exception | None = None

        for idx, provider in enumerate(self._providers):
            circuit = self._circuits[idx]
            if circuit.is_open:
                continue

            for attempt in range(2):  # 1 initial + 1 retry
                try:
                    tokens: list[str] = []
                    async for token in provider.complete(messages, **kwargs):
                        tokens.append(token)
                    if not tokens:
                        raise RuntimeError("Empty response from provider")
                    circuit.record_success()
                    for token in tokens:
                        yield token
                    return
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        await asyncio.sleep(self.RETRY_TIMEOUT)

            circuit.record_failure()

        # All providers exhausted
        if last_error:
            yield f"[FallbackChain] All providers failed. Last error: {last_error}"

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    @property
    def circuit_status(self) -> dict[int, bool]:
        return {i: c.is_open for i, c in self._circuits.items()}


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
}


# ---------------------------------------------------------------------------
# LLM Gateway
# ---------------------------------------------------------------------------

class LLMGateway:
    """The single interface all Gnosis code uses."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_chains: dict[str, FallbackChain] = {}

    def configure(
        self,
        tier: str,
        provider_name: str,
        api_key: str = "",
        model: str = "",
        **kwargs,
    ):
        """Configure a provider for a reasoning tier."""
        provider_class = PROVIDERS.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")

        init_kwargs = {
            k: v
            for k, v in {"api_key": api_key, "model": model, **kwargs}.items()
            if v
        }
        self._providers[tier] = provider_class(**init_kwargs)

    def configure_fallback(self, tier: str, providers: list[LLMProvider]):
        """Configure a fallback chain for a tier."""
        self._fallback_chains[tier] = FallbackChain(providers)

    async def think(
        self, tier: str, messages: list[dict], **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response, trying fallback chain first if configured."""
        chain = self._fallback_chains.get(tier)
        if chain:
            async for token in chain.complete(messages, **kwargs):
                yield token
            return

        provider = self._providers.get(tier)
        if not provider:
            raise ValueError(f"No provider configured for tier: {tier}")
        async for token in provider.complete(messages, **kwargs):
            yield token

    async def think_json(
        self, tier: str, messages: list[dict], schema: dict, **kwargs
    ) -> dict:
        """Get structured JSON response."""
        provider = self._providers.get(tier)
        if not provider:
            raise ValueError(f"No provider configured for tier: {tier}")
        return await provider.complete_json(messages, schema, **kwargs)


# Global gateway instance
gateway = LLMGateway()
