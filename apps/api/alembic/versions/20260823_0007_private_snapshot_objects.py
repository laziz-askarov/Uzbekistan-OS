"""Add private database-backed snapshot objects.

Revision ID: 20260823_0007
Revises: 20260801_0006
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260823_0007"
down_revision: str | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snapshot_objects",
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("byte_size >= 0", name="byte_size_non_negative"),
        sa.CheckConstraint("length(sha256) = 64", name="sha256_length"),
        sa.PrimaryKeyConstraint("storage_key", name="pk_snapshot_objects"),
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_table("snapshot_objects", schema="ingestion")
