"""Add audited admin-managed manual sources.

Revision ID: 20260823_0008
Revises: 20260823_0007
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260823_0008"
down_revision: str | None = "20260823_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "managed_source_configs",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "adapter_key",
            sa.String(length=160),
            server_default="generic-manual",
            nullable=False,
        ),
        sa.Column(
            "registry_status", sa.String(length=20), server_default="approved", nullable=False
        ),
        sa.Column(
            "production_eligible", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("created_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_sha256", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint("registry_status = 'approved'", name="registry_status_approved"),
        sa.CheckConstraint("production_eligible", name="production_eligible_required"),
        sa.CheckConstraint("jsonb_typeof(domains) = 'array'", name="domains_array"),
        sa.CheckConstraint("jsonb_array_length(domains) > 0", name="domains_not_empty"),
        sa.CheckConstraint("jsonb_typeof(languages) = 'array'", name="languages_array"),
        sa.CheckConstraint("jsonb_array_length(languages) > 0", name="languages_not_empty"),
        sa.CheckConstraint("length(request_sha256) = 64", name="request_sha256_length"),
        sa.ForeignKeyConstraint(
            ["created_by_principal_id"],
            ["identity.principals.id"],
            name="fk_managed_source_configs_created_by_principal_id_principals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["knowledge.sources.id"],
            name="fk_managed_source_configs_source_id_sources",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_id", name="pk_managed_source_configs"),
        sa.UniqueConstraint("idempotency_key", name="uq_managed_source_configs_idempotency_key"),
        sa.UniqueConstraint("slug", name="uq_managed_source_configs_slug"),
        schema="ingestion",
    )
    op.create_index(
        "ix_managed_source_configs_created_by_principal_id",
        "managed_source_configs",
        ["created_by_principal_id"],
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_managed_source_configs_created_by_principal_id",
        table_name="managed_source_configs",
        schema="ingestion",
    )
    op.drop_table("managed_source_configs", schema="ingestion")
