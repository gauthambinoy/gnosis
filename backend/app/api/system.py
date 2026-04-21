from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.retry import dlq
from app.core.task_worker import task_worker
from app.core.redis_client import redis_manager
from app.core.queue import task_queue
from app.core.webhooks import webhook_manager
from app.core.db_pool import db_pool_manager
from app.core.rate_limiter import rate_limiter
from app.core.tracing import tracer
from app.core.sentry_integration import error_tracker
from app.core.metrics import (
    ACTIVE_AGENTS,
    ACTIVE_CONNECTIONS,
    MEMORY_VECTORS,
    TASK_WORKER_TASKS,
)

router = APIRouter()


@router.get("/dlq")
async def list_dlq(limit: int = 50, user_id: str = Depends(get_current_user_id)):
    """List dead letter queue items."""
    items = dlq.get_all(limit)
    return {"items": items, "total": len(items)}


@router.post("/dlq/{item_id}/retry")
async def retry_dlq_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    """Retry a DLQ item."""
    item = dlq.retry(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="DLQ item not found")
    return {"status": "retried", "item": item}


@router.get("/status")
async def system_status(user_id: str = Depends(get_current_user_id)):
    """System status: worker tasks, cache stats, connections."""
    return {
        "worker_tasks": task_worker.status(),
        "redis_connected": redis_manager._redis is not None,
        "dlq_size": len(dlq.items),
    }


# --- Task Queue ---


@router.get("/queue/stats")
async def queue_stats(user_id: str = Depends(get_current_user_id)):
    """Distributed task queue statistics."""
    return task_queue.get_stats()


# --- Webhooks ---


class WebhookSubscribeRequest(BaseModel):
    url: str
    events: list[str]
    secret: str | None = None


@router.post("/webhooks")
async def subscribe_webhook(req: WebhookSubscribeRequest, user_id: str = Depends(get_current_user_id)):
    """Subscribe to webhook events."""
    sub = webhook_manager.subscribe(req.url, req.events, req.secret)
    return sub


@router.get("/webhooks")
async def list_webhooks(user_id: str = Depends(get_current_user_id)):
    """List all webhook subscriptions."""
    return webhook_manager.get_subscriptions()


@router.delete("/webhooks/{sub_id}")
async def unsubscribe_webhook(sub_id: str, user_id: str = Depends(get_current_user_id)):
    """Remove a webhook subscription."""
    webhook_manager.unsubscribe(sub_id)
    return {"status": "removed", "id": sub_id}


@router.get("/webhooks/log")
async def webhook_delivery_log(limit: int = 50, user_id: str = Depends(get_current_user_id)):
    """View webhook delivery log."""
    return webhook_manager.get_delivery_log(limit)


# --- DB Pool ---


@router.get("/pool")
async def pool_status(user_id: str = Depends(get_current_user_id)):
    """Database connection pool status."""
    return db_pool_manager.get_pool_status()


# --- Rate Limiter ---


@router.get("/rate-limits")
async def rate_limit_stats(user_id: str = Depends(get_current_user_id)):
    """Rate limiter statistics."""
    return rate_limiter.get_stats()


# --- Observability ---


@router.get("/traces")
async def recent_traces(limit: int = 20, user_id: str = Depends(get_current_user_id)):
    """Recent traces from the lightweight tracer."""
    return {"traces": tracer.get_recent_traces(limit=limit)}


@router.get("/errors")
async def recent_errors(limit: int = 20, user_id: str = Depends(get_current_user_id)):
    """Recent captured errors."""
    return {
        "errors": error_tracker.get_recent(limit=limit),
        "stats": error_tracker.get_stats(),
    }


@router.get("/errors/top")
async def top_errors(limit: int = 10, user_id: str = Depends(get_current_user_id)):
    """Top errors by frequency."""
    return {"top_errors": error_tracker.get_top_errors(limit=limit)}


@router.get("/metrics-summary")
async def metrics_summary(user_id: str = Depends(get_current_user_id)):
    """JSON summary of key Prometheus metrics."""
    return {
        "active_agents": ACTIVE_AGENTS._value.get(),
        "active_ws_connections": ACTIVE_CONNECTIONS._value.get(),
        "memory_vectors": MEMORY_VECTORS._value.get(),
        "task_worker_tasks": TASK_WORKER_TASKS._value.get(),
        "error_stats": error_tracker.get_stats(),
    }
