"""Gnosis API Client — Typed Python SDK for all Gnosis endpoints."""
import httpx
from typing import Optional, Dict, Any, List


class GnosisError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Gnosis API Error {status_code}: {detail}")


class GnosisClient:
    """Python SDK for the Gnosis AI Agent Platform.

    Usage:
        client = GnosisClient("http://localhost:8000")
        client.login("user@example.com", "password")

        # Create an agent
        agent = client.create_agent("My Agent", "You are a helpful assistant")

        # Execute it
        result = client.execute_agent(agent["id"], "Summarize my emails")
    """

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._api_key = api_key
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        response = self._client.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise GnosisError(response.status_code, detail)
        return response.json()

    def _get(self, path: str, **params) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict = None) -> Any:
        return self._request("POST", path, json=data or {})

    def _patch(self, path: str, data: dict) -> Any:
        return self._request("PATCH", path, json=data)

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # ── Auth ─────────────────────────────────────────────────────

    def register(self, email: str, password: str, name: str = "") -> dict:
        return self._post("/api/v1/auth/register", {"email": email, "password": password, "name": name})

    def login(self, email: str, password: str) -> dict:
        result = self._post("/api/v1/auth/login", {"email": email, "password": password})
        self._token = result.get("access_token")
        return result

    def logout(self):
        self._token = None

    # ── Agents ───────────────────────────────────────────────────

    def create_agent(self, name: str, persona: str, **kwargs) -> dict:
        data = {"name": name, "persona": persona, **kwargs}
        return self._post("/api/v1/agents", data)

    def list_agents(self) -> dict:
        return self._get("/api/v1/agents")

    def get_agent(self, agent_id: str) -> dict:
        return self._get(f"/api/v1/agents/{agent_id}")

    def update_agent(self, agent_id: str, **kwargs) -> dict:
        return self._patch(f"/api/v1/agents/{agent_id}", kwargs)

    def delete_agent(self, agent_id: str) -> dict:
        return self._delete(f"/api/v1/agents/{agent_id}")

    def execute_agent(self, agent_id: str, task: str) -> dict:
        return self._post(f"/api/v1/agents/{agent_id}/execute", {"task": task})

    def correct_agent(self, agent_id: str, correction: str, context: str = "") -> dict:
        return self._post(f"/api/v1/agents/{agent_id}/correct", {"correction": correction, "context": context})

    # ── Memory ───────────────────────────────────────────────────

    def store_memory(self, agent_id: str, content: str, tier: str = "semantic") -> dict:
        return self._post(f"/api/v1/memory/{agent_id}/store", {"content": content, "tier": tier})

    def search_memory(self, agent_id: str, query: str) -> dict:
        return self._get(f"/api/v1/memory/{agent_id}/search", query=query)

    def get_memory_stats(self, agent_id: str) -> dict:
        return self._get(f"/api/v1/memory/{agent_id}/stats")

    # ── Pipelines ────────────────────────────────────────────────

    def create_pipeline(self, name: str, description: str = "", steps: list = None) -> dict:
        return self._post("/api/v1/pipelines", {"name": name, "description": description, "steps": steps or []})

    def execute_pipeline(self, pipeline_id: str, input_data: dict = None) -> dict:
        return self._post(f"/api/v1/pipelines/{pipeline_id}/execute", {"input_data": input_data or {}})

    def list_pipelines(self) -> dict:
        return self._get("/api/v1/pipelines")

    # ── Schedules ────────────────────────────────────────────────

    def create_schedule(self, agent_id: str, name: str, cron: str, **kwargs) -> dict:
        return self._post("/api/v1/schedules", {"agent_id": agent_id, "name": name, "cron_expression": cron, **kwargs})

    def list_schedules(self, agent_id: str = None) -> dict:
        params = {"agent_id": agent_id} if agent_id else {}
        return self._get("/api/v1/schedules", **params)

    # ── RAG ──────────────────────────────────────────────────────

    def ingest_document(self, name: str, content: str, agent_id: str = None) -> dict:
        return self._post("/api/v1/rag/ingest/text", {"name": name, "content": content, "agent_id": agent_id})

    def search_documents(self, query: str, agent_id: str = None, top_k: int = 5) -> dict:
        return self._post("/api/v1/rag/search", {"query": query, "agent_id": agent_id, "top_k": top_k})

    # ── Marketplace ──────────────────────────────────────────────

    def browse_marketplace(self, category: str = None, search: str = None) -> dict:
        params = {}
        if category: params["category"] = category
        if search: params["search"] = search
        return self._get("/api/v1/marketplace/browse", **params)

    def clone_from_marketplace(self, marketplace_agent_id: str) -> dict:
        return self._post(f"/api/v1/marketplace/{marketplace_agent_id}/clone")

    # ── Health ───────────────────────────────────────────────────

    def health(self) -> dict:
        return self._get("/health")

    def health_ready(self) -> dict:
        return self._get("/health/ready")

    # ── Collaboration ────────────────────────────────────────────

    def create_room(self, name: str, topic: str, agent_ids: list) -> dict:
        return self._post("/api/v1/collaboration/rooms", {"name": name, "topic": topic, "agent_ids": agent_ids})

    def run_discussion(self, room_id: str) -> dict:
        return self._post(f"/api/v1/collaboration/rooms/{room_id}/discuss")

    # ── Export/Import ────────────────────────────────────────────

    def export_agent(self, agent_id: str) -> dict:
        return self._get(f"/api/v1/agents/{agent_id}/export")

    def import_agent(self, data: dict) -> dict:
        return self._post("/api/v1/agents/import", data)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
