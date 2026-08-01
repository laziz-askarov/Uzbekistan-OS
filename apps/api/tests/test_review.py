from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from app.ingestion.artifacts import ExtractedSection, ExtractionArtifact
from app.ingestion.review import (
    ArtifactReference,
    AuditRecord,
    ReviewDecision,
    ReviewerContext,
    ReviewerRole,
    ReviewError,
    ReviewQueueRecord,
    ReviewRecord,
    ReviewService,
    ReviewStatus,
    SectionChangeType,
)


class MemoryReviewRepository:
    def __init__(self, record: ReviewRecord) -> None:
        self.record = record
        self.audits: list[AuditRecord] = []
        self.references: dict[UUID, ArtifactReference] = {}
        self.previous: ArtifactReference | None = None
        self.queue: tuple[ReviewQueueRecord, ...] = ()

    def list_queue(
        self,
        *,
        status: ReviewStatus | None,
        limit: int,
    ) -> tuple[ReviewQueueRecord, ...]:
        records = self.queue
        if status is not None:
            records = tuple(record for record in records if record.review.status is status)
        return records[:limit]

    def get_for_update(self, review_item_id: UUID) -> ReviewRecord | None:
        return self.record if self.record.id == review_item_id else None

    def save(self, record: ReviewRecord) -> None:
        self.record = record

    def append_audit(self, record: AuditRecord) -> None:
        self.audits.append(record)

    def artifact_for_comparison(self, artifact_id: UUID) -> ArtifactReference | None:
        return self.references.get(artifact_id)

    def previous_approved_artifact(self, artifact_id: UUID) -> ArtifactReference | None:
        del artifact_id
        return self.previous


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

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


def pending_record() -> ReviewRecord:
    return ReviewRecord(
        id=uuid4(),
        extraction_artifact_id=uuid4(),
        status=ReviewStatus.PENDING,
        priority=50,
        assigned_user_id=None,
        decision_reason=None,
        decided_at=None,
        updated_at=datetime(2026, 7, 31, tzinfo=UTC),
    )


def context(*roles: ReviewerRole, actor: UUID | None = None) -> ReviewerContext:
    return ReviewerContext(
        actor_user_id=actor or uuid4(),
        roles=frozenset(roles),
        request_id="review-request",
    )


def artifact(snapshot_id: UUID, sections: list[tuple[str, str, str]]) -> ExtractionArtifact:
    return ExtractionArtifact(
        source_id=UUID("00000000-0000-0000-0000-000000002001"),
        snapshot_id=snapshot_id,
        adapter_key="generic-html",
        media_type="text/html",
        raw_sha256="0" * 64,
        normalized_sha256="1" * 64,
        extracted_at=datetime(2026, 7, 31, tzinfo=UTC),
        sections=[
            ExtractedSection(id=section_id, heading=heading, body=body)
            for section_id, heading, body in sections
        ],
    )


def test_review_claim_and_approval_are_role_gated_and_audited() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    reviewer = context(ReviewerRole.CONTENT_REVIEWER)
    service = ReviewService(repository=repository, object_store=MemoryObjectStore())

    claimed = service.claim(reviewer, record.id)
    replayed_claim = service.claim(reviewer, record.id)
    approved = service.decide(
        reviewer,
        record.id,
        ReviewDecision.APPROVE,
        reason="Evidence and extraction verified.",
    )

    assert claimed.status is ReviewStatus.IN_REVIEW
    assert claimed.assigned_user_id == reviewer.actor_user_id
    assert replayed_claim == claimed
    assert approved.status is ReviewStatus.APPROVED
    assert approved.decision_reason == "Evidence and extraction verified."
    assert [event.action for event in repository.audits] == [
        "review.claimed",
        "review.approved",
    ]
    assert all(event.request_id == "review-request" for event in repository.audits)


def test_unprivileged_actor_cannot_claim_review_work() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    service = ReviewService(repository=repository, object_store=MemoryObjectStore())

    with pytest.raises(ReviewError, match="role is required"):
        service.claim(context(), record.id)

    assert repository.record == record
    assert repository.audits == []


