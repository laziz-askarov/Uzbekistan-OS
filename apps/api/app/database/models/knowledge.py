from datetime import date, datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Domain(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "domains"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="risk_level_allowed",
        ),
        {"schema": "knowledge"},
    )

    slug: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, server_default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class SourceOrganization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_organizations"
    __table_args__ = ({"schema": "knowledge"},)

    country_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geography.countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    website_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('html', 'pdf', 'feed', 'manual')",
            name="source_type_allowed",
        ),
        CheckConstraint(
            "crawl_policy IN ('allowed', 'manual_only', 'blocked', 'pending_review')",
            name="crawl_policy_allowed",
        ),
        CheckConstraint("trust_tier BETWEEN 1 AND 3", name="trust_tier_range"),
        {"schema": "knowledge"},
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.source_organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    crawl_policy: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default="pending_review",
    )
    trust_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'in_review', 'published', 'expired', 'archived')",
            name="status_allowed",
        ),
        Index("ix_documents_domain_status", "domain_id", "status"),
        {"schema": "knowledge"},
    )

    slug: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    domain_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.domains.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    canonical_language_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geography.languages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    current_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "knowledge.document_versions.id",
            name="fk_documents_current_version_id_document_versions",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )


class DocumentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "language_id",
            "version_major",
            "version_minor",
            "version_revision",
            name="uq_document_versions_identity",
        ),
        CheckConstraint(
            "version_major >= 1 AND version_minor >= 0 AND version_revision >= 0",
            name="version_numbers_nonnegative",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="effective_date_order",
        ),
        Index("ix_document_versions_effective", "effective_from", "effective_until"),
        {"schema": "knowledge"},
    )

    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geography.languages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    translation_of_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="SET NULL"),
    )
    version_major: Mapped[int] = mapped_column(Integer, nullable=False)
    version_minor: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    version_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentSource(Base):
    __tablename__ = "document_sources"
    __table_args__ = ({"schema": "knowledge"},)

    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.sources.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class Chunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "ordinal", name="uq_chunks_version_ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal_nonnegative"),
        CheckConstraint("token_count > 0", name="token_count_positive"),
        Index("ix_chunks_attributes_gin", "attributes", postgresql_using="gin"),
        {"schema": "knowledge"},
    )

    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str] = mapped_column(String(160), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Embedding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_key", name="uq_embeddings_chunk_model"),
        CheckConstraint("dimensions > 0", name="dimensions_positive"),
        {"schema": "knowledge"},
    )

    chunk_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_key: Mapped[str] = mapped_column(String(160), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(VECTOR(), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PublicationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "publication_records"
    __table_args__ = ({"schema": "knowledge"},)

    review_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingestion.review_items.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    published_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    candidate_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentLifecycleEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_lifecycle_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('expired')", name="event_type_allowed"),
        UniqueConstraint(
            "document_version_id",
            "event_type",
            name="uq_document_lifecycle_events_version_type",
        ),
        {"schema": "knowledge"},
    )

    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "knowledge.document_versions.id",
            name="fk_lifecycle_events_version",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class IndexJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "index_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'retry_scheduled', 'succeeded', "
            "'dead_lettered', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts",
            name="attempt_count_range",
        ),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint("token_count >= 0", name="token_count_nonnegative"),
        CheckConstraint("duration_ms >= 0", name="duration_ms_nonnegative"),
        CheckConstraint("cost_microusd >= 0", name="cost_microusd_nonnegative"),
        UniqueConstraint(
            "document_version_id",
            "idempotency_key",
            name="uq_index_jobs_version_key",
        ),
        Index("ix_index_jobs_queue", "status", "scheduled_at"),
        {"schema": "knowledge"},
    )

    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    model_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cost_microusd: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    result: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
