"""Create database namespaces and the versioned knowledge foundation.

Revision ID: 20260731_0001
Revises:
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = (
    "identity",
    "geography",
    "knowledge",
    "workflow",
    "conversation",
    "ai",
    "ingestion",
    "analytics",
    "audit",
)

EXTENSIONS = ("pgcrypto", "vector", "pg_trgm", "unaccent", "citext")

LANGUAGE_EN_ID = "00000000-0000-0000-0000-000000000001"
LANGUAGE_UZ_ID = "00000000-0000-0000-0000-000000000002"
LANGUAGE_RU_ID = "00000000-0000-0000-0000-000000000003"
UZBEKISTAN_ID = "00000000-0000-0000-0000-000000000100"

DOMAIN_ROWS = (
    ("00000000-0000-0000-0000-000000001001", "immigration", "Immigration", "high"),
    ("00000000-0000-0000-0000-000000001002", "tourism", "Tourism", "medium"),
    (
        "00000000-0000-0000-0000-000000001003",
        "business-registration",
        "Business Registration",
        "high",
    ),
    ("00000000-0000-0000-0000-000000001004", "healthcare", "Healthcare", "high"),
    (
        "00000000-0000-0000-0000-000000001005",
        "everyday-living",
        "Everyday Living",
        "medium",
    ),
)


def upgrade() -> None:
    for extension in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')

    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    op.create_table(
        "languages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("native_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_languages"),
        sa.UniqueConstraint("code", name="uq_languages_code"),
        schema="geography",
    )

    op.create_table(
        "countries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("iso2", postgresql.CITEXT(), nullable=False),
        sa.Column("iso3", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("default_language_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["default_language_id"],
            ["geography.languages.id"],
            name="fk_countries_default_language_id_languages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_countries"),
        sa.UniqueConstraint("iso2", name="uq_countries_iso2"),
        sa.UniqueConstraint("iso3", name="uq_countries_iso3"),
        schema="geography",
    )
    op.create_index(
        "ix_countries_default_language_id",
        "countries",
        ["default_language_id"],
        schema="geography",
    )

    op.create_table(
        "domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "risk_level IN ('low', 'medium', 'high')",
            name="risk_level_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_domains"),
        sa.UniqueConstraint("slug", name="uq_domains_slug"),
        schema="knowledge",
    )

    languages = sa.table(
        "languages",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", postgresql.CITEXT()),
        sa.column("name", sa.String()),
        sa.column("native_name", sa.String()),
        schema="geography",
    )
    op.bulk_insert(
        languages,
        [
            {"id": LANGUAGE_EN_ID, "code": "en", "name": "English", "native_name": "English"},
            {"id": LANGUAGE_UZ_ID, "code": "uz", "name": "Uzbek", "native_name": "O'zbekcha"},
            {"id": LANGUAGE_RU_ID, "code": "ru", "name": "Russian", "native_name": "Русский"},
        ],
    )

    countries = sa.table(
        "countries",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("iso2", postgresql.CITEXT()),
        sa.column("iso3", postgresql.CITEXT()),
        sa.column("name", sa.String()),
        sa.column("default_language_id", postgresql.UUID(as_uuid=True)),
        schema="geography",
    )
    op.bulk_insert(
        countries,
        [
            {
                "id": UZBEKISTAN_ID,
                "iso2": "UZ",
                "iso3": "UZB",
                "name": "Uzbekistan",
                "default_language_id": LANGUAGE_UZ_ID,
            }
        ],
    )

    domains = sa.table(
        "domains",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", postgresql.CITEXT()),
        sa.column("name", sa.String()),
        sa.column("risk_level", sa.String()),
        schema="knowledge",
    )
    op.bulk_insert(
        domains,
        [
            {"id": row_id, "slug": slug, "name": name, "risk_level": risk_level}
            for row_id, slug, name, risk_level in DOMAIN_ROWS
        ],
    )

    op.create_table(
        "source_organizations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=False),
        sa.Column("is_official", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["country_id"],
            ["geography.countries.id"],
            name="fk_source_organizations_country_id_countries",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_organizations"),
        sa.UniqueConstraint("slug", name="uq_source_organizations_slug"),
        schema="knowledge",
    )
    op.create_index(
        "ix_source_organizations_country_id",
        "source_organizations",
        ["country_id"],
        schema="knowledge",
    )

    op.create_table(
        "sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column(
            "crawl_policy",
            sa.String(length=24),
            server_default="pending_review",
            nullable=False,
        ),
        sa.Column("trust_tier", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
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
            "source_type IN ('html', 'pdf', 'feed', 'manual')",
            name="source_type_allowed",
        ),
        sa.CheckConstraint(
            "crawl_policy IN ('allowed', 'manual_only', 'blocked', 'pending_review')",
            name="crawl_policy_allowed",
        ),
        sa.CheckConstraint("trust_tier BETWEEN 1 AND 3", name="trust_tier_range"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["knowledge.source_organizations.id"],
            name="fk_sources_organization_id_source_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("url", name="uq_sources_url"),
        schema="knowledge",
    )
    op.create_index(
        "ix_sources_organization_id",
        "sources",
        ["organization_id"],
        schema="knowledge",
    )

    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_language_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "status IN ('draft', 'in_review', 'published', 'expired', 'archived')",
            name="status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_language_id"],
            ["geography.languages.id"],
            name="fk_documents_canonical_language_id_languages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["knowledge.domains.id"],
            name="fk_documents_domain_id_domains",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("slug", name="uq_documents_slug"),
        schema="knowledge",
    )
    op.create_index(
        "ix_documents_canonical_language_id",
        "documents",
        ["canonical_language_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_documents_domain_id",
        "documents",
        ["domain_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_documents_domain_status",
        "documents",
        ["domain_id", "status"],
        schema="knowledge",
    )

    op.create_table(
        "document_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("translation_of_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_major", sa.Integer(), nullable=False),
        sa.Column("version_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_major >= 1 AND version_minor >= 0 AND version_revision >= 0",
            name="version_numbers_nonnegative",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="effective_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge.documents.id"],
            name="fk_document_versions_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["language_id"],
            ["geography.languages.id"],
            name="fk_document_versions_language_id_languages",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["translation_of_id"],
            ["knowledge.document_versions.id"],
            name="fk_document_versions_translation_of_id_document_versions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_versions"),
        sa.UniqueConstraint(
            "document_id",
            "language_id",
            "version_major",
            "version_minor",
            "version_revision",
            name="uq_document_versions_identity",
        ),
        schema="knowledge",
    )
    op.create_index(
        "ix_document_versions_document_id",
        "document_versions",
        ["document_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_document_versions_language_id",
        "document_versions",
        ["language_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_document_versions_effective",
        "document_versions",
        ["effective_from", "effective_until"],
        schema="knowledge",
    )
    op.create_foreign_key(
        "fk_documents_current_version_id_document_versions",
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
        source_schema="knowledge",
        referent_schema="knowledge",
        ondelete="SET NULL",
    )

    op.create_table(
        "document_sources",
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge.document_versions.id"],
            name="fk_document_sources_document_version_id_document_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["knowledge.sources.id"],
            name="fk_document_sources_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "document_version_id",
            "source_id",
            name="pk_document_sources",
        ),
        schema="knowledge",
    )

    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", sa.String(length=160), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "attributes",
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
        sa.CheckConstraint("ordinal >= 0", name="ordinal_nonnegative"),
        sa.CheckConstraint("token_count > 0", name="token_count_positive"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge.document_versions.id"],
            name="fk_chunks_document_version_id_document_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint(
            "document_version_id",
            "ordinal",
            name="uq_chunks_version_ordinal",
        ),
        schema="knowledge",
    )
    op.create_index(
        "ix_chunks_document_version_id",
        "chunks",
        ["document_version_id"],
        schema="knowledge",
    )
    op.create_index(
        "ix_chunks_attributes_gin",
        "chunks",
        ["attributes"],
        unique=False,
        schema="knowledge",
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_chunks_content_fts ON knowledge.chunks "
        "USING gin (to_tsvector('simple', content))"
    )

    op.create_table(
        "embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_key", sa.String(length=160), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", VECTOR(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("dimensions > 0", name="dimensions_positive"),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["knowledge.chunks.id"],
            name="fk_embeddings_chunk_id_chunks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_embeddings"),
        sa.UniqueConstraint("chunk_id", "model_key", name="uq_embeddings_chunk_model"),
        schema="knowledge",
    )
    op.create_index(
        "ix_embeddings_chunk_id",
        "embeddings",
        ["chunk_id"],
        schema="knowledge",
    )

    op.create_table(
        "source_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "http_status BETWEEN 100 AND 599",
            name="http_status_range",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["knowledge.sources.id"],
            name="fk_source_snapshots_source_id_sources",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_snapshots"),
        sa.UniqueConstraint("storage_key", name="uq_source_snapshots_storage_key"),
        schema="ingestion",
    )
    op.create_index(
        "ix_source_snapshots_source_id",
        "source_snapshots",
        ["source_id"],
        schema="ingestion",
    )
    op.create_index(
        "ix_source_snapshots_sha256",
        "source_snapshots",
        ["sha256"],
        schema="ingestion",
    )

    op.create_table(
        "crawl_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="queued", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "error",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="status_allowed",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="attempt_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["knowledge.sources.id"],
            name="fk_crawl_jobs_source_id_sources",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_crawl_jobs"),
        schema="ingestion",
    )
    op.create_index(
        "ix_crawl_jobs_source_id",
        "crawl_jobs",
        ["source_id"],
        schema="ingestion",
    )
    op.create_index(
        "ix_crawl_jobs_queue",
        "crawl_jobs",
        ["status", "scheduled_at"],
        schema="ingestion",
    )

    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=160), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
        schema="audit",
    )
    op.create_index("ix_events_actor_user_id", "events", ["actor_user_id"], schema="audit")
    op.create_index("ix_events_action", "events", ["action"], schema="audit")
    op.create_index("ix_events_entity_type", "events", ["entity_type"], schema="audit")
    op.create_index("ix_events_entity_id", "events", ["entity_id"], schema="audit")
    op.create_index("ix_events_request_id", "events", ["request_id"], schema="audit")
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"], schema="audit")

    op.execute(
        """
        CREATE VIEW knowledge.retrievable_chunks AS
        SELECT
            c.id AS chunk_id,
            c.document_version_id,
            c.section_id,
            c.ordinal,
            c.content,
            c.attributes,
            d.id AS document_id,
            d.slug AS document_slug,
            d.domain_id,
            v.language_id,
            v.title,
            v.summary,
            v.effective_from,
            v.effective_until
        FROM knowledge.chunks AS c
        JOIN knowledge.document_versions AS v ON v.id = c.document_version_id
        JOIN knowledge.documents AS d ON d.id = v.document_id
        WHERE d.status = 'published'
          AND d.current_version_id = v.id
          AND v.published_at IS NOT NULL
          AND v.effective_from <= CURRENT_DATE
          AND (v.effective_until IS NULL OR v.effective_until >= CURRENT_DATE)
        """
    )


def downgrade() -> None:
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    for extension in reversed(EXTENSIONS):
        op.execute(f'DROP EXTENSION IF EXISTS "{extension}"')
