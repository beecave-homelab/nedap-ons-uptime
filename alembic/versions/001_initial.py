"""Initial schema for targets and checks tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial tables and indexes."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.create_table(
        "targets",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_s", sa.Integer(), nullable=False),
        sa.Column("timeout_s", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "checks",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("up", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checks_target_id_checked_at", "checks", ["target_id", "checked_at"])
    op.create_index("ix_checks_checked_at", "checks", ["checked_at"])
    op.create_index(op.f("ix_checks_target_id"), "checks", ["target_id"])


def downgrade() -> None:
    """Drop initial tables and indexes."""
    op.drop_index(op.f("ix_checks_target_id"), table_name="checks")
    op.drop_index("ix_checks_checked_at", table_name="checks")
    op.drop_index("ix_checks_target_id_checked_at", table_name="checks")
    op.drop_table("checks")
    op.drop_table("targets")
