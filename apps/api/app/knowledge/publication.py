from datetime import date, datetime, timedelta
from hashlib import sha256
from json import dumps
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.artifacts import ExtractionArtifact
from app.ingestion.models import DomainSlug, LanguageCode
from app.ingestion.ports import SnapshotStore

PUBLISHER_ROLES = frozenset({"knowledge_publisher", "admin"})
FRESHNESS_DAYS_BY_DOMAIN: dict[DomainSlug, int] = {
    "immigration": 30,
    "business-registration": 30,
    "healthcare": 30,
    "everyday-living": 60,
    "tourism": 180,
}


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


class CandidateRequirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    mandatory: bool
    applies_when: list[str] = Field(default_factory=list)
    citations: list[CandidateCitation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_requirement(self) -> "CandidateRequirement":
        if len(self.applies_when) != len(set(self.applies_when)):
            raise ValueError("requirement applicability conditions must be unique")
        return self


class CandidateStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    ordinal: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    requirement_ids: list[str] = Field(default_factory=list)
    citations: list[CandidateCitation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_step(self) -> "CandidateStep":
        if len(self.requirement_ids) != len(set(self.requirement_ids)):
            raise ValueError("step requirement IDs must be unique")
        return self


class CandidateFee(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str = Field(min_length=1)
    amount_type: Literal["exact", "range", "variable", "unknown"]
    amount: float | None = Field(default=None, ge=0)
    minimum_amount: float | None = Field(default=None, ge=0)
    maximum_amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    unit: str | None = Field(default=None, min_length=1)
    payer: str | None = Field(default=None, min_length=1)
    payment_method: str | None = Field(default=None, min_length=1)
    refundable: bool | None = None
    conditions: str | None = Field(default=None, min_length=1)
    citations: list[CandidateCitation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_amount(self) -> "CandidateFee":
        if self.amount_type == "exact" and (self.amount is None or self.currency is None):
            raise ValueError("exact fees require amount and currency")
        if self.amount_type == "range":
            if self.minimum_amount is None or self.maximum_amount is None or self.currency is None:
                raise ValueError("range fees require minimum, maximum, and currency")
            if self.maximum_amount < self.minimum_amount:
                raise ValueError("fee maximum cannot be lower than minimum")
        return self


class CandidateProcessingTime(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    duration_type: Literal["exact", "range", "variable", "unknown"]
    value: int | None = Field(default=None, ge=0)
    minimum_value: int | None = Field(default=None, ge=0)
    maximum_value: int | None = Field(default=None, ge=0)
    unit: Literal["hours", "calendar_days", "business_days", "weeks", "months"] | None = None
    starts_when: str | None = Field(default=None, min_length=1)
    conditions: str | None = Field(default=None, min_length=1)
    citations: list[CandidateCitation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_duration(self) -> "CandidateProcessingTime":
        if self.duration_type == "exact" and (self.value is None or self.unit is None):
            raise ValueError("exact processing time requires value and unit")
        if self.duration_type == "range":
            if self.minimum_value is None or self.maximum_value is None or self.unit is None:
                raise ValueError("processing-time range requires minimum, maximum, and unit")
            if self.maximum_value < self.minimum_value:
                raise ValueError("processing-time maximum cannot be lower than minimum")
        return self


class PublicationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    review_item_id: UUID
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    domain: DomainSlug
    topic: str | None = Field(default=None, min_length=2, max_length=120)
    language: LanguageCode
    version: CandidateVersion
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1)
    audiences: list[str] = Field(default_factory=list)
    nationalities: list[str] = Field(default_factory=list)
    residency_statuses: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    applicability_conditions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    requirements: list[CandidateRequirement] = Field(default_factory=list)
    steps: list[CandidateStep] = Field(default_factory=list)
    fees: list[CandidateFee] = Field(default_factory=list)
    processing_time: CandidateProcessingTime | None = None
    sections: list[CandidateSection] = Field(min_length=1)
    effective_from: date
    effective_until: date
    translation_of_id: UUID | None = None

    @field_validator("title", "summary")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("publication text cannot be blank")
        return value

    @field_validator("nationalities")
    @classmethod
    def nationalities_must_be_iso_country_codes(cls, value: list[str]) -> list[str]:
        if any(len(item) != 2 or not item.isascii() or not item.isupper() for item in value):
            raise ValueError("candidate nationalities must use uppercase ISO alpha-2 codes")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> "PublicationCandidate":
        if self.effective_until < self.effective_from:
            raise ValueError("effective_until cannot precede effective_from")
        maximum_until = self.effective_from + timedelta(days=FRESHNESS_DAYS_BY_DOMAIN[self.domain])
        if self.effective_until > maximum_until:
            raise ValueError(
                "effective_until exceeds the approved freshness window for this domain"
            )
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("candidate section IDs must be unique")
        for field_name in (
            "audiences",
            "nationalities",
            "residency_statuses",
            "locations",
            "applicability_conditions",
            "keywords",
        ):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"candidate {field_name} must be unique")
        for field_name in ("requirements", "steps", "fees"):
            identifiers = [item.id for item in getattr(self, field_name)]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"candidate {field_name} IDs must be unique")
        ordinals = [step.ordinal for step in self.steps]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("candidate step ordinals must be unique")
        requirement_ids = {requirement.id for requirement in self.requirements}
        unknown_requirements = {
            requirement_id
            for step in self.steps
            for requirement_id in step.requirement_ids
            if requirement_id not in requirement_ids
        }
        if unknown_requirements:
            raise ValueError("candidate steps reference unknown requirements")
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
        if artifact.topic != candidate.topic:
            raise PublicationError(
                "candidate_topic_mismatch",
                "candidate topic must match the approved extraction topic",
            )
        artifact_section_ids = [section.id for section in artifact.sections]
        candidate_section_ids = [section.id for section in candidate.sections]
        if artifact_section_ids != candidate_section_ids:
            raise PublicationError(
                "candidate_artifact_mismatch",
                "candidate sections and order must exactly match the approved artifact",
            )
        artifact_sections = {section.id: section for section in artifact.sections}
        candidate_sections = {section.id: section for section in candidate.sections}
        approved_bodies = [section.body for section in artifact.sections]
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
        structured_citations = [
            citation
            for item in [*candidate.requirements, *candidate.steps, *candidate.fees]
            for citation in item.citations
        ]
        if candidate.processing_time is not None:
            structured_citations.extend(candidate.processing_time.citations)
        for citation in structured_citations:
            if citation.source_id != source_id:
                raise PublicationError(
                    "citation_lineage_mismatch",
                    "all citations must reference the reviewed source",
                )
            if citation.quote is None:
                raise PublicationError(
                    "structured_evidence_quote_required",
                    "requirements, steps, fees, and processing time require evidence quotes",
                )
            if not any(citation.quote in body for body in approved_bodies):
                raise PublicationError(
                    "citation_quote_mismatch",
                    "structured citation quote is not present in the reviewed artifact",
                )
