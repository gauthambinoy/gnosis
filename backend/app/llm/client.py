"""
Universal LLM Gateway — supports any provider.
All Gnosis code calls this gateway, never providers directly.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass
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


class OpenRouterProvider(LLMProvider):
    """200+ models via OpenRouter."""

    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
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
            ) as resp:
                async for line in resp.content:
                    text = line.decode().strip()
                    if text.startswith("data: ") and text != "data: [DONE]":
                        import json
                        chunk = json.loads(text[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        import json
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4  # rough estimate

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * 0.003 + output_tokens * 0.015) / 1000


class AnthropicProvider(LLMProvider):
    """Direct Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
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
            ) as resp:
                async for line in resp.content:
                    text = line.decode().strip()
                    if text.startswith("data: "):
                        import json
                        try:
                            chunk = json.loads(text[6:])
                            if chunk.get("type") == "content_block_delta":
                                yield chunk["delta"].get("text", "")
                        except (json.JSONDecodeError, KeyError):
                            pass

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        import json
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
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
            ) as resp:
                async for line in resp.content:
                    text = line.decode().strip()
                    if text:
                        import json
                        try:
                            chunk = json.loads(text)
                            if content := chunk.get("message", {}).get("content"):
                                yield content
                        except json.JSONDecodeError:
                            pass

    async def complete_json(self, messages: list[dict], schema: dict, **kwargs) -> dict:
        full_response = ""
        async for token in self.complete(messages, **kwargs):
            full_response += token
        import json
        return json.loads(full_response)

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # free!


# Provider registry
PROVIDERS = {
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


class LLMGateway:
    """The single interface all Gnosis code uses."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def configure(self, tier: str, provider_name: str, api_key: str = "", model: str = "", **kwargs):
        """Configure a provider for a reasoning tier."""
        provider_class = PROVIDERS.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")

        init_kwargs = {k: v for k, v in {"api_key": api_key, "model": model, **kwargs}.items() if v}
        self._providers[tier] = provider_class(**init_kwargs)

    async def think(self, tier: str, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Stream a response from the appropriate tier."""
        provider = self._providers.get(tier)
        if not provider:
            raise ValueError(f"No provider configured for tier: {tier}")
        async for token in provider.complete(messages, **kwargs):
            yield token

    async def think_json(self, tier: str, messages: list[dict], schema: dict, **kwargs) -> dict:
        """Get structured JSON response."""
        provider = self._providers.get(tier)
        if not provider:
            raise ValueError(f"No provider configured for tier: {tier}")
        return await provider.complete_json(messages, schema, **kwargs)


# Global gateway instance
gateway = LLMGateway()
