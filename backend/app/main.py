from contextlib import asynccontextmanager
import asyncio
import signal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.core.api_docs import get_openapi_config as _get_docs_config
from app.core.cors_config import get_cors_config as _get_cors_config
from app.api import (
    auth,
    agents,
    awakening,
    execute,
    integrations,
    memory,
    oracle,
    standup,
    events,
    llm,
    templates,
    system,
    pipelines,
    schedules,
    files,
    webhook_triggers,
    replay,
    marketplace,
    export_import,
    prompts,
    versions,
    rag,
    sso,
    collaboration,
    knowledge_graph,
    workspaces,
    billing,
    rpa,
    factory,
)
from app.api import security_dashboard, system_control, predictions, realworld
from app.api import swarm as swarm_api, auto_api as auto_api_router, dreams
from app.api import (
    webhooks_config,
    agent_clone,
    execution_cancel,
    bulk_ops,
    agent_health,
)
from app.api import agent_export, sse, onboarding
from app.api import audit, search, dashboard_stats, retries
from app.api import quotas, config_snapshots, tools, activity
from app.api import pii, retention, gdpr, dpa
from app.api import query_analyzer, streaming, redis_metrics
from app.api import debugger, costs, dlq, flamegraph
from app.api import (
    voice_profiles,
    emotions,
    badges,
    preferences,
    persona_inheritance,
    response_templates,
)
from app.api import mood, prompt_compression, drift, waterfall, self_heal, quality
from app.api import (
    annotations,
    approvals,
    explanations,
    collab_edit,
    ab_compare,
    bookmarks,
    voice_input,
    comments,
)
from app.api import consent, residency, compliance_reports, data_flow
from app.api import (
    env_promotion,
    agent_permissions,
    internal_marketplace,
    integration_tokens,
)
from app.api import (
    tutorials,
    sandbox,
    feature_flags,
    changelog,
    recipes,
    nudges,
    commands,
)
from app.api import help as help_api
from app.api import ollama, pwa, docker_export, edge_deploy, bandwidth, inbound_webhooks
from app.api import snapshots as snapshots_api, cli as cli_api
from app.api import (
    memory_prefetch,
    bundle_analysis,
    pool_monitor,
    exec_queue,
    memory_gc,
)
from app.ws import nerve_center, minds_eye
from app.ws.routes import router as ws_execution_router
from app.core.event_wiring import setup_event_wiring
from app.core.security import SecurityMiddleware
from app.core.security_hardened import UltraSecurityMiddleware
from app.core.versioning import APIVersionMiddleware
from app.core.logger import setup_logging, get_logger
from app.core.error_handling import register_error_handlers
from app.core.rate_limiter import require_rate_limit
from app.core.env_validator import validate_environment
# ``scripts/`` lives next to ``app/`` (one level above the package root),
# so ensure it is importable for the startup secret validator.
import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = _Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPTS_DIR))
from scripts.validate_secrets import enforce_no_default_secrets  # noqa: E402
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.body_limit import RequestBodyLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.redis_client import redis_manager
from app.core.scheduler import scheduler_engine
from app.core.task_worker import task_worker
from app.core.database import engine
from app.core.metrics import MetricsMiddleware, metrics_endpoint
from app.core.http_client import init_http_client, close_http_client
from app.core.shutdown import shutdown_manager
from app.core.startup_banner import print_banner
from fastapi import Depends
from app.api import health as health_router_mod
from app.api import aws_status
from app.api import health_check
from app.api import feedback
import app.core.database as _db_mod

settings = get_settings()

# Initialize structured logging
setup_logging(level=settings.log_level)
logger = get_logger("main")


# ---------------------------------------------------------------------------
# Periodic task stubs (safe no-ops that call real engines when available)
# ---------------------------------------------------------------------------


async def _memory_consolidation():
    try:
        from app.core.learning_engine import learning_engine

        await learning_engine.consolidate_memories("system")
    except Exception as e:
        logger.warning(f"memory-consolidation: {e}")


async def _pattern_learning():
    try:
        from app.core.learning_engine import LearningEngine

        le = LearningEngine()
        await le.pattern_learn("system")
    except Exception as e:
        logger.warning(f"pattern-learning: {e}")


