from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from app.ingestion.artifacts import ExtractionArtifact
from app.ingestion.ports import SnapshotStore


class ReviewerRole(StrEnum):
    CONTENT_REVIEWER = "content_reviewer"
    ADMIN = "admin"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class SectionChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ReviewError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReviewerContext:
    actor_user_id: UUID
    roles: frozenset[ReviewerRole]
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    id: UUID
    extraction_artifact_id: UUID
    status: ReviewStatus
    priority: int
    assigned_user_id: UUID | None
    decision_reason: str | None
    decided_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewQueueRecord:
    review: ReviewRecord
    source_id: UUID
    source_title: str
    source_url: str
    fetched_at: datetime
    section_count: int
    topic: str | None = None
    filename: str | None = None
    manual_upload: bool = False
    manual_correction: bool = False


@dataclass(frozen=True, slots=True)
class AuditRecord:
    actor_user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    request_id: str | None
    payload: dict[str, object]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    id: UUID
    storage_key: str
    sha256: str


@dataclass(frozen=True, slots=True)
class SectionChange:
    section_id: str
    change_type: SectionChangeType
    previous_heading: str | None
    current_heading: str | None


@dataclass(frozen=True, slots=True)
class ArtifactComparison:
    current_artifact_id: UUID
    previous_artifact_id: UUID | None
    changes: tuple[SectionChange, ...]

    @property
    def changed(self) -> bool:
        return any(change.change_type is not SectionChangeType.UNCHANGED for change in self.changes)


class ReviewRepository(Protocol):
    def list_queue(
        self,
        *,
        status: ReviewStatus | None,
        limit: int,
    ) -> tuple[ReviewQueueRecord, ...]: ...

    def get_for_update(self, review_item_id: UUID) -> ReviewRecord | None: ...

    def save(self, record: ReviewRecord) -> None: ...

    def append_audit(self, record: AuditRecord) -> None: ...

    def artifact_for_comparison(self, artifact_id: UUID) -> ArtifactReference | None: ...

    def previous_approved_artifact(self, artifact_id: UUID) -> ArtifactReference | None: ...


