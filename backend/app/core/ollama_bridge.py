"""Gnosis Ollama Bridge — local-first LLM execution via Ollama."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import httpx


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    timeout: int = 120
    available: bool = False


class OllamaBridge:
    """Bridge to local Ollama instance for offline execution."""

    def __init__(self):
        self.config = OllamaConfig()
        self._generation_history: list[dict] = []

    async def check_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                self.config.available = resp.status_code == 200
        except Exception:
            self.config.available = False
        return self.config.available

    async def list_models(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                if resp.status_code == 200:
                    return resp.json().get("models", [])
        except Exception:
            pass
        return []

    async def generate(self, prompt: str, model: str | None = None) -> str:
        use_model = model or self.config.model
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json={"model": use_model, "prompt": prompt, "stream": False},
                )
                if resp.status_code == 200:
                    result = resp.json().get("response", "")
                    self._generation_history.append({
                        "model": use_model,
                        "prompt_len": len(prompt),
                        "response_len": len(result),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    return result
                return f"Error: Ollama returned status {resp.status_code}"
        except Exception as e:
            return f"Error: {e}"

    def get_status(self) -> dict:
        return {
            "base_url": self.config.base_url,
            "default_model": self.config.model,
            "available": self.config.available,
            "generation_count": len(self._generation_history),
        }


ollama_bridge = OllamaBridge()