async def _oracle_analysis():
    try:
        from app.core.oracle_engine import OracleEngine

        oe = OracleEngine()
        await oe.generate_insights()
    except Exception as e:
        logger.warning(f"oracle-analysis: {e}")


async def _trust_evaluation():
    try:
        from app.core.trust_engine import TrustEngine

        te = TrustEngine()
        await te.evaluate("system", {})
    except Exception as e:
        logger.warning(f"trust-evaluation: {e}")


async def _memory_decay():
    """Periodic task: decay memory strength for all agents."""
    try:
        from app.core.memory_engine import memory_engine

        await memory_engine.decay_all()
    except Exception as e:
        logger.warning(f"memory-decay: {e}")


SHUTDOWN_TIMEOUT = 30

_shutdown_event: asyncio.Event | None = None


def _install_signal_handlers(
    loop: asyncio.AbstractEventLoop, shutdown_ev: asyncio.Event
):
    """Register SIGTERM/SIGINT handlers that trigger graceful shutdown."""

    def _signal_handler(sig, _frame=None):
        logger.info(f"Received signal {sig.name}, triggering graceful shutdown")
        shutdown_ev.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler, sig)
        except (NotImplementedError, RuntimeError):
            # Windows or non-main thread – fall back to signal.signal
            try:
                signal.signal(sig, lambda s, f: _signal_handler(signal.Signals(s)))
            except (OSError, ValueError):
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Install signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    _install_signal_handlers(loop, _shutdown_event)
    shutdown_manager.install_signal_handlers(loop)

    # Startup: initialize connections
    logger.info("◎ Gnosis starting up...")

    # Print startup banner
    print_banner()

    # Log environment configuration before opening connections.
    validate_environment(strict=False)

    # Hard fail-fast guard: refuse to serve if a known default secret is in
    # place in any production-like environment. Must run BEFORE any side
    # effects (DB/Redis connections, background workers, etc.).
    enforce_no_default_secrets(settings)

    # Connect Redis (graceful — never crashes)
    await redis_manager.connect()

    # Shared HTTP client
    await init_http_client()

    # Try to connect to DB, warn if unavailable (don't crash — allow demo mode)
    try:
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        _db_mod.db_available = True
        logger.info("◎ PostgreSQL connected")
    except Exception as e:
        _db_mod.db_available = False
        logger.warning(f"⚠ PostgreSQL unavailable: {e} — running in demo mode")

    setup_event_wiring()
    logger.info("◎ Event bus wired")

    # Register periodic tasks
    task_worker.register("memory-consolidation", _memory_consolidation, 3600)
    task_worker.register("pattern-learning", _pattern_learning, 7200)
    task_worker.register("oracle-analysis", _oracle_analysis, 1800)
    task_worker.register("trust-evaluation", _trust_evaluation, 3600)
    task_worker.register("memory-decay", _memory_decay, 300)  # Run every 5 minutes

    # Start task worker in background
    worker_task = asyncio.create_task(task_worker.start())

    # Start agent scheduler
    await scheduler_engine.start()

    yield

    # Shutdown: cleanup with timeout
    logger.info("◎ Gnosis shutting down...")

    async def _graceful_shutdown():
        # 1. Stop agent scheduler
        await scheduler_engine.stop()
        # 2. Stop task worker
        await task_worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        # 3. Flush metrics (no-op if prometheus_client has nothing to flush)
        try:
            from prometheus_client import REGISTRY  # noqa: F401

            logger.debug("Metrics flushed")
        except Exception:
            logger.warning("Error during shutdown", exc_info=True)
        # 4. Close shared HTTP client
        await close_http_client()
        # 5. Disconnect Redis
        await redis_manager.close()
        # 6. Dispose DB engine
        await engine.dispose()

    try:
        await asyncio.wait_for(_graceful_shutdown(), timeout=SHUTDOWN_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(
            f"Graceful shutdown timed out after {SHUTDOWN_TIMEOUT}s — forcing exit"
        )

    logger.info("◎ Gnosis shutdown complete")


_docs_config = _get_docs_config()
app = FastAPI(
    title=_docs_config["title"],
    description=_docs_config["description"],
    version=_docs_config["version"],
    openapi_tags=_docs_config["openapi_tags"],
    docs_url=_docs_config["docs_url"],
    redoc_url=_docs_config["redoc_url"],
    lifespan=lifespan,
)

# Register global error handlers
register_error_handlers(app)

# Response compression (added before CORS so responses are compressed)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS (configurable via CORS_ORIGINS env var)
_cors = _get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors["allow_origins"],
    allow_credentials=_cors["allow_credentials"],
    allow_methods=_cors["allow_methods"],
    allow_headers=_cors["allow_headers"],
    expose_headers=_cors["expose_headers"],
)