class ReviewService:
    def __init__(self, *, repository: ReviewRepository, object_store: SnapshotStore) -> None:
        self.repository = repository
        self.object_store = object_store

    def list_queue(
        self,
        context: ReviewerContext,
        *,
        status: ReviewStatus | None = None,
        limit: int = 50,
    ) -> tuple[ReviewQueueRecord, ...]:
        self._authorize(context)
        if not 1 <= limit <= 100:
            raise ReviewError(
                "invalid_review_limit",
                "review queue limit must be between 1 and 100",
            )
        return self.repository.list_queue(status=status, limit=limit)

    def artifact(self, context: ReviewerContext, artifact_id: UUID) -> ExtractionArtifact:
        self._authorize(context)
        reference = self.repository.artifact_for_comparison(artifact_id)
        if reference is None:
            raise ReviewError("artifact_not_found", "extraction artifact does not exist")
        return self._load_artifact(reference)

    def claim(self, context: ReviewerContext, review_item_id: UUID) -> ReviewRecord:
        self._authorize(context)
        record = self._get(review_item_id)
        if (
            record.status is ReviewStatus.IN_REVIEW
            and record.assigned_user_id == context.actor_user_id
        ):
            return record
        if record.status is not ReviewStatus.PENDING:
            raise ReviewError(
                "invalid_review_transition",
                f"cannot claim a review item in {record.status} status",
            )

        now = datetime.now(UTC)
        claimed = replace(
            record,
            status=ReviewStatus.IN_REVIEW,
            assigned_user_id=context.actor_user_id,
            updated_at=now,
        )
        self.repository.save(claimed)
        self._audit(context, claimed, "review.claimed", record.status, claimed.status, now)
        return claimed

    def decide(
        self,
        context: ReviewerContext,
        review_item_id: UUID,
        decision: ReviewDecision,
        *,
        reason: str,
    ) -> ReviewRecord:
        self._authorize(context)
        cleaned_reason = reason.strip()
        if not cleaned_reason or len(cleaned_reason) > 2000:
            raise ReviewError(
                "invalid_decision_reason",
                "decision reason must contain between 1 and 2000 characters",
            )

        record = self._get(review_item_id)
        if record.status is not ReviewStatus.IN_REVIEW:
            raise ReviewError(
                "invalid_review_transition",
                f"cannot decide a review item in {record.status} status",
            )
        if record.assigned_user_id != context.actor_user_id:
            raise ReviewError(
                "review_not_assigned",
                "only the assigned reviewer may decide this item",
            )

        target = (
            ReviewStatus.APPROVED if decision is ReviewDecision.APPROVE else ReviewStatus.REJECTED
        )
        now = datetime.now(UTC)
        decided = replace(
            record,
            status=target,
            decision_reason=cleaned_reason,
            decided_at=now,
            updated_at=now,
        )
        self.repository.save(decided)
        self._audit(context, decided, f"review.{target.value}", record.status, target, now)
        return decided

    def compare(self, context: ReviewerContext, artifact_id: UUID) -> ArtifactComparison:
        self._authorize(context)
        current_reference = self.repository.artifact_for_comparison(artifact_id)
        if current_reference is None:
            raise ReviewError("artifact_not_found", "extraction artifact does not exist")
        previous_reference = self.repository.previous_approved_artifact(artifact_id)

        current = self._load_artifact(current_reference)
        previous = self._load_artifact(previous_reference) if previous_reference else None
        return compare_artifacts(
            current,
            previous,
            current_artifact_id=current_reference.id,
            previous_artifact_id=previous_reference.id if previous_reference else None,
        )

    def _get(self, review_item_id: UUID) -> ReviewRecord:
        record = self.repository.get_for_update(review_item_id)
        if record is None:
            raise ReviewError("review_not_found", "review item does not exist")
        return record

    def _load_artifact(self, reference: ArtifactReference) -> ExtractionArtifact:
        content = self.object_store.get(reference.storage_key)
        if sha256(content).hexdigest() != reference.sha256:
            raise ReviewError(
                "artifact_integrity_failure",
                "extraction artifact checksum does not match database lineage",
            )
        return ExtractionArtifact.model_validate_json(content)

    @staticmethod
    def _authorize(context: ReviewerContext) -> None:
        if not context.roles.intersection({ReviewerRole.CONTENT_REVIEWER, ReviewerRole.ADMIN}):
            raise ReviewError(
                "review_forbidden",
                "reviewer or administrator role is required",
            )

    def _audit(
        self,
        context: ReviewerContext,
        record: ReviewRecord,
        action: str,
        previous_status: ReviewStatus,
        current_status: ReviewStatus,
        occurred_at: datetime,
    ) -> None:
        self.repository.append_audit(
            AuditRecord(
                actor_user_id=context.actor_user_id,
                action=action,
                entity_type="ingestion.review_item",
                entity_id=record.id,
                request_id=context.request_id,
                payload={
                    "extraction_artifact_id": str(record.extraction_artifact_id),
                    "previous_status": previous_status.value,
                    "current_status": current_status.value,
                    "decision_reason_sha256": (
                        sha256(record.decision_reason.encode()).hexdigest()
                        if record.decision_reason
                        else None
                    ),
                },
                occurred_at=occurred_at,
            )
        )


def compare_artifacts(
    current: ExtractionArtifact,
    previous: ExtractionArtifact | None,
    *,
    current_artifact_id: UUID | None = None,
    previous_artifact_id: UUID | None = None,
) -> ArtifactComparison:
    current_sections = {section.id: section for section in current.sections}
    previous_sections = {section.id: section for section in previous.sections} if previous else {}
    changes: list[SectionChange] = []

    for section_id in sorted(current_sections.keys() | previous_sections.keys()):
        current_section = current_sections.get(section_id)
        previous_section = previous_sections.get(section_id)
        if previous_section is None:
            change_type = SectionChangeType.ADDED
        elif current_section is None:
            change_type = SectionChangeType.REMOVED
        elif (
            current_section.heading != previous_section.heading
            or current_section.body != previous_section.body
        ):
            change_type = SectionChangeType.MODIFIED
        else:
            change_type = SectionChangeType.UNCHANGED
        changes.append(
            SectionChange(
                section_id=section_id,
                change_type=change_type,
                previous_heading=previous_section.heading if previous_section else None,
                current_heading=current_section.heading if current_section else None,
            )
        )

    return ArtifactComparison(
        current_artifact_id=current_artifact_id or current.snapshot_id,
        previous_artifact_id=(
            (previous_artifact_id or previous.snapshot_id) if previous is not None else None
        ),
        changes=tuple(changes),
    )
