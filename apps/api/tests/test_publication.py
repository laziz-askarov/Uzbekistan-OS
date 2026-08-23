from dataclasses import replace
from datetime import UTC, date, datetime
from hashlib import sha256
from json import load
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.artifacts import ExtractedSection, ExtractionArtifact
from app.knowledge.publication import (
    CandidateCitation,
    CandidateFee,
    CandidateProcessingTime,
    CandidateRequirement,
    CandidateSection,
    CandidateStep,
    CandidateVersion,
    PublicationCandidate,
    PublicationError,
    PublicationResult,
    PublicationService,
    ReviewedLineage,
)
from app.knowledge.publication_repositories import SqlAlchemyPublicationRepository

ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_SCHEMA = ROOT / "packages/knowledge/schemas/knowledge-document.schema.json"
PUBLICATION_TEMPLATE = ROOT / "packages/knowledge/examples/publication-candidate-template.json"
FILLED_PUBLICATION_EXAMPLE = (
    ROOT / "packages/knowledge/examples/filled-publication-candidate.example.json"
)
FILLED_DOCUMENT_EXAMPLE = (
    ROOT / "packages/knowledge/examples/filled-knowledge-document.example.json"
)
SOURCE_ID = UUID("00000000-0000-0000-0000-000000002001")


class MemoryObjectStore:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects

    def put(
        self,
        storage_key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        del content_type
        self.objects[storage_key] = content

    def get(self, storage_key: str) -> bytes:
        return self.objects[storage_key]


class MemoryPublicationRepository:
    def __init__(self, lineage: ReviewedLineage | None) -> None:
        self.lineage = lineage
        self.published: list[PublicationCandidate] = []

    def lock_review_lineage(self, review_item_id):
        if self.lineage and self.lineage.review_item_id == review_item_id:
            return self.lineage
        return None

    def publish_candidate(
        self,
        candidate,
        lineage,
        principal,
        *,
        published_at,
    ) -> PublicationResult:
        del lineage, principal
        self.published.append(candidate)
        return PublicationResult(
            publication_id=uuid4(),
            document_id=uuid4(),
            document_version_id=uuid4(),
            candidate_sha256=candidate.sha256,
            published_at=published_at,
        )


def approved_artifact() -> ExtractionArtifact:
    return ExtractionArtifact(
        source_id=SOURCE_ID,
        snapshot_id=uuid4(),
        adapter_key="generic-html",
        media_type="text/html",
        raw_sha256="0" * 64,
        normalized_sha256="1" * 64,
        extracted_at=datetime(2026, 7, 31, tzinfo=UTC),
        sections=[
            ExtractedSection(
                id="overview",
                heading="Overview",
                body="Entry guidance from the reviewed source.",
            )
        ],
    )


def candidate(review_item_id: UUID, *, source_id: UUID = SOURCE_ID) -> PublicationCandidate:
    return PublicationCandidate(
        review_item_id=review_item_id,
        slug="reviewed-entry-guidance",
        domain="immigration",
        language="en",
        version=CandidateVersion(major=1),
        title="Reviewed entry guidance",
        summary="A reviewed non-production publication candidate.",
        audiences=["international-visitor"],
        keywords=["entry"],
        sections=[
            CandidateSection(
                id="overview",
                heading="Overview",
                body="Entry guidance from the reviewed source.",
                citations=[
                    CandidateCitation(
                        source_id=source_id,
                        locator="Overview section",
                        quote="Entry guidance",
                    )
                ],
            )
        ],
        effective_from=date(2026, 7, 31),
        effective_until=date(2026, 8, 30),
    )


def test_candidate_requires_bounded_domain_freshness() -> None:
    review_item_id = uuid4()
    payload = candidate(review_item_id).model_dump(mode="json")

    with pytest.raises(ValueError, match="freshness window"):
        PublicationCandidate.model_validate(
            {**payload, "effective_until": "2026-09-01"}
        )

    with pytest.raises(ValueError, match="valid date"):
        PublicationCandidate.model_validate({**payload, "effective_until": None})


def setup_publication():
    artifact = approved_artifact()
    artifact_bytes = artifact.canonical_bytes()
    review_item_id = uuid4()
    lineage = ReviewedLineage(
        review_item_id=review_item_id,
        review_status="approved",
        reviewed_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        source_id=SOURCE_ID,
        snapshot_sha256=artifact.raw_sha256,
        artifact_storage_key="artifact.json",
        artifact_sha256=sha256(artifact_bytes).hexdigest(),
    )
    repository = MemoryPublicationRepository(lineage)
    service = PublicationService(
        repository=repository,
        object_store=MemoryObjectStore({"artifact.json": artifact_bytes}),
    )
    principal = AuthenticatedPrincipal(
        id=uuid4(),
        roles=frozenset({"knowledge_publisher"}),
        request_id="publication-request",
    )
    return service, repository, principal, candidate(review_item_id)


def test_approved_evidence_can_be_published_by_publisher_role() -> None:
    service, repository, principal, publication_candidate = setup_publication()

    result = service.publish(
        principal,
        publication_candidate,
        published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
    )

    assert result.candidate_sha256 == publication_candidate.sha256
    assert repository.published == [publication_candidate]


def test_checked_in_publication_candidate_template_matches_runtime_model() -> None:
    with PUBLICATION_TEMPLATE.open(encoding="utf-8") as stream:
        template = load(stream)

    parsed = PublicationCandidate.model_validate(template)

    assert parsed.language == "uz"
    assert parsed.nationalities == []
    assert parsed.requirements[0].id == "identity-document"
    assert parsed.steps[0].requirement_ids == ["identity-document"]
    assert parsed.fees[0].amount_type == "unknown"
    assert parsed.processing_time is not None


def test_filled_publication_and_document_examples_match_contracts() -> None:
    with FILLED_PUBLICATION_EXAMPLE.open(encoding="utf-8") as stream:
        candidate_example = load(stream)
    with FILLED_DOCUMENT_EXAMPLE.open(encoding="utf-8") as stream:
        document_example = load(stream)
    with KNOWLEDGE_SCHEMA.open(encoding="utf-8") as stream:
        schema = load(stream)

    candidate = PublicationCandidate.model_validate(candidate_example)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document_example)

    assert candidate.slug == document_example["slug"]
    assert candidate.version.model_dump() == document_example["version"]
    assert [section.model_dump(mode="json") for section in candidate.sections] == document_example[
        "sections"
    ]