# Security middleware (hardened layer + original)
app.add_middleware(UltraSecurityMiddleware, settings=settings)
app.add_middleware(SecurityMiddleware, rate_limit=100)

# Baseline HTTP security headers (HSTS, CSP, X-Frame-Options, ...)
app.add_middleware(SecurityHeadersMiddleware)

# Request body size limit (10MB default)
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=10 * 1024 * 1024)

# API versioning middleware
app.add_middleware(APIVersionMiddleware)

# Rate-limited dependencies for high-traffic routers
_rl = [Depends(require_rate_limit)]

# REST API routes
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(
    agents.router,
    prefix=f"{settings.api_prefix}/agents",
    tags=["agents"],
    dependencies=_rl,
)
app.include_router(
    awakening.router,
    prefix=f"{settings.api_prefix}/awaken",
    tags=["awakening"],
    dependencies=_rl,
)
app.include_router(
    execute.router,
    prefix=f"{settings.api_prefix}/execute",
    tags=["execute"],
    dependencies=_rl,
)
app.include_router(
    integrations.router,
    prefix=f"{settings.api_prefix}/integrations",
    tags=["integrations"],
    dependencies=_rl,
)
app.include_router(
    memory.router,
    prefix=f"{settings.api_prefix}/memory",
    tags=["memory"],
    dependencies=_rl,
)
app.include_router(
    oracle.router,
    prefix=f"{settings.api_prefix}/oracle",
    tags=["oracle"],
    dependencies=_rl,
)
app.include_router(
    standup.router,
    prefix=f"{settings.api_prefix}/standup",
    tags=["standup"],
    dependencies=_rl,
)

app.include_router(
    templates.router, prefix=f"{settings.api_prefix}/templates", tags=["templates"]
)
app.include_router(
    events.router, prefix=f"{settings.api_prefix}/events", tags=["events"]
)
app.include_router(
    llm.router, prefix=f"{settings.api_prefix}/llm", tags=["llm"], dependencies=_rl
)
app.include_router(
    system.router, prefix=f"{settings.api_prefix}/system", tags=["system"]
)
app.include_router(
    schedules.router, prefix=f"{settings.api_prefix}/schedules", dependencies=_rl
)
app.include_router(
    pipelines.router, prefix=f"{settings.api_prefix}/pipelines", dependencies=_rl
)

app.include_router(
    files.router, prefix=f"{settings.api_prefix}/files", dependencies=_rl
)
app.include_router(
    webhook_triggers.router,
    prefix=f"{settings.api_prefix}/webhook-triggers",
    dependencies=_rl,
)
app.include_router(
    replay.router, prefix=f"{settings.api_prefix}/replay", dependencies=_rl
)

app.include_router(
    marketplace.router, prefix=f"{settings.api_prefix}/marketplace", dependencies=_rl
)
app.include_router(
    export_import.router,
    prefix=f"{settings.api_prefix}/export-import",
    dependencies=_rl,
)
app.include_router(
    prompts.router, prefix=f"{settings.api_prefix}/prompts", dependencies=_rl
)
app.include_router(
    versions.router, prefix=f"{settings.api_prefix}/versions", dependencies=_rl
)

app.include_router(rag.router, prefix=f"{settings.api_prefix}/rag", dependencies=_rl)

app.include_router(
    workspaces.router, prefix=f"{settings.api_prefix}/workspaces", dependencies=_rl
)
app.include_router(
    billing.router, prefix=f"{settings.api_prefix}/billing", dependencies=_rl
)

