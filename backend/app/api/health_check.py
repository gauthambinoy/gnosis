"""
Production Health Check Endpoint and Status Model

Provides real-time system health information for:
- Database connectivity
- Redis cache availability
- LLM provider health (OpenRouter, OpenAI, Anthropic)
- Rate limiter status
- Feature flags loaded
"""

from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter
from sqlalchemy import text

from app.core.logger import get_logger
from app.core.error_handling import GnosisException
from app.core.database import get_db
from app.core.redis_client import redis_manager

logger = get_logger("health")

router = APIRouter(prefix="/api/v1", tags=["health"])


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    status: str  # "healthy", "degraded", "unavailable"
    latency_ms: float | None = None
    message: str = ""
    checked_at: str = ""


class HealthResponse(BaseModel):
    """Overall system health response."""
    status: str  # "healthy", "degraded", "unavailable"
    timestamp: str
    components: dict[str, ComponentHealth] = {}
    uptime_seconds: float | None = None


async def check_database() -> ComponentHealth:
    """Check database connectivity."""
    import time
    
    try:
        start = time.time()
        db = get_db()
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        
        return ComponentHealth(
            status="healthy",
            latency_ms=latency,
            message="PostgreSQL responding normally",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(
            status="unavailable",
            message=f"Database connection failed: {type(e).__name__}",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


async def check_redis() -> ComponentHealth:
    """Check Redis cache availability."""
    import time
    
    try:
        start = time.time()
        pong = await redis_manager.ping()
        latency = (time.time() - start) * 1000
        
        if pong:
            return ComponentHealth(
                status="healthy",
                latency_ms=latency,
                message="Redis responding normally",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            return ComponentHealth(
                status="unavailable",
                message="Redis ping failed",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return ComponentHealth(
            status="degraded",
            message=f"Redis unavailable (app degraded): {type(e).__name__}",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


async def check_llm_providers() -> ComponentHealth:
    """Check LLM provider connectivity."""
    import time
    
    try:
        from app.core.llm_gateway import llm_gateway
        
        start = time.time()
        # Quick test: get available models
        models = await llm_gateway.list_models()
        latency = (time.time() - start) * 1000
        
        if models and len(models) > 0:
            return ComponentHealth(
                status="healthy",
                latency_ms=latency,
                message=f"LLM providers available ({len(models)} models)",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            return ComponentHealth(
                status="degraded",
                message="LLM providers partially available",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        logger.warning(f"LLM provider check failed: {e}")
        return ComponentHealth(
            status="degraded",
            message=f"LLM providers unreachable: {type(e).__name__}",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


async def check_rate_limiter() -> ComponentHealth:
    """Check rate limiter status."""
    try:
        from app.core.rate_limiter import rate_limiter
        
        status = await rate_limiter.get_status()
        if status.get("healthy"):
            return ComponentHealth(
                status="healthy",
                message=f"Rate limiter: {status.get('active_keys', 0)} active keys",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            return ComponentHealth(
                status="degraded",
                message="Rate limiter operating in fallback mode",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        logger.warning(f"Rate limiter check failed: {e}")
        return ComponentHealth(
            status="degraded",
            message=f"Rate limiter check failed: {type(e).__name__}",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


async def check_feature_flags() -> ComponentHealth:
    """Check feature flags loaded."""
    try:
        from app.core.feature_flags import feature_flags
        
        flag_count = await feature_flags.count()
        if flag_count > 0:
            return ComponentHealth(
                status="healthy",
                message=f"Feature flags loaded: {flag_count} active",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            return ComponentHealth(
                status="degraded",
                message="No feature flags loaded",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        logger.warning(f"Feature flags check failed: {e}")
        return ComponentHealth(
            status="degraded",
            message=f"Feature flags unavailable: {type(e).__name__}",
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


# PUBLIC: health/liveness/readiness probe required for load balancers and uptime monitors
@router.get("/health")
async def health_simple():
    """Simple health check for load balancers."""
    return {"status": "ok"}


# PUBLIC: health/liveness/readiness probe required for load balancers and uptime monitors
@router.get("/health/detailed")
async def health_detailed() -> HealthResponse:
    """
    Detailed health check with component status.
    
    Returns status of:
    - Database (PostgreSQL)
    - Cache (Redis)
    - LLM providers (OpenRouter, OpenAI, etc.)
    - Rate limiter
    - Feature flags
    
    Overall status is:
    - "healthy" if all components healthy
    - "degraded" if any component degraded but at least 1 working
    - "unavailable" if critical component (database) is down
    """
    import time
    
    start_time = time.time()
    
    # Check all components in parallel
    db_health = await check_database()
    redis_health = await check_redis()
    llm_health = await check_llm_providers()
    rate_limiter_health = await check_rate_limiter()
    flags_health = await check_feature_flags()
    
    components = {
        "database": db_health,
        "cache": redis_health,
        "llm_providers": llm_health,
        "rate_limiter": rate_limiter_health,
        "feature_flags": flags_health,
    }
    
    # Determine overall status
    statuses = [c.status for c in components.values()]
    if "unavailable" in statuses and "database" in [k for k, v in components.items() if v.status == "unavailable"]:
        overall_status = "unavailable"
    elif "unavailable" in statuses:
        overall_status = "degraded"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
        uptime_seconds=time.time() - start_time,
    )


# PUBLIC: health/liveness/readiness probe required for load balancers and uptime monitors
@router.get("/health/live")
async def health_live() -> dict:
    """Liveness probe for Kubernetes."""
    return {"status": "alive"}


# PUBLIC: health/liveness/readiness probe required for load balancers and uptime monitors
@router.get("/health/ready")
async def health_ready() -> dict:
    """
    Readiness probe for Kubernetes.
    
    Returns 200 only if service is ready to accept traffic
    (all critical systems initialized).
    """
    db_health = await check_database()
    if db_health.status == "unavailable":
        raise GnosisException(
            "Service not ready: database unavailable",
            status_code=503,
        )
    
    return {"status": "ready"}
