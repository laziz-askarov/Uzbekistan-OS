from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.identity.service import AuthenticatedPrincipal

AUTHOR_ROLES = frozenset({"content_author", "admin"})
REVIEWER_ROLES = frozenset({"content_reviewer", "admin"})
PUBLISHER_ROLES = frozenset({"knowledge_publisher", "admin"})


class EditorialStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    STALE = "stale"
    ARCHIVED = "archived"


class EditorialDecision(StrEnum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"


class ContentType(StrEnum):
    ARTICLE = "article"
    GUIDE = "guide"
    PLATFORM_UPDATE = "platform_update"
    INTERVIEW = "interview"


class EditorialError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class EditorialSourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    document_version_id: UUID | None = None
    locator: str = Field(min_length=1, max_length=2000)
    quote: str | None = Field(default=None, max_length=5000)

    @field_validator("locator", "quote")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("source reference text cannot be blank")
        return cleaned


class EditorialRevisionDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    author_id: UUID
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=2000)
    body_markdown: str = Field(min_length=1)
    structured_content: dict[str, object] = Field(default_factory=dict)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=200)
    canonical_url: str | None = Field(default=None, max_length=2000)
    hero_image_url: str | None = Field(default=None, max_length=2000)
    hero_image_alt: str | None = Field(default=None, max_length=500)
    include_in_rag: bool = False
    sources: tuple[EditorialSourceReference, ...] = ()

    @field_validator(
        "title",
        "summary",
        "body_markdown",
        "seo_title",
        "seo_description",
        "canonical_url",
        "hero_image_url",
        "hero_image_alt",
    )
    @classmethod
    def strip_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("editorial content fields cannot be blank")
        return cleaned

    @model_validator(mode="after")
    def source_references_are_unique(self) -> "EditorialRevisionDraft":
        identities = [(source.source_id, source.locator) for source in self.sources]
        if len(identities) != len(set(identities)):
            raise ValueError("editorial source references must be unique")
        return self

    @property
    def checksum_sha256(self) -> str:
        payload = self.model_dump(mode="json")
        return sha256(
            dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()


class EditorialAuthorDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=240)
    bio: str | None = Field(default=None, max_length=5000)
    avatar_url: str | None = Field(default=None, max_length=2000)
    profile_url: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "bio", "avatar_url", "profile_url")
    @classmethod
    def strip_author_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("author fields cannot be blank")
        return cleaned


class EditorialPostDraft(EditorialRevisionDraft):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_type: ContentType
    domain_slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    language_code: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    translation_group_id: UUID | None = None

    @model_validator(mode="after")
    def grounded_posts_require_a_domain_and_source(self) -> "EditorialPostDraft":
        if (self.content_type is ContentType.GUIDE or self.include_in_rag) and (
            not self.domain_slug or not self.sources
        ):
            raise ValueError(
                "guides and RAG-enabled posts require a knowledge domain "
                "and at least one official source"
            )
        return self


@dataclass(frozen=True, slots=True)
class EditorialRevisionRecord:
    id: UUID
    post_id: UUID
    version_number: int
    content_type: ContentType
    status: EditorialStatus
    checksum_sha256: str
    created_by_principal_id: UUID
    include_in_rag: bool = False
    submitted_at: datetime | None = None
    reviewed_by_principal_id: UUID | None = None
    reviewed_at: datetime | None = None
    decision_reason: str | None = None
    published_by_principal_id: UUID | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EditorialAuthorRecord:
    id: UUID
    principal_id: UUID | None
    slug: str
    name: str
    bio: str | None
    avatar_url: str | None
    profile_url: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class EditorialPostSummaryRecord:
    id: UUID
    slug: str
    translation_group_id: UUID
    content_type: ContentType
    domain_slug: str | None
    language_code: str
    status: EditorialStatus
    published_version_id: UUID | None
    latest_revision_id: UUID
    latest_revision_number: int
    latest_revision_status: EditorialStatus
    latest_title: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewedKnowledgeSourceRecord:
    source_id: UUID
    document_id: UUID
    document_version_id: UUID
    document_slug: str
    document_title: str
    document_summary: str
    domain_slug: str
    language_code: str
    version_label: str
    source_title: str
    organization: str
    source_url: str
    source_locator: str
    reviewed_at: datetime
    published_at: datetime
    effective_until: date | None