app.include_router(collaboration.router, dependencies=_rl)
app.include_router(knowledge_graph.router, dependencies=_rl)
app.include_router(sso.router)

app.include_router(rpa.router, dependencies=_rl)

app.include_router(factory.router, dependencies=_rl)

app.include_router(
    aws_status.router, prefix=f"{settings.api_prefix}/aws-status", dependencies=_rl
)

app.include_router(
    security_dashboard.router,
    prefix=f"{settings.api_prefix}/security",
    dependencies=_rl,
)

app.include_router(dreams.router, dependencies=_rl)

app.include_router(
    system_control.router,
    prefix=f"{settings.api_prefix}/system-control",
    tags=["system-control"],
)

app.include_router(predictions.router, tags=["predictions"], dependencies=_rl)
app.include_router(realworld.router, tags=["realworld"], dependencies=_rl)

app.include_router(swarm_api.router, dependencies=_rl)
app.include_router(
    auto_api_router.router, prefix=f"{settings.api_prefix}/auto-api", dependencies=_rl
)

# New feature routers
app.include_router(webhooks_config.router, dependencies=_rl)
app.include_router(agent_clone.router, dependencies=_rl)
app.include_router(execution_cancel.router, dependencies=_rl)
app.include_router(bulk_ops.router, dependencies=_rl)
app.include_router(agent_health.router, dependencies=_rl)
app.include_router(agent_export.router, dependencies=_rl)
app.include_router(sse.router, dependencies=_rl)
app.include_router(onboarding.router, dependencies=_rl)

# Governance & Compliance
app.include_router(quotas.router, dependencies=_rl)
app.include_router(config_snapshots.router, dependencies=_rl)
app.include_router(tools.router, dependencies=_rl)
app.include_router(activity.router, dependencies=_rl)
app.include_router(pii.router, dependencies=_rl)
app.include_router(retention.router, dependencies=_rl)
app.include_router(gdpr.router, dependencies=_rl)
app.include_router(dpa.router, dependencies=_rl)

# Observability & Performance
app.include_router(query_analyzer.router, dependencies=_rl)
app.include_router(streaming.router, dependencies=_rl)
app.include_router(redis_metrics.router, dependencies=_rl)
app.include_router(debugger.router, dependencies=_rl)
app.include_router(costs.router, dependencies=_rl)
app.include_router(dlq.router, dependencies=_rl)
app.include_router(flamegraph.router, dependencies=_rl)

# Persona & Agent Behavior
app.include_router(voice_profiles.router, dependencies=_rl)
app.include_router(emotions.router, dependencies=_rl)
app.include_router(
    badges.router, prefix=f"{settings.api_prefix}/badges", dependencies=_rl
)
app.include_router(
    preferences.router, prefix=f"{settings.api_prefix}/preferences", dependencies=_rl
)
app.include_router(
    persona_inheritance.router,
    prefix=f"{settings.api_prefix}/persona-inheritance",
    dependencies=_rl,
)
app.include_router(
    response_templates.router,
    prefix=f"{settings.api_prefix}/response-templates",
    dependencies=_rl,
)
app.include_router(mood.router, dependencies=_rl)
app.include_router(prompt_compression.router, dependencies=_rl)

# Observability Extensions
app.include_router(drift.router, dependencies=_rl)
app.include_router(waterfall.router, dependencies=_rl)
app.include_router(self_heal.router, dependencies=_rl)
app.include_router(quality.router, dependencies=_rl)

# Hi-Impact Features
app.include_router(audit.router, dependencies=_rl)
app.include_router(
    search.router, prefix=f"{settings.api_prefix}/search", dependencies=_rl
)
app.include_router(dashboard_stats.router, dependencies=_rl)
app.include_router(
    retries.router, prefix=f"{settings.api_prefix}/retries", dependencies=_rl
)

# Collaboration
app.include_router(annotations.router, dependencies=_rl)
app.include_router(approvals.router, dependencies=_rl)
app.include_router(explanations.router, dependencies=_rl)
app.include_router(collab_edit.router, dependencies=_rl)
app.include_router(
    ab_compare.router, prefix=f"{settings.api_prefix}/ab-compare", dependencies=_rl
)
app.include_router(
    bookmarks.router, prefix=f"{settings.api_prefix}/bookmarks", dependencies=_rl
)
app.include_router(voice_input.router, dependencies=_rl)
app.include_router(comments.router, dependencies=_rl)

