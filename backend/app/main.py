from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.config import get_settings
from app.api import auth, agents, awakening, execute, integrations, memory, oracle, standup, events, llm, templates
from app.ws import nerve_center, minds_eye
from app.core.event_wiring import setup_event_wiring
from app.core.security import SecurityMiddleware
from app.core.logger import setup_logging, get_logger
from app.core.error_handlers import register_error_handlers
from app.core.redis_client import redis_manager
from app.core.task_worker import task_worker
from app.core.database import engine
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
        from app.core.learning_engine import learning_engine
        await learning_engine.run_learning_cycle()
    except Exception as e:
        logger.warning(f"pattern-learning: {e}")


async def _oracle_analysis():
    try:
        from app.core.oracle_engine import oracle_engine
        await oracle_engine.run_analysis()
    except Exception as e:
        logger.warning(f"oracle-analysis: {e}")


async def _trust_evaluation():
    try:
        from app.core.trust_engine import trust_engine
        await trust_engine.evaluate_all()
    except Exception as e:
        logger.warning(f"trust-evaluation: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connections
    logger.info("◎ Gnosis starting up...")

    # Connect Redis (graceful — never crashes)
    await redis_manager.connect()

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

    # Start task worker in background
    worker_task = asyncio.create_task(task_worker.start())

    yield

    # Shutdown: cleanup
    logger.info("◎ Gnosis shutting down...")
    await task_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await redis_manager.close()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="The Knowledge That Works — AI Agent Platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# Register global error handlers
register_error_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(SecurityMiddleware, rate_limit=100)

# REST API routes
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(agents.router, prefix=f"{settings.api_prefix}/agents", tags=["agents"])
app.include_router(awakening.router, prefix=f"{settings.api_prefix}/awaken", tags=["awakening"])
app.include_router(execute.router, prefix=f"{settings.api_prefix}/execute", tags=["execute"])
app.include_router(integrations.router, prefix=f"{settings.api_prefix}/integrations", tags=["integrations"])
app.include_router(memory.router, prefix=f"{settings.api_prefix}/memory", tags=["memory"])
app.include_router(oracle.router, prefix=f"{settings.api_prefix}/oracle", tags=["oracle"])
app.include_router(standup.router, prefix=f"{settings.api_prefix}/standup", tags=["standup"])

app.include_router(templates.router, prefix=f"{settings.api_prefix}/templates", tags=["templates"])
app.include_router(events.router, prefix=f"{settings.api_prefix}/events", tags=["events"])
app.include_router(llm.router, prefix=f"{settings.api_prefix}/llm", tags=["llm"])

# WebSocket routes
app.include_router(nerve_center.router, tags=["ws"])
app.include_router(minds_eye.router, tags=["ws"])


@app.get("/health")
async def health():
    return {"status": "alive", "service": "gnosis"}
