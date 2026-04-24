"""Gnosis API Client — Typed Python SDK for all Gnosis endpoints."""
import logging
import random
import time
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed error hierarchy
# ---------------------------------------------------------------------------


class GnosisError(Exception):
    """Base error raised for any non-2xx response from the Gnosis API."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Gnosis API Error {status_code}: {detail}")


class GnosisAuthError(GnosisError):
    """401/403 — credentials missing, invalid, or insufficient."""


class GnosisNotFoundError(GnosisError):
    """404 — resource does not exist."""


class GnosisRateLimitError(GnosisError):
    """429 — client should back off and retry."""

    def __init__(self, status_code: int, detail: Any, retry_after: Optional[float] = None):
        super().__init__(status_code, detail)
        self.retry_after = retry_after


class GnosisServerError(GnosisError):
    """5xx — transient backend issue; safe to retry idempotent calls."""


class GnosisNetworkError(GnosisError):
    """Transport-level failure (DNS, refused, timeout)."""

    def __init__(self, detail: Any):
        super().__init__(0, detail)


# Status codes worth retrying for idempotent verbs (GET/HEAD/PUT/DELETE).
# POST/PATCH are NOT retried by default — they may not be idempotent.
_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_IDEMPOTENT_VERBS = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}


def _classify(status: int, detail: Any, response: Optional[httpx.Response] = None) -> GnosisError:
    if status in (401, 403):
        return GnosisAuthError(status, detail)
    if status == 404:
        return GnosisNotFoundError(status, detail)
    if status == 429:
        retry_after: Optional[float] = None
        if response is not None:
            ra = response.headers.get("Retry-After")
            if ra:
                try:
                    retry_after = float(ra)
                except ValueError:
                    pass
        return GnosisRateLimitError(status, detail, retry_after=retry_after)
    if status >= 500:
        return GnosisServerError(status, detail)
    return GnosisError(status, detail)


class GnosisClient:
    """Python SDK for the Gnosis AI Agent Platform.

    Network failures and 429/5xx responses on idempotent verbs are retried
    automatically with exponential backoff + full jitter. Configure via
    constructor kwargs:

        GnosisClient(
            "http://localhost:8000",
            max_retries=3,
            backoff_base=0.5,
            backoff_max=10.0,
            timeout=30.0,
        )

    Usage:
        client = GnosisClient("http://localhost:8000")
        client.login("user@example.com", "password")
        agent = client.create_agent("My Agent", "You are a helpful assistant")
        result = client.execute_agent(agent["id"], "Summarize my emails")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout)
        self._max_retries = max(0, int(max_retries))
        self._backoff_base = max(0.0, float(backoff_base))
        self._backoff_max = max(self._backoff_base, float(backoff_max))

    # Allow `with GnosisClient(...) as c:` use.
    def __enter__(self) -> "GnosisClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _sleep_for_attempt(self, attempt: int, hint: Optional[float] = None) -> None:
        """Exponential backoff with full jitter; respects server Retry-After."""
        if hint is not None and hint > 0:
            time.sleep(min(hint, self._backoff_max))
            return
        cap = min(self._backoff_max, self._backoff_base * (2**attempt))
        time.sleep(random.uniform(0, cap))

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        verb = method.upper()
        last_error: Optional[Exception] = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.request(
                    verb, url, headers=self._headers(), **kwargs
                )
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.NetworkError,
            ) as exc:
                last_error = GnosisNetworkError(repr(exc))
                if verb in _IDEMPOTENT_VERBS and attempt < attempts - 1:
                    logger.warning(
                        "gnosis_sdk.network_retry attempt=%s/%s url=%s err=%r",
                        attempt + 1, attempts, url, exc,
                    )
                    self._sleep_for_attempt(attempt)
                    continue
                raise last_error from exc

            if response.status_code < 400:
                if response.status_code == 204 or not response.content:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text

            # Error response
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            err = _classify(response.status_code, detail, response)
            should_retry = (
                attempt < attempts - 1
                and response.status_code in _RETRY_STATUSES
                and verb in _IDEMPOTENT_VERBS
            )
            if should_retry:
                hint = getattr(err, "retry_after", None)
                logger.warning(
                    "gnosis_sdk.status_retry attempt=%s/%s status=%s url=%s",
                    attempt + 1, attempts, response.status_code, url,
                )
                self._sleep_for_attempt(attempt, hint=hint)
                last_error = err
                continue
            raise err

        # Loop exhausted (should be unreachable — defensive).
        assert last_error is not None
        raise last_error

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
