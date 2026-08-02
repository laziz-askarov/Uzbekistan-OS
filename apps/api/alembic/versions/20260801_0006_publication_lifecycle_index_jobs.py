"""Add auditable publication lifecycle events and index jobs.

Revision ID: 20260801_0006
Revises: 20260731_0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0006"
down_revision: str | None = "20260731_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_lifecycle_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("event_type IN ('expired')", name="event_type_allowed"),
        sa.ForeignKeyConstraint(
            ["actor_principal_id"],
            ["identity.principals.id"],
            name="fk_document_lifecycle_events_actor_principal_id_principals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge.documents.id"],
            name="fk_document_lifecycle_events_document_id_documents",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge.document_versions.id"],
            name="fk_lifecycle_events_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_lifecycle_events"),
        sa.UniqueConstraint(
            "document_version_id",
            "event_type",
            name="uq_document_lifecycle_events_version_type",
        ),
        schema="knowledge",
    )
    op.create_index(
        "ix_document_lifecycle_events_actor_principal_id",
        "document_lifecycle_events",
        ["actor_principal_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_document_lifecycle_events_document_id",
        "document_lifecycle_events",
        ["document_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_document_lifecycle_events_document_version_id",
        "document_lifecycle_events",
        ["document_version_id"],
        schema="knowledge",
    )

    op.create_table(
        "index_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("model_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_microusd", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "error",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'retry_scheduled', 'succeeded', "
            "'dead_lettered', 'cancelled')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts",
            name="attempt_count_range",
        ),
        sa.CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        sa.CheckConstraint("token_count >= 0", name="token_count_nonnegative"),
        sa.CheckConstraint("duration_ms >= 0", name="duration_ms_nonnegative"),
        sa.CheckConstraint("cost_microusd >= 0", name="cost_microusd_nonnegative"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge.document_versions.id"],
            name="fk_index_jobs_document_version_id_document_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_principal_id"],
            ["identity.principals.id"],
            name="fk_index_jobs_requested_by_principal_id_principals",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_index_jobs"),
        sa.UniqueConstraint(
            "document_version_id",
            "idempotency_key",
            name="uq_index_jobs_version_key",
        ),
        schema="knowledge",
    )
    op.create_index(
        "ix_index_jobs_document_version_id",
        "index_jobs",
        ["document_version_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_index_jobs_requested_by_principal_id",
        "index_jobs",
        ["requested_by_principal_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_index_jobs_queue",
        "index_jobs",
        ["status", "scheduled_at"],
        schema="knowledge",
    )


def downgrade() -> None:
    op.drop_table("index_jobs", schema="knowledge")
    op.drop_table("document_lifecycle_events", schema="knowledge")
