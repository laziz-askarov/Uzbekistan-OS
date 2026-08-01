from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SourceSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        CheckConstraint("http_status BETWEEN 100 AND 599", name="http_status_range"),
        UniqueConstraint("source_id", "sha256", name="uq_source_snapshots_source_sha256"),
        {"schema": "ingestion"},
    )

    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    normalized_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CrawlJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "crawl_jobs"
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
        UniqueConstraint("source_id", "idempotency_key", name="uq_crawl_jobs_source_key"),
        Index("ix_crawl_jobs_queue", "status", "scheduled_at"),
        {"schema": "ingestion"},
    )

    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_snapshot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingestion.source_snapshots.id", ondelete="SET NULL"),
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
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


class ExtractionArtifact(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "extraction_artifacts"
    __table_args__ = (
        CheckConstraint("section_count > 0", name="section_count_positive"),
        UniqueConstraint(
            "source_snapshot_id",
            "adapter_key",
            "schema_version",
            name="uq_extraction_artifacts_snapshot_adapter_version",
        ),
        {"schema": "ingestion"},
    )

    source_snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingestion.source_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adapter_key: Mapped[str] = mapped_column(String(160), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    section_count: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ReviewItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_review', 'approved', 'rejected', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint("priority BETWEEN 0 AND 100", name="priority_range"),
        Index("ix_review_items_queue", "status", "priority", "created_at"),
        {"schema": "ingestion"},
    )

    extraction_artifact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ingestion.extraction_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    assigned_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
