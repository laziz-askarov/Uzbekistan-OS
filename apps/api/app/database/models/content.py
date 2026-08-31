from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ContentAuthor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authors"
    __table_args__ = ({"schema": "content"},)

    principal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="SET NULL"),
        unique=True,
    )
    slug: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class ContentPost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('article', 'guide', 'platform_update', 'interview')",
            name="content_type_allowed",
        ),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')",
            name="status_allowed",
        ),
        Index("ix_content_posts_status_domain", "status", "domain_id"),
        {"schema": "content"},
    )

    slug: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(24), nullable=False)
    domain_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.domains.id", ondelete="RESTRICT"),
        index=True,
    )
    language_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geography.languages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    translation_group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, server_default=func.gen_random_uuid(), index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    created_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    published_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "content.post_versions.id",
            name="fk_content_posts_published_version",
            use_alter=True,
            ondelete="SET NULL",
        ),
    )


class ContentPostVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "post_versions"
    __table_args__ = (
        UniqueConstraint("post_id", "version_number", name="uq_content_post_version_number"),
        CheckConstraint("version_number >= 1", name="version_number_positive"),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')",
            name="status_allowed",
        ),
        CheckConstraint(
            "status = 'draft' OR submitted_at IS NOT NULL",
            name="submission_fields_consistent",
        ),
        CheckConstraint(
            "status NOT IN ('approved', 'published', 'stale', 'archived') "
            "OR (reviewed_by_principal_id IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="review_fields_consistent",
        ),
        CheckConstraint(
            "status NOT IN ('published', 'stale', 'archived') "
            "OR (published_by_principal_id IS NOT NULL AND published_at IS NOT NULL)",
            name="publication_fields_consistent",
        ),
        Index("ix_content_post_versions_status_review_due", "status", "review_due_at"),
        {"schema": "content"},
    )

    post_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(200))
    canonical_url: Mapped[str | None] = mapped_column(Text)
    hero_image_url: Mapped[str | None] = mapped_column(Text)
    hero_image_alt: Mapped[str | None] = mapped_column(String(500))
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.authors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    include_in_rag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_principal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("identity.principals.id", ondelete="RESTRICT")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    published_by_principal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("identity.principals.id", ondelete="RESTRICT")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ContentRagChunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("post_version_id", "ordinal", name="uq_content_rag_chunk_ordinal"),
        CheckConstraint("ordinal >= 0", name="ordinal_nonnegative"),
        CheckConstraint("token_count > 0", name="token_count_positive"),
        {"schema": "content"},
    )

    post_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.post_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str] = mapped_column(String(160), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContentPostSource(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "post_sources"
    __table_args__ = (
        UniqueConstraint(
            "post_version_id", "source_id", "locator", name="uq_content_post_source_locator"
        ),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        {"schema": "content"},
    )

    post_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.post_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge.document_versions.id", ondelete="SET NULL"),
    )
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class ContentPostRelation(Base):
    __tablename__ = "post_relations"
    __table_args__ = (
        CheckConstraint("post_id <> related_post_id", name="not_self_referential"),
        CheckConstraint(
            "relation_type IN ('related', 'next', 'previous')", name="relation_type_allowed"
        ),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        {"schema": "content"},
    )

    post_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    related_post_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class ContentMediaAsset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="byte_size_positive"),
        {"schema": "content"},
    )

    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    public_url: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContentPublicationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "publication_records"
    __table_args__ = ({"schema": "content"},)

    post_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.post_versions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    prior_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("content.post_versions.id", ondelete="SET NULL"),
    )
    published_by_principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity.principals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
