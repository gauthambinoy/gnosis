"""Memory persistence: add user_id/embedding/expires_at/last_accessed_at + sensory tier.

Revision ID: 005_memory_persistence
Revises: 004_request_audit_log
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005_memory_persistence"
down_revision = "004_request_audit_log"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    # Add 'sensory' to the memorytier enum on PostgreSQL (idempotent).
    if _is_postgres():
        op.execute("ALTER TYPE memorytier ADD VALUE IF NOT EXISTS 'sensory'")

    # Use batch so SQLite can rebuild the table when needed.
    with op.batch_alter_table("memories") as batch:
        batch.add_column(
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True).with_variant(sa.String(36), "sqlite"),
                sa.ForeignKey(
                    "users.id",
                    name="fk_memories_user_id",
                    ondelete="CASCADE",
                ),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("embedding", sa.Text, nullable=True))
        batch.add_column(
            sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        # agent_id becomes nullable (memories may belong to a user only)
        batch.alter_column("agent_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_user_tier", "memories", ["user_id", "tier"])
    op.create_index("ix_memories_created_at", "memories", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_memories_created_at", table_name="memories")
    op.drop_index("ix_memories_user_tier", table_name="memories")
    op.drop_index("ix_memories_user_id", table_name="memories")

    with op.batch_alter_table("memories") as batch:
        batch.alter_column(
            "agent_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False,
        )
        batch.drop_column("expires_at")
        batch.drop_column("last_accessed_at")
        batch.drop_column("embedding")
        batch.drop_column("user_id")

    # Note: removing an enum value in PostgreSQL is non-trivial; leaving
    # 'sensory' in place on downgrade is harmless.
