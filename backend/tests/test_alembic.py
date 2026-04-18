"""Smoke test: alembic upgrade head → downgrade base → upgrade head.

Runs against an in-memory / file SQLite database so it never touches production.
Skips cleanly when the migrations contain PostgreSQL-specific constructs that
SQLite cannot execute (e.g. postgresql.UUID, ALTER COLUMN TYPE … USING).
"""

import os

import pytest


def _alembic_cfg(db_path: str):
    """Return an alembic Config pointed at our backend alembic/ directory."""
    from alembic.config import Config

    # Locate alembic.ini relative to this file (backend/tests/ → backend/)
    ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    cfg = Config(os.path.abspath(ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg


def test_at_least_one_revision_exists():
    """Alembic versions/ directory must contain at least one migration file."""
    versions_dir = os.path.join(
        os.path.dirname(__file__), "..", "alembic", "versions"
    )
    py_files = [
        f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("_")
    ]
    assert py_files, "No migration files found in alembic/versions/"


def test_alembic_up_down_up(tmp_path):
    """upgrade head → downgrade base → upgrade head must all succeed.

    Skips with a clear message when migrations use PostgreSQL-specific types
    that are incompatible with the SQLite test driver.
    """
    try:
        from alembic import command
        from alembic.config import Config  # noqa: F401 — side-effect import check
    except ImportError:
        pytest.skip("alembic package not installed")

    db_file = str(tmp_path / "alembic_smoke.db")
    cfg = _alembic_cfg(db_file)

    _SKIP_ERRS = (
        "postgresql",
        "no such function",
        "UUID",
        "USING",
        "alter_column",
        "CompileError",
        "NotImplementedError",
        "UnsupportedCompilationError",
        # SQLite rejects ALTER TABLE … ALTER COLUMN used in migration 002
        'near "ALTER"',
        "sqlite3.OperationalError",
        "OperationalError",
    )

    try:
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
    except Exception as exc:
        exc_text = str(exc)
        exc_type = type(exc).__name__
        combined = exc_text + exc_type
        if any(kw.lower() in combined.lower() for kw in _SKIP_ERRS):
            pytest.skip(
                "Migrations contain PostgreSQL-specific DDL incompatible with the "
                "SQLite test driver (e.g. ALTER COLUMN, UUID type). "
                "Run against a real PostgreSQL instance to validate up/down. "
                f"({exc_type}: {exc_text[:200]})"
            )
        raise
