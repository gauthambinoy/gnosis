"""Request/Response audit logging middleware."""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from dataclasses import dataclass, asdict
from typing import List
from datetime import datetime, timezone
from collections import deque
from app.config import get_settings

logger = logging.getLogger("gnosis.audit")
_settings = get_settings()

@dataclass
class AuditRecord:
    id: str = ""
    timestamp: str = ""
    method: str = ""
    path: str = ""
    status_code: int = 0
    latency_ms: float = 0
    user_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    request_size: int = 0
    response_size: int = 0

class AuditStore:
    """In-memory circular buffer for audit records."""
    def __init__(self, max_records: int = 10000):
        self._records: deque = deque(maxlen=max_records)
        self._stats = {"total_requests": 0, "total_errors": 0, "total_latency_ms": 0}

    def add(self, record: AuditRecord):
        self._records.append(record)
        self._stats["total_requests"] += 1
        self._stats["total_latency_ms"] += record.latency_ms
        if record.status_code >= 400:
            self._stats["total_errors"] += 1

    def recent(self, limit: int = 50, path_filter: str = None, method_filter: str = None) -> List[dict]:
        records = list(self._records)
        if path_filter:
            records = [r for r in records if path_filter in r.path]
        if method_filter:
            records = [r for r in records if r.method == method_filter.upper()]
        return [asdict(r) for r in records[-limit:]][::-1]

    @property
    def stats(self) -> dict:
        total = self._stats["total_requests"]
        return {
            **self._stats,
            "avg_latency_ms": round(self._stats["total_latency_ms"] / max(total, 1), 2),
            "error_rate": round(self._stats["total_errors"] / max(total, 1) * 100, 2),
            "buffer_size": len(self._records),
        }

audit_store = AuditStore()

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip noisy endpoints
        if request.url.path in (
            "/health",
            "/health/ready",
            "/health/live",
            "/health/detailed",
            f"{_settings.api_prefix}/health",
            f"{_settings.api_prefix}/health/ready",
            f"{_settings.api_prefix}/health/live",
            f"{_settings.api_prefix}/health/detailed",
            "/metrics",
        ):
            return await call_next(request)

        start = time.time()
        request_id = str(uuid.uuid4())[:8]

        # Extract user info
        auth = request.headers.get("authorization", "")
        user_id = ""
        if auth.startswith("Bearer "):
            try:
                from jose import jwt
                payload = jwt.decode(auth[7:], _settings.secret_key, algorithms=["HS256"], options={"verify_exp": False})
                user_id = payload.get("sub", "")
            except Exception:
                pass

        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")

        response = await call_next(request)
        latency = (time.time() - start) * 1000

        record = AuditRecord(
            id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency, 2),
            user_id=user_id,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", "")[:200],
            request_size=int(request.headers.get("content-length", 0)),
        )
        audit_store.add(record)

        # Log slow requests
        if latency > 1000:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {latency:.0f}ms")

        response.headers["X-Request-ID"] = request_id
        return response