def test_reviewer_role_alone_cannot_publish() -> None:
    service, repository, principal, publication_candidate = setup_publication()
    reviewer = replace(principal, roles=frozenset({"content_reviewer"}))

    with pytest.raises(PublicationError, match="publisher"):
        service.publish(
            reviewer,
            publication_candidate,
            published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
        )

    assert repository.published == []


def test_unapproved_review_cannot_be_published() -> None:
    service, repository, principal, publication_candidate = setup_publication()
    repository.lineage = repository.lineage.model_copy(
        update={"review_status": "in_review", "reviewed_at": None}
    )

    with pytest.raises(PublicationError, match="approved extraction review"):
        service.publish(
            principal,
            publication_candidate,
            published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
        )

    assert repository.published == []


def test_candidate_must_match_reviewed_artifact_and_source() -> None:
    service, repository, principal, publication_candidate = setup_publication()
    mismatched = publication_candidate.model_copy(
        update={
            "sections": [
                publication_candidate.sections[0].model_copy(update={"body": "Changed body"})
            ]
        }
    )

    with pytest.raises(PublicationError, match="differs"):
        service.publish(
            principal,
            mismatched,
            published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
        )
    assert repository.published == []

    wrong_source = candidate(publication_candidate.review_item_id, source_id=uuid4())
    with pytest.raises(PublicationError, match="reviewed source"):
        service.publish(
            principal,
            wrong_source,
            published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
        )


def test_candidate_section_order_must_match_reviewed_artifact() -> None:
    artifact = approved_artifact().model_copy(
        update={
            "sections": [
                *approved_artifact().sections,
                ExtractedSection(
                    id="requirements",
                    heading="Requirements",
                    body="Bring the listed evidence.",
                ),
            ]
        }
    )
    publication_candidate = candidate(uuid4()).model_copy(
        update={
            "sections": [
                CandidateSection(
                    id="requirements",
                    heading="Requirements",
                    body="Bring the listed evidence.",
                    citations=[
                        CandidateCitation(
                            source_id=SOURCE_ID,
                            locator="Requirements section",
                        )
                    ],
                ),
                *candidate(uuid4()).sections,
            ]
        }
    )

    with pytest.raises(PublicationError, match="sections and order"):
        PublicationService._validate_evidence(
            publication_candidate,
            artifact,
            SOURCE_ID,
        )