@dataclass(frozen=True, slots=True)
class EditorialRevisionDetailRecord:
    revision: EditorialRevisionRecord
    slug: str
    domain_slug: str | None
    language_code: str
    translation_group_id: UUID
    title: str
    summary: str
    body_markdown: str
    structured_content: dict[str, object]
    seo_title: str | None
    seo_description: str | None
    canonical_url: str | None
    hero_image_url: str | None
    hero_image_alt: str | None
    include_in_rag: bool
    author: EditorialAuthorRecord
    sources: tuple[EditorialSourceReference, ...]


@dataclass(frozen=True, slots=True)
class PublishedEditorialSourceRecord:
    source_id: UUID
    document_version_id: UUID | None
    document_slug: str | None
    document_title: str | None
    reviewed_at: datetime | None
    title: str
    organization: str
    url: str
    locator: str


@dataclass(frozen=True, slots=True)
class PublishedEditorialTranslationRecord:
    language_code: str
    slug: str
    title: str


@dataclass(frozen=True, slots=True)
class PublishedEditorialSummaryRecord:
    id: UUID
    slug: str
    translation_group_id: UUID
    content_type: ContentType
    domain_slug: str | None
    language_code: str
    title: str
    summary: str
    hero_image_url: str | None
    hero_image_alt: str | None
    author_name: str
    author_slug: str
    published_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PublishedEditorialPostRecord:
    id: UUID
    version_id: UUID
    version_number: int
    slug: str
    content_type: ContentType
    domain_slug: str | None
    language_code: str
    title: str
    summary: str
    body_markdown: str
    structured_content: dict[str, object]
    seo_title: str | None
    seo_description: str | None
    canonical_url: str | None
    hero_image_url: str | None
    hero_image_alt: str | None
    author: EditorialAuthorRecord
    sources: tuple[PublishedEditorialSourceRecord, ...]
    translations: tuple[PublishedEditorialTranslationRecord, ...]
    published_at: datetime
    updated_at: datetime
    review_due_at: datetime | None


@dataclass(frozen=True, slots=True)
class EditorialAuditRecord:
    actor_user_id: UUID
    action: str
    entity_id: UUID
    request_id: str | None
    payload: dict[str, object]
    occurred_at: datetime


class EditorialRepository(Protocol):
    def list_published_posts(
        self,
        *,
        domain_slug: str | None,
        language_code: str | None,
        limit: int,
    ) -> tuple[PublishedEditorialSummaryRecord, ...]: ...

    def get_published_post(self, slug: str) -> PublishedEditorialPostRecord | None: ...

    def list_authors(self) -> tuple[EditorialAuthorRecord, ...]: ...

    def create_author(
        self,
        draft: EditorialAuthorDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at: datetime,
    ) -> EditorialAuthorRecord: ...

    def list_posts(
        self,
        *,
        status: EditorialStatus | None,
        limit: int,
    ) -> tuple[EditorialPostSummaryRecord, ...]: ...

    def list_reviewed_sources(
        self,
        *,
        domain_slug: str | None,
        language_code: str | None,
        limit: int,
    ) -> tuple[ReviewedKnowledgeSourceRecord, ...]: ...

    def get_detail(self, revision_id: UUID) -> EditorialRevisionDetailRecord | None: ...

    def create_post(
        self,
        draft: EditorialPostDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at: datetime,
    ) -> EditorialRevisionRecord: ...

    def create_revision(
        self,
        post_id: UUID,
        draft: EditorialRevisionDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at: datetime,
    ) -> EditorialRevisionRecord: ...

    def get_for_update(self, revision_id: UUID) -> EditorialRevisionRecord | None: ...

    def sources_are_eligible(self, revision_id: UUID) -> bool: ...

    def source_links_are_current(self, revision_id: UUID) -> bool: ...

    def update_draft(
        self,
        record: EditorialRevisionRecord,
        draft: EditorialRevisionDraft,
        principal: AuthenticatedPrincipal,
        *,
        updated_at: datetime,
    ) -> EditorialRevisionDetailRecord: ...

    def save(self, record: EditorialRevisionRecord) -> None: ...

    def publish(
        self,
        record: EditorialRevisionRecord,
        principal: AuthenticatedPrincipal,
        *,
        published_at: datetime,
    ) -> EditorialRevisionRecord: ...

    def append_audit(self, record: EditorialAuditRecord) -> None: ...


