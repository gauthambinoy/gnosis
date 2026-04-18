"""Initial migration — create all tables.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column(
            "is_active", sa.Boolean, server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "is_verified", sa.Boolean, server_default=sa.text("false"), nullable=False
        ),
        sa.Column("llm_provider", sa.String(50), server_default="openrouter"),
        sa.Column("llm_config", postgresql.JSON, server_default="{}"),
        sa.Column("llm_preset", sa.String(20), server_default="balanced"),
        sa.Column("total_tokens_used", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- agents ---
    agent_status = postgresql.ENUM(
        "active",
        "idle",
        "paused",
        "error",
        "learning",
        name="agentstatus",
        create_type=True,
    )
    agent_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("personality", sa.String(50), server_default="professional"),
        sa.Column("avatar_emoji", sa.String(10), server_default="◎"),
        sa.Column("trigger_type", sa.String(50), server_default="manual"),
        sa.Column("trigger_config", postgresql.JSON, server_default="{}"),
        sa.Column("steps", postgresql.JSON, server_default="[]"),
        sa.Column("integrations", postgresql.JSON, server_default="[]"),
        sa.Column("guardrails", postgresql.JSON, server_default="[]"),
        sa.Column("status", agent_status, server_default="idle", nullable=False),
        sa.Column("trust_level", sa.Integer, server_default="0"),
        sa.Column("total_executions", sa.Integer, server_default="0"),
        sa.Column("successful_executions", sa.Integer, server_default="0"),
        sa.Column("failed_executions", sa.Integer, server_default="0"),
        sa.Column("total_corrections", sa.Integer, server_default="0"),
        sa.Column("accuracy", sa.Float, server_default="0.0"),
        sa.Column("avg_latency_ms", sa.Float, server_default="0.0"),
        sa.Column("total_tokens_used", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, server_default="0.0"),
        sa.Column("time_saved_minutes", sa.Float, server_default="0.0"),
        sa.Column("last_learned_at", sa.String, nullable=True),
        sa.Column("memory_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- executions ---
    exec_status = postgresql.ENUM(
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "awaiting_approval",
        name="executionstatus",
        create_type=True,
    )
    exec_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("trigger_data", postgresql.JSON, server_default="{}"),
        sa.Column("status", exec_status, server_default="queued", nullable=False),
        sa.Column("steps", postgresql.JSON, server_default="[]"),
        sa.Column("result_summary", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("total_latency_ms", sa.Float, server_default="0.0"),
        sa.Column("total_tokens", sa.Integer, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, server_default="0.0"),
        sa.Column("reasoning_tier", sa.String(10), nullable=True),
        sa.Column("was_corrected", sa.String, server_default="false"),
        sa.Column("correction_text", sa.Text, nullable=True),
        sa.Column("user_rating", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- memories ---
    mem_tier = postgresql.ENUM(
        "correction",
        "episodic",
        "semantic",
        "procedural",
        name="memorytier",
        create_type=True,
    )
    mem_tier.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tier", mem_tier, nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True, index=True),
        sa.Column("faiss_index_id", sa.Integer, nullable=True),
        sa.Column("embedding_model", sa.String(50), server_default="all-MiniLM-L6-v2"),
        sa.Column("importance_score", sa.Float, server_default="1.0"),
        sa.Column("relevance_score", sa.Float, server_default="1.0"),
        sa.Column("decay_factor", sa.Float, server_default="0.97"),
        sa.Column("access_count", sa.Integer, server_default="0"),
        sa.Column("strength", sa.Float, server_default="1.0"),
        sa.Column("source_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSON, server_default="{}"),
        sa.Column("tags", postgresql.JSON, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- insights ---
    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), server_default="info"),
        sa.Column("data", postgresql.JSON, server_default="{}"),
        sa.Column("suggested_action", sa.Text, nullable=True),
        sa.Column("is_read", sa.String, server_default="false"),
        sa.Column("is_dismissed", sa.String, server_default="false"),
        sa.Column("is_acted_upon", sa.String, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- trust_events ---
    op.create_table(
        "trust_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_level", sa.Integer, nullable=False),
        sa.Column("to_level", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("metrics_snapshot", postgresql.JSON, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("trust_events")
    op.drop_table("insights")
    op.drop_table("memories")
    op.drop_table("executions")
    op.drop_table("agents")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS agentstatus")
    op.execute("DROP TYPE IF EXISTS executionstatus")
    op.execute("DROP TYPE IF EXISTS memorytier")
