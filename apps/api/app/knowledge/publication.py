from datetime import date, datetime
from hashlib import sha256
from json import dumps
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.artifacts import ExtractionArtifact
from app.ingestion.models import DomainSlug, LanguageCode
from app.ingestion.ports import SnapshotStore

PUBLISHER_ROLES = frozenset({"knowledge_publisher", "admin"})


class PublicationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CandidateVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    major: int = Field(ge=1)
    minor: int = Field(default=0, ge=0)
    revision: int = Field(default=0, ge=0)


class CandidateCitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    locator: str = Field(min_length=1)
    quote: str | None = None

    @field_validator("locator")
    @classmethod
    def locator_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("citation locator cannot be blank")
        return value

    @field_validator("quote")
    @classmethod
    def quote_must_contain_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("citation quote cannot be blank")
        return value


class CandidateSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    heading: str = Field(min_length=1)
    body: str = Field(min_length=1)
    citations: list[CandidateCitation] = Field(min_length=1)

    @field_validator("heading", "body")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("section text cannot be blank")
        return value


class PublicationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    review_item_id: UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    domain: DomainSlug
    language: LanguageCode
    version: CandidateVersion
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1)
    audiences: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    sections: list[CandidateSection] = Field(min_length=1)
    effective_from: date
    effective_until: date | None = None
    translation_of_id: UUID | None = None

    @field_validator("title", "summary")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("publication text cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> "PublicationCandidate":
        if self.effective_until is not None and self.effective_until < self.effective_from:
            raise ValueError("effective_until cannot precede effective_from")
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("candidate section IDs must be unique")
        if len(self.audiences) != len(set(self.audiences)):
            raise ValueError("candidate audiences must be unique")
        if len(self.keywords) != len(set(self.keywords)):
            raise ValueError("candidate keywords must be unique")
        return self

    def canonical_bytes(self) -> bytes:
        return dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()


class PublicationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    publication_id: UUID
    document_id: UUID
    document_version_id: UUID
    candidate_sha256: str
    published_at: datetime


class ReviewedLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    review_item_id: UUID
    review_status: str
    reviewed_at: datetime | None
    source_id: UUID
    snapshot_sha256: str
    artifact_storage_key: str
    artifact_sha256: str
    existing_publication: PublicationResult | None = None


class PublicationRepository(Protocol):
    def lock_review_lineage(self, review_item_id: UUID) -> ReviewedLineage | None: ...

    def publish_candidate(
        self,
        candidate: PublicationCandidate,
        lineage: ReviewedLineage,
        principal: AuthenticatedPrincipal,
        *,
        published_at: datetime,
    ) -> PublicationResult: ...


class PublicationService:
    def __init__(self, *, repository: PublicationRepository, object_store: SnapshotStore) -> None:
        self.repository = repository
        self.object_store = object_store

    def publish(
        self,
        principal: AuthenticatedPrincipal,
        candidate: PublicationCandidate,
        *,
        published_at: datetime,
    ) -> PublicationResult:
        if not principal.roles.intersection(PUBLISHER_ROLES):
            raise PublicationError(
                "publication_forbidden",
                "knowledge publisher or administrator role is required",
            )
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise PublicationError(
                "invalid_publication_time",
                "publication time must be timezone-aware",
            )
        lineage = self.repository.lock_review_lineage(candidate.review_item_id)
        if lineage is None:
            raise PublicationError("review_not_found", "review item does not exist")
        if lineage.review_status != "approved" or lineage.reviewed_at is None:
            raise PublicationError(
                "review_not_approved",
                "publication requires an approved extraction review",
            )
        if lineage.existing_publication is not None:
            if lineage.existing_publication.candidate_sha256 == candidate.sha256:
                return lineage.existing_publication
            raise PublicationError(
                "publication_conflict",
                "review item is already linked to a different publication candidate",
            )

        artifact_bytes = self.object_store.get(lineage.artifact_storage_key)
        if sha256(artifact_bytes).hexdigest() != lineage.artifact_sha256:
            raise PublicationError(
                "artifact_integrity_failure",
                "reviewed artifact checksum does not match database lineage",
            )
        artifact = ExtractionArtifact.model_validate_json(artifact_bytes)
        if artifact.raw_sha256 != lineage.snapshot_sha256:
            raise PublicationError(
                "snapshot_lineage_mismatch",
                "reviewed artifact does not match its source snapshot",
            )
        self._validate_evidence(candidate, artifact, lineage.source_id)
        return self.repository.publish_candidate(
            candidate,
            lineage,
            principal,
            published_at=published_at,
        )

    @staticmethod
    def _validate_evidence(
        candidate: PublicationCandidate,
        artifact: ExtractionArtifact,
        source_id: UUID,
    ) -> None:
        artifact_section_ids = [section.id for section in artifact.sections]
        candidate_section_ids = [section.id for section in candidate.sections]
        if artifact_section_ids != candidate_section_ids:
            raise PublicationError(
                "candidate_artifact_mismatch",
                "candidate sections and order must exactly match the approved artifact",
            )
        artifact_sections = {section.id: section for section in artifact.sections}
        candidate_sections = {section.id: section for section in candidate.sections}
        for section_id, section in candidate_sections.items():
            approved = artifact_sections[section_id]
            if section.heading != approved.heading or section.body != approved.body:
                raise PublicationError(
                    "candidate_artifact_mismatch",
                    f"candidate section differs from approved artifact: {section_id}",
                )
            for citation in section.citations:
                if citation.source_id != source_id:
                    raise PublicationError(
                        "citation_lineage_mismatch",
                        "all citations must reference the reviewed source",
                    )
                if citation.quote is not None and citation.quote not in approved.body:
                    raise PublicationError(
                        "citation_quote_mismatch",
                        f"citation quote is not present in section: {section_id}",
                    )