class EditorialService:
    def __init__(self, repository: EditorialRepository) -> None:
        self.repository = repository

    def list_published_posts(
        self,
        *,
        domain_slug: str | None = None,
        language_code: str | None = None,
        limit: int = 100,
    ) -> tuple[PublishedEditorialSummaryRecord, ...]:
        if not 1 <= limit <= 100:
            raise EditorialError(
                "invalid_editorial_limit", "editorial post limit must be between 1 and 100"
            )
        return self.repository.list_published_posts(
            domain_slug=domain_slug,
            language_code=language_code,
            limit=limit,
        )

    def get_published_post(self, slug: str) -> PublishedEditorialPostRecord:
        post = self.repository.get_published_post(slug)
        if post is None:
            raise EditorialError(
                "editorial_publication_not_found",
                "published editorial post does not exist",
            )
        return post

    def list_authors(self, principal: AuthenticatedPrincipal) -> tuple[EditorialAuthorRecord, ...]:
        self._authorize(principal, AUTHOR_ROLES | REVIEWER_ROLES | PUBLISHER_ROLES, "staff")
        return self.repository.list_authors()

    def create_author(
        self,
        principal: AuthenticatedPrincipal,
        draft: EditorialAuthorDraft,
        *,
        created_at: datetime | None = None,
    ) -> EditorialAuthorRecord:
        self._authorize(principal, AUTHOR_ROLES, "editorial author")
        now = created_at or datetime.now(UTC)
        author = self.repository.create_author(draft, principal, created_at=now)
        self.repository.append_audit(
            EditorialAuditRecord(
                actor_user_id=principal.id,
                action="content.author_created",
                entity_id=author.id,
                request_id=principal.request_id,
                payload={"slug": author.slug},
                occurred_at=now,
            )
        )
        return author

    def list_posts(
        self,
        principal: AuthenticatedPrincipal,
        *,
        status: EditorialStatus | None = None,
        limit: int = 100,
    ) -> tuple[EditorialPostSummaryRecord, ...]:
        self._authorize(principal, AUTHOR_ROLES | REVIEWER_ROLES | PUBLISHER_ROLES, "staff")
        if not 1 <= limit <= 100:
            raise EditorialError(
                "invalid_editorial_limit", "editorial post limit must be between 1 and 100"
            )
        return self.repository.list_posts(status=status, limit=limit)

    def list_reviewed_sources(
        self,
        principal: AuthenticatedPrincipal,
        *,
        domain_slug: str | None = None,
        language_code: str | None = None,
        limit: int = 200,
    ) -> tuple[ReviewedKnowledgeSourceRecord, ...]:
        self._authorize(principal, AUTHOR_ROLES | REVIEWER_ROLES | PUBLISHER_ROLES, "staff")
        if not 1 <= limit <= 200:
            raise EditorialError(
                "invalid_editorial_source_limit",
                "reviewed source limit must be between 1 and 200",
            )
        return self.repository.list_reviewed_sources(
            domain_slug=domain_slug,
            language_code=language_code,
            limit=limit,
        )

    def get_revision(
        self, principal: AuthenticatedPrincipal, revision_id: UUID
    ) -> EditorialRevisionDetailRecord:
        self._authorize(principal, AUTHOR_ROLES | REVIEWER_ROLES | PUBLISHER_ROLES, "staff")
        detail = self.repository.get_detail(revision_id)
        if detail is None:
            raise EditorialError(
                "editorial_revision_not_found", "editorial revision does not exist"
            )
        return detail

    def create_post(
        self,
        principal: AuthenticatedPrincipal,
        draft: EditorialPostDraft,
        *,
        created_at: datetime | None = None,
    ) -> EditorialRevisionRecord:
        self._authorize(principal, AUTHOR_ROLES, "editorial author")
        now = created_at or datetime.now(UTC)
        record = self.repository.create_post(draft, principal, created_at=now)
        self._audit(principal, record, "content.post_created", None, record.status, now)
        return record

    def create_revision(
        self,
        principal: AuthenticatedPrincipal,
        post_id: UUID,
        draft: EditorialRevisionDraft,
        *,
        created_at: datetime | None = None,
    ) -> EditorialRevisionRecord:
        self._authorize(principal, AUTHOR_ROLES, "editorial author")
        now = created_at or datetime.now(UTC)
        record = self.repository.create_revision(post_id, draft, principal, created_at=now)
        self._audit(principal, record, "content.revision_created", None, record.status, now)
        return record

    def update_draft(
        self,
        principal: AuthenticatedPrincipal,
        revision_id: UUID,
        draft: EditorialRevisionDraft,
        *,
        updated_at: datetime | None = None,
    ) -> EditorialRevisionDetailRecord:
        self._authorize(principal, AUTHOR_ROLES, "editorial author")
        record = self._get(revision_id)
        if record.status is not EditorialStatus.DRAFT:
            raise EditorialError(
                "invalid_editorial_transition",
                f"cannot edit a revision in {record.status} status",
            )
        now = updated_at or datetime.now(UTC)
        updated = self.repository.update_draft(
            record,
            draft,
            principal,
            updated_at=now,
        )
        self._audit(
            principal,
            updated.revision,
            "content.revision_updated",
            record.status,
            updated.revision.status,
            now,
        )
        return updated

    def submit(
        self,
        principal: AuthenticatedPrincipal,
        revision_id: UUID,
        *,
        submitted_at: datetime | None = None,
    ) -> EditorialRevisionRecord:
        self._authorize(principal, AUTHOR_ROLES, "editorial author")
        record = self._get(revision_id)
        if record.status is not EditorialStatus.DRAFT:
            raise EditorialError(
                "invalid_editorial_transition",
                f"cannot submit a revision in {record.status} status",
            )
        if not self.repository.source_links_are_current(record.id):
            raise EditorialError(
                "editorial_source_lineage_stale",
                "all editorial citations must reference current reviewed knowledge publications",
            )
        if (record.content_type is ContentType.GUIDE or record.include_in_rag) and not (
            self.repository.sources_are_eligible(record.id)
        ):
            raise EditorialError(
                "editorial_sources_not_eligible",
                "guides and RAG-enabled posts require active sources owned "
                "by official organizations",
            )
        now = submitted_at or datetime.now(UTC)
        submitted = replace(
            record,
            status=EditorialStatus.IN_REVIEW,
            submitted_at=now,
            updated_at=now,
        )
        self.repository.save(submitted)
        self._audit(
            principal, submitted, "content.revision_submitted", record.status, submitted.status, now
        )
        return submitted

    def decide(
        self,
        principal: AuthenticatedPrincipal,
        revision_id: UUID,
        decision: EditorialDecision,
        *,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> EditorialRevisionRecord:
        self._authorize(principal, REVIEWER_ROLES, "content reviewer")
        cleaned_reason = reason.strip()
        if not cleaned_reason or len(cleaned_reason) > 2000:
            raise EditorialError(
                "invalid_editorial_decision_reason",
                "decision reason must contain between 1 and 2000 characters",
            )
        record = self._get(revision_id)
        if record.status is not EditorialStatus.IN_REVIEW:
            raise EditorialError(
                "invalid_editorial_transition",
                f"cannot review a revision in {record.status} status",
            )
        if record.created_by_principal_id == principal.id and "admin" not in principal.roles:
            raise EditorialError(
                "editorial_self_review_forbidden",
                "non-admin authors cannot approve their own revisions",
            )
        now = reviewed_at or datetime.now(UTC)
        target = (
            EditorialStatus.APPROVED
            if decision is EditorialDecision.APPROVE
            else EditorialStatus.DRAFT
        )
        decided = replace(
            record,
            status=target,
            reviewed_by_principal_id=principal.id,
            reviewed_at=now,
            decision_reason=cleaned_reason,
            updated_at=now,
        )
        self.repository.save(decided)
        action = (
            "content.revision_approved"
            if decision is EditorialDecision.APPROVE
            else "content.revision_changes_requested"
        )
        self._audit(principal, decided, action, record.status, target, now)
        return decided

    def publish(
        self,
        principal: AuthenticatedPrincipal,
        revision_id: UUID,
        *,
        published_at: datetime | None = None,
    ) -> EditorialRevisionRecord:
        self._authorize(principal, PUBLISHER_ROLES, "content publisher")
        record = self._get(revision_id)
        if record.status is not EditorialStatus.APPROVED:
            raise EditorialError(
                "invalid_editorial_transition",
                f"cannot publish a revision in {record.status} status",
            )
        if not self.repository.source_links_are_current(record.id):
            raise EditorialError(
                "editorial_source_lineage_stale",
                "editorial citation lineage changed after review",
            )
        if (record.content_type is ContentType.GUIDE or record.include_in_rag) and not (
            self.repository.sources_are_eligible(record.id)
        ):
            raise EditorialError(
                "editorial_sources_not_eligible",
                "guide or RAG source eligibility changed after review",
            )
        now = published_at or datetime.now(UTC)
        published = self.repository.publish(record, principal, published_at=now)
        self._audit(
            principal, published, "content.revision_published", record.status, published.status, now
        )
        return published

    def _get(self, revision_id: UUID) -> EditorialRevisionRecord:
        record = self.repository.get_for_update(revision_id)
        if record is None:
            raise EditorialError(
                "editorial_revision_not_found", "editorial revision does not exist"
            )
        return record

    @staticmethod
    def _authorize(
        principal: AuthenticatedPrincipal, allowed_roles: frozenset[str], role_name: str
    ) -> None:
        if not principal.roles.intersection(allowed_roles):
            raise EditorialError(
                "editorial_forbidden", f"server-controlled {role_name} role is required"
            )

    def _audit(
        self,
        principal: AuthenticatedPrincipal,
        record: EditorialRevisionRecord,
        action: str,
        previous_status: EditorialStatus | None,
        current_status: EditorialStatus,
        occurred_at: datetime,
    ) -> None:
        self.repository.append_audit(
            EditorialAuditRecord(
                actor_user_id=principal.id,
                action=action,
                entity_id=record.id,
                request_id=principal.request_id,
                payload={
                    "post_id": str(record.post_id),
                    "version_number": record.version_number,
                    "previous_status": previous_status.value if previous_status else None,
                    "current_status": current_status.value,
                    "checksum_sha256": record.checksum_sha256,
                    "include_in_rag": record.include_in_rag,
                    "decision_reason_sha256": (
                        sha256(record.decision_reason.encode()).hexdigest()
                        if record.decision_reason
                        else None
                    ),
                },
                occurred_at=occurred_at,
            )
        )