# Compliance Extended
app.include_router(consent.router, dependencies=_rl)
app.include_router(residency.router, dependencies=_rl)
app.include_router(
    compliance_reports.router,
    prefix=f"{settings.api_prefix}/compliance",
    dependencies=_rl,
)
app.include_router(
    data_flow.router, prefix=f"{settings.api_prefix}/data-flow", dependencies=_rl
)

# Governance Extended
app.include_router(env_promotion.router, dependencies=_rl)
app.include_router(agent_permissions.router, dependencies=_rl)
app.include_router(internal_marketplace.router, dependencies=_rl)
app.include_router(integration_tokens.router, dependencies=_rl)

# Growth
app.include_router(
    tutorials.router, prefix=f"{settings.api_prefix}/tutorials", dependencies=_rl
)
app.include_router(sandbox.router, dependencies=_rl)
app.include_router(
    feature_flags.router,
    prefix=f"{settings.api_prefix}/feature-flags",
    dependencies=_rl,
)
app.include_router(
    changelog.router, prefix=f"{settings.api_prefix}/changelog", dependencies=_rl
)
app.include_router(
    recipes.router, prefix=f"{settings.api_prefix}/recipes", dependencies=_rl
)
app.include_router(help_api.router, dependencies=_rl)
app.include_router(
    nudges.router, prefix=f"{settings.api_prefix}/nudges", dependencies=_rl
)
app.include_router(
    commands.router, prefix=f"{settings.api_prefix}/commands", dependencies=_rl
)

# Edge & Deployment
app.include_router(
    ollama.router, prefix=f"{settings.api_prefix}/ollama", dependencies=_rl
)
app.include_router(pwa.router, prefix=f"{settings.api_prefix}/pwa", dependencies=_rl)
app.include_router(
    docker_export.router,
    prefix=f"{settings.api_prefix}/docker-export",
    dependencies=_rl,
)
app.include_router(
    edge_deploy.router, prefix=f"{settings.api_prefix}/edge", dependencies=_rl
)
app.include_router(
    bandwidth.router, prefix=f"{settings.api_prefix}/bandwidth", dependencies=_rl
)
app.include_router(
    inbound_webhooks.router,
    prefix=f"{settings.api_prefix}/inbound-webhooks",
    dependencies=_rl,
)
app.include_router(
    snapshots_api.router, prefix=f"{settings.api_prefix}/snapshots", dependencies=_rl
)
app.include_router(
    cli_api.router, prefix=f"{settings.api_prefix}/cli", dependencies=_rl
)

# Performance Extended
app.include_router(
    memory_prefetch.router,
    prefix=f"{settings.api_prefix}/memory-prefetch",
    dependencies=_rl,
)
app.include_router(
    bundle_analysis.router,
    prefix=f"{settings.api_prefix}/bundle-analysis",
    dependencies=_rl,
)
app.include_router(
    pool_monitor.router, prefix=f"{settings.api_prefix}/pool-monitor", dependencies=_rl
)
app.include_router(
    exec_queue.router, prefix=f"{settings.api_prefix}/exec-queue", dependencies=_rl
)
app.include_router(
    memory_gc.router, prefix=f"{settings.api_prefix}/memory-gc", dependencies=_rl
)

# WebSocket routes
app.include_router(nerve_center.router, tags=["ws"])
app.include_router(minds_eye.router, tags=["ws"])
app.include_router(ws_execution_router, tags=["ws"])


# Prometheus metrics
app.add_middleware(MetricsMiddleware)

# Request-ID tracing (added last so it wraps everything — runs first)
app.add_middleware(RequestIDMiddleware)

app.add_route("/metrics", metrics_endpoint)

# Health check routes — NO rate limiting (must remain available for k8s probes)
app.include_router(health_router_mod.router, tags=["health"])
app.include_router(
    health_router_mod.router, prefix=settings.api_prefix, tags=["health"]
)
app.include_router(health_check.router)
app.include_router(feedback.router)
