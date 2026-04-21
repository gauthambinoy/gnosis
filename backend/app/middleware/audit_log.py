"""Request/Response audit logging middleware.

Durability model
----------------
Every captured :class:`AuditRecord` is persisted with the following priority:

1. **Redis** (primary) – ``LPUSH`` + ``LTRIM`` pipeline against the list key
   ``gnosis:audit:requests`` (capped at ``REDIS_LIST_CAP`` = 10 000 entries).
   Writes happen in a fire-and-forget background task so the request path
   never blocks on Redis.
2. **Database** (fallback) – if Redis is unavailable the same background task
   inserts into the ``request_audit_log`` table.
3. **In-memory deque** – retained only as a fast tail-read cache for the
   currently running process. It is **not** a source of truth.

Redis outages never raise from the request path – failures are caught,
logged at warning level, and the request is served normally.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import get_settings

logger = logging.getLogger("gnosis.audit")
_settings = get_settings()

#: Redis list key holding JSON-serialised :class:`AuditRecord` entries.
REDIS_LIST_KEY = "gnosis:audit:requests"
#: Maximum entries retained in Redis before ``LTRIM`` drops the oldest.
REDIS_LIST_CAP = 10_000


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
    """Durable, best-effort audit buffer.

    Writes are persisted to Redis first (bounded list) and fall back to the
    ``request_audit_log`` table when Redis is unavailable. A small in-process
    deque is kept purely as a fast tail-read cache – never as the source of
    truth.
    """

    def __init__(self, max_records: int = 1000):
        # Tail cache – *not* durable. Used for quick reads and for the stats
        # counters exposed on this process.
        self._records: deque = deque(maxlen=max_records)
        self._stats = {"total_requests": 0, "total_errors": 0, "total_latency_ms": 0}
        self._background_tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    def add(self, record: AuditRecord) -> None:
        """Record an audit entry.

        Always updates the in-memory tail cache synchronously, then schedules
        a background task that persists the entry to Redis (primary) or the
        database (fallback). Safe to call from inside the request path –
        never blocks on I/O.
        """
        self._records.append(record)
        self._stats["total_requests"] += 1
        self._stats["total_latency_ms"] += record.latency_ms
        if record.status_code >= 400:
            self._stats["total_errors"] += 1

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop – running from a sync context (e.g. a test that
            # constructs the store directly). Persistence must still be
            # best-effort so we simply skip remote persistence here; callers
            # may invoke :meth:`persist` explicitly.
            return

        task = loop.create_task(self.persist(record))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def persist(self, record: AuditRecord) -> str:
        """Persist a single record. Returns the backend that accepted it.

        Return value is one of ``"redis"``, ``"db"`` or ``"none"``. Never
        raises – persistence failures are logged and swallowed.
        """
        payload = json.dumps(asdict(record), separators=(",", ":"))

        # Primary: Redis
        try:
            from app.core.redis_client import redis_manager

            client = redis_manager.client
            if client is not None:
                pipe = client.pipeline()
                pipe.lpush(REDIS_LIST_KEY, payload)
                pipe.ltrim(REDIS_LIST_KEY, 0, REDIS_LIST_CAP - 1)
                await pipe.execute()
                return "redis"
        except Exception as exc:  # pragma: no cover - logged path
            logger.warning(
                "audit.redis_write_failed request_id=%s path=%s error=%r",
                record.id,
                record.path,
                exc,
            )

        # Fallback: database
        try:
            return await self._persist_db(record)
        except Exception as exc:  # pragma: no cover - logged path
            logger.warning(
                "audit.db_write_failed request_id=%s path=%s error=%r",
                record.id,
                record.path,
                exc,
            )
            return "none"

    async def _persist_db(self, record: AuditRecord) -> str:
        from app.core.database import async_session_factory
        from app.models.audit import RequestAuditLog

        ts = None
        if record.timestamp:
            try:
                ts = datetime.fromisoformat(record.timestamp)
            except ValueError:
                ts = None

        async with async_session_factory() as session:
            row = RequestAuditLog(
                request_id=record.id or "",
                timestamp=ts or datetime.now(timezone.utc),
                method=record.method,
                path=record.path[:512],
                status_code=record.status_code,
                latency_ms=float(record.latency_ms or 0),
                user_id=record.user_id or None,
                ip_address=record.ip_address or None,
                user_agent=(record.user_agent or None) and record.user_agent[:256],
                request_size=int(record.request_size or 0),
                response_size=int(record.response_size or 0),
            )
            session.add(row)
            await session.commit()
        return "db"

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------
    async def recent(
        self,
        limit: int = 50,
        path_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
    ) -> List[dict]:
        """Return up to ``limit`` most-recent audit records (newest first).

        Reads from Redis first, then falls back to the database, then to the
        in-memory tail cache. The same filtering semantics are applied
        regardless of backend.
        """
        method_norm = method_filter.upper() if method_filter else None

        # Primary: Redis
        try:
            from app.core.redis_client import redis_manager

            client = redis_manager.client
            if client is not None:
                # Fetch a generous window, then filter + cap client-side so
                # filters behave identically to the DB / deque paths.
                raw = await client.lrange(REDIS_LIST_KEY, 0, REDIS_LIST_CAP - 1)
                out: List[dict] = []
                for item in raw:
                    try:
                        rec = json.loads(item)
                    except (TypeError, ValueError):
                        continue
                    if path_filter and path_filter not in rec.get("path", ""):
                        continue
                    if method_norm and rec.get("method") != method_norm:
                        continue
                    out.append(rec)
                    if len(out) >= limit:
                        break
                return out
        except Exception as exc:  # pragma: no cover - logged path
            logger.warning("audit.redis_read_failed error=%r", exc)

        # Fallback: database
        try:
            return await self._read_db(limit, path_filter, method_norm)
        except Exception as exc:  # pragma: no cover - logged path
            logger.warning("audit.db_read_failed error=%r", exc)

        # Last resort: in-memory tail cache
        records = list(self._records)
        if path_filter:
            records = [r for r in records if path_filter in r.path]
        if method_norm:
            records = [r for r in records if r.method == method_norm]
        return [asdict(r) for r in records[-limit:]][::-1]

    async def _read_db(
        self, limit: int, path_filter: Optional[str], method_norm: Optional[str]
    ) -> List[dict]:
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.audit import RequestAuditLog

        stmt = select(RequestAuditLog).order_by(RequestAuditLog.timestamp.desc())
        if path_filter:
            stmt = stmt.where(RequestAuditLog.path.like(f"%{path_filter}%"))
        if method_norm:
            stmt = stmt.where(RequestAuditLog.method == method_norm)
        stmt = stmt.limit(limit)

        async with async_session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "id": r.request_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "latency_ms": r.latency_ms,
                "user_id": r.user_id or "",
                "ip_address": r.ip_address or "",
                "user_agent": r.user_agent or "",
                "request_size": r.request_size,
                "response_size": r.response_size,
            }
            for r in rows
        ]

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


async def recent_audit_records(
    limit: int = 50,
    path_filter: Optional[str] = None,
    method_filter: Optional[str] = None,
) -> List[dict]:
    """Module-level readback helper (Redis → DB → in-memory)."""
    return await audit_store.recent(
        limit=limit, path_filter=path_filter, method_filter=method_filter
    )


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

                payload = jwt.decode(
                    auth[7:],
                    _settings.secret_key,
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                user_id = payload.get("sub", "")
            except Exception:
                pass

        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else ""
        )

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
        try:
            audit_store.add(record)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit.add_failed error=%r", exc)

        # Log slow requests
        if latency > 1000:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {latency:.0f}ms"
            )

        response.headers["X-Request-ID"] = request_id
        return response
