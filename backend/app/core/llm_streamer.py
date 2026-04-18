"""Gnosis LLM Streamer — Real Server-Sent Events streaming from LLM providers."""
import json
import logging
import time
from typing import AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger("gnosis.llm_streamer")

@dataclass
class StreamMetrics:
    total_streams: int = 0
    active_streams: int = 0
    total_tokens: int = 0
    avg_ttft_ms: float = 0  # Time to first token
    avg_tps: float = 0  # Tokens per second

class LLMStreamer:
    """Provides real SSE streaming from LLM providers."""
    
    def __init__(self):
        self._metrics = StreamMetrics()
        self._active: dict = {}

    async def stream_completion(
        self,
        prompt: str,
        model: str = "openai/gpt-4o-mini",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider: str = "openrouter",
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from an LLM provider as SSE events."""
        
        stream_id = f"stream-{int(time.time() * 1000)}"
        self._metrics.total_streams += 1
        self._metrics.active_streams += 1
        self._active[stream_id] = True
        
        start_time = time.time()
        first_token_time = None
        token_count = 0
        
        try:
            if provider == "openrouter":
                async for chunk in self._stream_openrouter(prompt, model, system_prompt, temperature, max_tokens):
                    if first_token_time is None:
                        first_token_time = time.time()
                    token_count += 1
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk, 'token_index': token_count})}\n\n"
            elif provider == "anthropic":
                async for chunk in self._stream_anthropic(prompt, model, system_prompt, temperature, max_tokens):
                    if first_token_time is None:
                        first_token_time = time.time()
                    token_count += 1
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk, 'token_index': token_count})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'content': f'Unsupported provider: {provider}'})}\n\n"
                return
            
            # Stream completion metrics
            elapsed = time.time() - start_time
            ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
            tps = token_count / elapsed if elapsed > 0 else 0
            
            self._metrics.total_tokens += token_count
            self._metrics.avg_ttft_ms = (self._metrics.avg_ttft_ms * 0.9) + (ttft * 0.1)
            self._metrics.avg_tps = (self._metrics.avg_tps * 0.9) + (tps * 0.1)
            
            yield f"data: {json.dumps({'type': 'done', 'total_tokens': token_count, 'duration_ms': round(elapsed * 1000, 1), 'ttft_ms': round(ttft, 1), 'tps': round(tps, 1)})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            self._metrics.active_streams -= 1
            self._active.pop(stream_id, None)

    async def _stream_openrouter(self, prompt, model, system_prompt, temperature, max_tokens) -> AsyncGenerator[str, None]:
        """Stream from OpenRouter API."""
        import os
        try:
            from app.core.http_client import get_http_client
            client = get_http_client()
        except Exception:
            import httpx
            client = httpx.AsyncClient(timeout=60)
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True},
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def _stream_anthropic(self, prompt, model, system_prompt, temperature, max_tokens) -> AsyncGenerator[str, None]:
        """Stream from Anthropic API."""
        import os
        try:
            from app.core.http_client import get_http_client
            client = get_http_client()
        except Exception:
            import httpx
            client = httpx.AsyncClient(timeout=60)
        
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system_prompt or "You are a helpful assistant.",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": True,
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        event = json.loads(line[6:])
                        if event.get("type") == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                yield text
                    except json.JSONDecodeError:
                        continue

    @property
    def metrics(self) -> dict:
        return {
            "total_streams": self._metrics.total_streams,
            "active_streams": self._metrics.active_streams,
            "total_tokens": self._metrics.total_tokens,
            "avg_ttft_ms": round(self._metrics.avg_ttft_ms, 1),
            "avg_tps": round(self._metrics.avg_tps, 1),
        }

llm_streamer = LLMStreamer()