def test_review_queue_is_role_gated_and_returns_source_context() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    repository.queue = (
        ReviewQueueRecord(
            review=record,
            source_id=uuid4(),
            source_title="Official entry guidance",
            source_url="https://government.example/entry",
            fetched_at=datetime(2026, 8, 1, tzinfo=UTC),
            section_count=3,
        ),
    )
    service = ReviewService(repository=repository, object_store=MemoryObjectStore())

    records = service.list_queue(
        context(ReviewerRole.CONTENT_REVIEWER),
        status=ReviewStatus.PENDING,
        limit=25,
    )

    assert records == repository.queue
    with pytest.raises(ReviewError, match="role is required"):
        service.list_queue(context())
    with pytest.raises(ReviewError, match="between 1 and 100"):
        service.list_queue(context(ReviewerRole.ADMIN), limit=101)


def test_only_assigned_reviewer_can_decide() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    assigned = context(ReviewerRole.CONTENT_REVIEWER)
    other = context(ReviewerRole.ADMIN)
    service = ReviewService(repository=repository, object_store=MemoryObjectStore())
    service.claim(assigned, record.id)

    with pytest.raises(ReviewError, match="assigned reviewer"):
        service.decide(
            other,
            record.id,
            ReviewDecision.REJECT,
            reason="Needs correction.",
        )

    assert repository.record.status is ReviewStatus.IN_REVIEW
    assert len(repository.audits) == 1


def test_artifact_comparison_reports_added_removed_and_modified_sections() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    store = MemoryObjectStore()
    current_id = record.extraction_artifact_id
    previous_id = uuid4()
    current = artifact(
        uuid4(),
        [
            ("overview", "Overview", "Updated body"),
            ("fees", "Fees", "New fee"),
        ],
    )
    previous = artifact(
        uuid4(),
        [
            ("overview", "Overview", "Old body"),
            ("documents", "Documents", "Passport"),
        ],
    )
    store.put("current.json", current.canonical_bytes())
    store.put("previous.json", previous.canonical_bytes())
    repository.references[current_id] = ArtifactReference(
        id=current_id,
        storage_key="current.json",
        sha256=sha256(current.canonical_bytes()).hexdigest(),
    )
    repository.previous = ArtifactReference(
        id=previous_id,
        storage_key="previous.json",
        sha256=sha256(previous.canonical_bytes()).hexdigest(),
    )
    service = ReviewService(repository=repository, object_store=store)

    comparison = service.compare(context(ReviewerRole.CONTENT_REVIEWER), current_id)

    assert comparison.current_artifact_id == current_id
    assert comparison.previous_artifact_id == previous_id
    assert comparison.changed is True
    assert {change.section_id: change.change_type for change in comparison.changes} == {
        "documents": SectionChangeType.REMOVED,
        "fees": SectionChangeType.ADDED,
        "overview": SectionChangeType.MODIFIED,
    }


def test_artifact_detail_verifies_checksum_before_returning_content() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    store = MemoryObjectStore()
    extracted = artifact(uuid4(), [("overview", "Overview", "Verified body")])
    store.put("current.json", extracted.canonical_bytes())
    repository.references[record.extraction_artifact_id] = ArtifactReference(
        id=record.extraction_artifact_id,
        storage_key="current.json",
        sha256=sha256(extracted.canonical_bytes()).hexdigest(),
    )

    result = ReviewService(repository=repository, object_store=store).artifact(
        context(ReviewerRole.CONTENT_REVIEWER),
        record.extraction_artifact_id,
    )

    assert result == extracted


def test_artifact_comparison_rejects_database_object_checksum_mismatch() -> None:
    record = pending_record()
    repository = MemoryReviewRepository(record)
    store = MemoryObjectStore()
    current = artifact(uuid4(), [("overview", "Overview", "Body")])
    store.put("current.json", current.canonical_bytes())
    repository.references[record.extraction_artifact_id] = ArtifactReference(
        id=record.extraction_artifact_id,
        storage_key="current.json",
        sha256="f" * 64,
    )
    service = ReviewService(repository=repository, object_store=store)

    with pytest.raises(ReviewError, match="checksum"):
        service.compare(
            context(ReviewerRole.CONTENT_REVIEWER),
            record.extraction_artifact_id,
        )
