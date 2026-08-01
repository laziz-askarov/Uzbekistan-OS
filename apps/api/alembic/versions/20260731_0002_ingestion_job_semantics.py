"""Add idempotent ingestion job and snapshot semantics.

Revision ID: 20260731_0002
Revises: 20260731_0001
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0002"
down_revision: str | None = "20260731_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_snapshots",
        sa.Column("normalized_sha256", sa.String(length=64), nullable=True),
        schema="ingestion",
    )
    op.add_column(
        "source_snapshots",
        sa.Column("byte_size", sa.Integer(), server_default="0", nullable=False),
        schema="ingestion",
    )
    op.execute(
        "UPDATE ingestion.source_snapshots "
        "SET normalized_sha256 = sha256 WHERE normalized_sha256 IS NULL"
    )
    op.alter_column(
        "source_snapshots",
        "normalized_sha256",
        nullable=False,
        schema="ingestion",
    )
    op.create_unique_constraint(
        "uq_source_snapshots_source_sha256",
        "source_snapshots",
        ["source_id", "sha256"],
        schema="ingestion",
    )

    op.drop_constraint(
        op.f("ck_crawl_jobs_status_allowed"),
        "crawl_jobs",
        schema="ingestion",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_crawl_jobs_attempt_count_nonnegative"),
        "crawl_jobs",
        schema="ingestion",
        type_="check",
    )
    op.alter_column(
        "crawl_jobs",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=24),
        schema="ingestion",
    )
    op.add_column(
        "crawl_jobs",
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="ingestion",
    )
    op.add_column(
        "crawl_jobs",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        schema="ingestion",
    )
    op.add_column(
        "crawl_jobs",
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        schema="ingestion",
    )
    op.add_column(
        "crawl_jobs",
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="ingestion",
    )
    op.execute(
        "UPDATE ingestion.crawl_jobs "
        "SET idempotency_key = 'legacy:' || id::text WHERE idempotency_key IS NULL"
    )
    op.alter_column(
        "crawl_jobs",
        "idempotency_key",
        nullable=False,
        schema="ingestion",
    )
    op.create_check_constraint(
        "status_allowed",
        "crawl_jobs",
        "status IN ('queued', 'running', 'retry_scheduled', 'succeeded', "
        "'dead_lettered', 'cancelled')",
        schema="ingestion",
    )
    op.create_check_constraint(
        "attempt_count_range",
        "crawl_jobs",
        "attempt_count >= 0 AND attempt_count <= max_attempts",
        schema="ingestion",
    )
    op.create_check_constraint(
        "max_attempts_positive",
        "crawl_jobs",
        "max_attempts > 0",
        schema="ingestion",
    )
    op.create_foreign_key(
        "fk_crawl_jobs_source_snapshot_id_source_snapshots",
        "crawl_jobs",
        "source_snapshots",
        ["source_snapshot_id"],
        ["id"],
        source_schema="ingestion",
        referent_schema="ingestion",
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_crawl_jobs_source_key",
        "crawl_jobs",
        ["source_id", "idempotency_key"],
        schema="ingestion",
    )
    op.create_index(
        "ix_crawl_jobs_source_snapshot_id",
        "crawl_jobs",
        ["source_snapshot_id"],
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crawl_jobs_source_snapshot_id",
        table_name="crawl_jobs",
        schema="ingestion",
    )
    op.drop_constraint(
        "uq_crawl_jobs_source_key",
        "crawl_jobs",
        schema="ingestion",
        type_="unique",
    )
    op.drop_constraint(
        "fk_crawl_jobs_source_snapshot_id_source_snapshots",
        "crawl_jobs",
        schema="ingestion",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("ck_crawl_jobs_max_attempts_positive"),
        "crawl_jobs",
        schema="ingestion",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_crawl_jobs_attempt_count_range"),
        "crawl_jobs",
        schema="ingestion",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_crawl_jobs_status_allowed"),
        "crawl_jobs",
        schema="ingestion",
        type_="check",
    )
    op.execute(
        "UPDATE ingestion.crawl_jobs SET status = 'failed' "
        "WHERE status IN ('retry_scheduled', 'dead_lettered')"
    )
    op.alter_column(
        "crawl_jobs",
        "status",
        existing_type=sa.String(length=24),
        type_=sa.String(length=20),
        schema="ingestion",
    )
    op.create_check_constraint(
        "status_allowed",
        "crawl_jobs",
        "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
        schema="ingestion",
    )
    op.create_check_constraint(
        "attempt_count_nonnegative",
        "crawl_jobs",
        "attempt_count >= 0",
        schema="ingestion",
    )
    op.drop_column("crawl_jobs", "result", schema="ingestion")
    op.drop_column("crawl_jobs", "max_attempts", schema="ingestion")
    op.drop_column("crawl_jobs", "idempotency_key", schema="ingestion")
    op.drop_column("crawl_jobs", "source_snapshot_id", schema="ingestion")

    op.drop_constraint(
        "uq_source_snapshots_source_sha256",
        "source_snapshots",
        schema="ingestion",
        type_="unique",
    )
    op.drop_column("source_snapshots", "byte_size", schema="ingestion")
    op.drop_column("source_snapshots", "normalized_sha256", schema="ingestion")