def test_publication_source_must_be_approved_active_and_official() -> None:
    organization = SimpleNamespace(is_active=True, is_official=True)
    pending_source = SimpleNamespace(is_active=True, crawl_policy="pending_review")

    with pytest.raises(PublicationError, match="not approved for publication"):
        SqlAlchemyPublicationRepository._ensure_source_eligible(
            pending_source,
            organization,
        )

    approved_source = SimpleNamespace(is_active=True, crawl_policy="manual_only")
    unofficial = SimpleNamespace(is_active=True, is_official=False)
    with pytest.raises(PublicationError, match="active and official"):
        SqlAlchemyPublicationRepository._ensure_source_eligible(
            approved_source,
            unofficial,
        )


def test_same_publication_replays_but_changed_candidate_conflicts() -> None:
    service, repository, principal, publication_candidate = setup_publication()
    existing = PublicationResult(
        publication_id=uuid4(),
        document_id=uuid4(),
        document_version_id=uuid4(),
        candidate_sha256=publication_candidate.sha256,
        published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
    )
    repository.lineage = repository.lineage.model_copy(update={"existing_publication": existing})

    replay = service.publish(
        principal,
        publication_candidate,
        published_at=datetime(2026, 7, 31, 14, tzinfo=UTC),
    )

    assert replay == existing
    assert repository.published == []

    changed = publication_candidate.model_copy(update={"title": "Changed title"})
    with pytest.raises(PublicationError, match="different publication candidate"):
        service.publish(
            principal,
            changed,
            published_at=datetime(2026, 7, 31, 14, tzinfo=UTC),
        )


def test_generated_knowledge_content_matches_canonical_schema() -> None:
    _, repository, _, publication_candidate = setup_publication()
    citation = CandidateCitation(
        source_id=SOURCE_ID,
        locator="Overview section",
        quote="Entry guidance",
    )
    publication_candidate = publication_candidate.model_copy(
        update={
            "nationalities": ["US"],
            "residency_statuses": ["non-resident"],
            "locations": ["Tashkent"],
            "applicability_conditions": ["Fixture only"],
            "requirements": [
                CandidateRequirement(
                    id="passport",
                    title="Passport",
                    description="Entry guidance requires a passport.",
                    mandatory=True,
                    citations=[citation],
                )
            ],
            "steps": [
                CandidateStep(
                    id="submit-passport",
                    ordinal=1,
                    title="Submit passport",
                    description="Present the passport.",
                    requirement_ids=["passport"],
                    citations=[citation],
                )
            ],
            "fees": [
                CandidateFee(
                    id="application-fee",
                    label="Application fee",
                    amount_type="exact",
                    amount=0,
                    currency="UZS",
                    unit="application",
                    payer="applicant",
                    citations=[citation],
                )
            ],
            "processing_time": CandidateProcessingTime(
                duration_type="unknown",
                conditions="Fixture only",
                citations=[citation],
            ),
        }
    )
    lineage = repository.lineage
    document_id = uuid4()
    snapshot = SimpleNamespace(
        fetched_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        sha256="0" * 64,
    )
    content = SqlAlchemyPublicationRepository._knowledge_content(
        publication_candidate,
        lineage,
        document_id,
        SimpleNamespace(name="Test source organization"),
        SimpleNamespace(
            id=SOURCE_ID,
            title="Reviewed source",
            url="https://government.example/source",
        ),
        snapshot,
        datetime(2026, 7, 31, 13, tzinfo=UTC),
    )
    with KNOWLEDGE_SCHEMA.open(encoding="utf-8") as stream:
        schema = load(stream)

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(content)
    assert content["applicability"]["nationalities"] == ["US"]
    assert content["requirements"][0]["id"] == "passport"
    assert content["fees"][0]["currency"] == "UZS"
    assert content["published_at"] == "2026-07-31T13:00:00+00:00"


def test_candidate_rejects_invalid_structured_content() -> None:
    with pytest.raises(ValueError, match="ISO alpha-2"):
        PublicationCandidate.model_validate(
            candidate(uuid4()).model_dump(mode="json") | {"nationalities": ["USA"]}
        )

    with pytest.raises(ValueError, match="unknown requirements"):
        PublicationCandidate.model_validate(
            candidate(uuid4()).model_dump(mode="json")
            | {
                "steps": [
                    {
                        "id": "submit",
                        "ordinal": 1,
                        "title": "Submit",
                        "description": "Submit evidence.",
                        "requirement_ids": ["missing"],
                        "citations": [
                            {
                                "source_id": str(SOURCE_ID),
                                "locator": "Overview section",
                            }
                        ],
                    }
                ]
            }
        )
