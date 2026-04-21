"""Durable fallback table for request audit middleware.

Revision ID: 004_request_audit_log
Revises: 003_engine_states
Create Date: 2026-04-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_request_audit_log"
down_revision = "003_engine_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=False, index=True),
        sa.Column("status_code", sa.Integer, nullable=False, index=True),
        sa.Column("latency_ms", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("user_id", sa.String(128), nullable=True, index=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(256), nullable=True),
        sa.Column(
            "request_size", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "response_size", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("request_audit_log")
