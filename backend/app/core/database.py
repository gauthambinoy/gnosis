from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from app.config import get_settings
from app.core.logger import get_logger

settings = get_settings()
_logger = get_logger("database")

_is_real_db = not settings.database_url.startswith("sqlite")

_pool_kwargs: dict = {}
if _is_real_db:
    _pool_kwargs = dict(
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

engine = create_async_engine(
    settings.database_url,
    echo=False,
    **_pool_kwargs,
)

# Debug-level pool event listeners (only for real pooled engines)
if _is_real_db and settings.debug:
    _sync_engine = engine.sync_engine

    @event.listens_for(_sync_engine, "checkout")
    def _on_checkout(dbapi_conn, connection_record, connection_proxy):
        _logger.debug("Pool checkout: %s", id(dbapi_conn))

    @event.listens_for(_sync_engine, "checkin")
    def _on_checkin(dbapi_conn, connection_record):
        _logger.debug("Pool checkin: %s", id(dbapi_conn))

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Flag set at startup: True if PostgreSQL is reachable
db_available: bool = False


async def get_db() -> AsyncSession:
    """FastAPI dependency for DB sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
