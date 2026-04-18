"""Fix execution model: was_corrected Boolean, total_cost_usd Numeric, add config_version_id.

Revision ID: 002_fix_execution_fields
Revises: 001_initial
Create Date: 2025-07-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_fix_execution_fields"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix was_corrected: String -> Boolean
    op.alter_column(
        "executions",
        "was_corrected",
        type_=sa.Boolean,
        postgresql_using="CASE WHEN was_corrected IN ('true', '1', 'yes') THEN true ELSE false END",
        server_default=sa.text("false"),
        nullable=False,
    )

    # Fix total_cost_usd: Float -> Numeric(12,6)
    op.alter_column(
        "executions",
        "total_cost_usd",
        type_=sa.Numeric(12, 6),
        postgresql_using="total_cost_usd::numeric(12,6)",
    )

    # Add config_version_id for config snapshot tracking (GOVERN-2)
    op.add_column(
        "executions",
        sa.Column("config_version_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_executions_config_version", "executions", ["config_version_id"])


def downgrade() -> None:
    op.drop_index("ix_executions_config_version", table_name="executions")
    op.drop_column("executions", "config_version_id")
    op.alter_column(
        "executions",
        "total_cost_usd",
        type_=sa.Float,
    )
    op.alter_column(
        "executions",
        "was_corrected",
        type_=sa.String(50),
        server_default=sa.text("'false'"),
    )
