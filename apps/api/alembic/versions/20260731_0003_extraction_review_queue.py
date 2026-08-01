"""Add extraction artifacts and the human review queue.

Revision ID: 20260731_0003
Revises: 20260731_0002
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0003"
down_revision: str | None = "20260731_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction_artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adapter_key", sa.String(length=160), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("normalized_sha256", sa.String(length=64), nullable=False),
        sa.Column("section_count", sa.Integer(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("section_count > 0", name="section_count_positive"),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["ingestion.source_snapshots.id"],
            name="fk_extraction_artifacts_source_snapshot_id_source_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_artifacts"),
        sa.UniqueConstraint("storage_key", name="uq_extraction_artifacts_storage_key"),
        sa.UniqueConstraint(
            "source_snapshot_id",
            "adapter_key",
            "schema_version",
            name="uq_extraction_artifacts_snapshot_adapter_version",
        ),
        schema="ingestion",
    )
    op.create_index(
        "ix_extraction_artifacts_source_snapshot_id",
        "extraction_artifacts",
        ["source_snapshot_id"],
        schema="ingestion",
    )

    op.create_table(
        "review_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("extraction_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="50", nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_review', 'approved', 'rejected', 'cancelled')",
            name="status_allowed",
        ),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="priority_range"),
        sa.ForeignKeyConstraint(
            ["extraction_artifact_id"],
            ["ingestion.extraction_artifacts.id"],
            name="fk_review_items_extraction_artifact_id_extraction_artifacts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_items"),
        sa.UniqueConstraint(
            "extraction_artifact_id",
            name="uq_review_items_extraction_artifact_id",
        ),
        schema="ingestion",
    )
    op.create_index(
        "ix_review_items_assigned_user_id",
        "review_items",
        ["assigned_user_id"],
        schema="ingestion",
    )
    op.create_index(
        "ix_review_items_queue",
        "review_items",
        ["status", "priority", "created_at"],
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_table("review_items", schema="ingestion")
    op.drop_table("extraction_artifacts", schema="ingestion")
