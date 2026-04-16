"""Persist stateful engine data.

Revision ID: 003_engine_states
Revises: 002_fix_execution_fields
Create Date: 2026-04-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_engine_states"
down_revision = "002_fix_execution_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("engine_name", sa.String(100), nullable=False, index=True),
        sa.Column("entity_id", sa.String(128), nullable=False, index=True),
        sa.Column("group_id", sa.String(128), nullable=True, index=True),
        sa.Column("state_type", sa.String(64), nullable=True, index=True),
        sa.Column("version_number", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("state_json", postgresql.JSON, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("engine_name", "entity_id", name="uq_engine_states_engine_entity"),
    )


def downgrade() -> None:
    op.drop_table("engine_states")
