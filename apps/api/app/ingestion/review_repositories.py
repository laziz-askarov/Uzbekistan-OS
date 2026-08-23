from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.models.audit import AuditEvent
from app.database.models.ingestion import ExtractionArtifact, ReviewItem, SourceSnapshot
from app.database.models.knowledge import Source
from app.ingestion.review import (
    ArtifactReference,
    AuditRecord,
    ReviewQueueRecord,
    ReviewRecord,
    ReviewStatus,
)


class SqlAlchemyReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_queue(
        self,
        *,
        status: ReviewStatus | None,
        limit: int,
    ) -> tuple[ReviewQueueRecord, ...]:
        statement = (
            select(ReviewItem, ExtractionArtifact, SourceSnapshot, Source)
            .join(
                ExtractionArtifact,
                ExtractionArtifact.id == ReviewItem.extraction_artifact_id,
            )
            .join(
                SourceSnapshot,
                SourceSnapshot.id == ExtractionArtifact.source_snapshot_id,
            )
            .join(Source, Source.id == SourceSnapshot.source_id)
            .order_by(ReviewItem.priority.desc(), ReviewItem.created_at.asc(), ReviewItem.id.asc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(ReviewItem.status == status.value)
        rows = self.session.execute(statement).all()
        return tuple(
            ReviewQueueRecord(
                review=self._to_record(review_item),
                source_id=source.id,
                source_title=source.title,
                source_url=source.url,
                fetched_at=snapshot.fetched_at,
                section_count=artifact.section_count,
                topic=(str(artifact.details["topic"]) if artifact.details.get("topic") else None),
            )
            for review_item, artifact, snapshot, source in rows
        )

    def get_for_update(self, review_item_id: UUID) -> ReviewRecord | None:
        item = self.session.scalar(
            select(ReviewItem).where(ReviewItem.id == review_item_id).with_for_update()
        )
        return self._to_record(item) if item else None

    def save(self, record: ReviewRecord) -> None:
        item = self.session.get(ReviewItem, record.id)
        if item is None:
            raise RuntimeError(f"review item does not exist: {record.id}")
        item.status = record.status
        item.assigned_user_id = record.assigned_user_id
        item.decision_reason = record.decision_reason
        item.decided_at = record.decided_at
        item.updated_at = record.updated_at
        self.session.flush()

    def append_audit(self, record: AuditRecord) -> None:
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=record.actor_user_id,
                action=record.action,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                request_id=record.request_id,
                payload=record.payload,
                occurred_at=record.occurred_at,
            )
        )
        self.session.flush()

    def artifact_for_comparison(self, artifact_id: UUID) -> ArtifactReference | None:
        artifact = self.session.get(ExtractionArtifact, artifact_id)
        return self._artifact_reference(artifact) if artifact else None

    def previous_approved_artifact(self, artifact_id: UUID) -> ArtifactReference | None:
        current = self.session.get(ExtractionArtifact, artifact_id)
        if current is None:
            return None
        current_snapshot = self.session.get(SourceSnapshot, current.source_snapshot_id)
        if current_snapshot is None:
            return None

        previous = self.session.scalar(
            select(ExtractionArtifact)
            .join(
                SourceSnapshot,
                SourceSnapshot.id == ExtractionArtifact.source_snapshot_id,
            )
            .join(
                ReviewItem,
                ReviewItem.extraction_artifact_id == ExtractionArtifact.id,
            )
            .where(
                SourceSnapshot.source_id == current_snapshot.source_id,
                ExtractionArtifact.id != current.id,
                ReviewItem.status == ReviewStatus.APPROVED,
                or_(
                    SourceSnapshot.fetched_at < current_snapshot.fetched_at,
                    and_(
                        SourceSnapshot.fetched_at == current_snapshot.fetched_at,
                        SourceSnapshot.id < current_snapshot.id,
                    ),
                ),
            )
            .order_by(SourceSnapshot.fetched_at.desc(), SourceSnapshot.id.desc())
            .limit(1)
        )
        return self._artifact_reference(previous) if previous else None

    @staticmethod
    def _to_record(item: ReviewItem) -> ReviewRecord:
        return ReviewRecord(
            id=item.id,
            extraction_artifact_id=item.extraction_artifact_id,
            status=ReviewStatus(item.status),
            priority=item.priority,
            assigned_user_id=item.assigned_user_id,
            decision_reason=item.decision_reason,
            decided_at=item.decided_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _artifact_reference(artifact: ExtractionArtifact) -> ArtifactReference:
        return ArtifactReference(
            id=artifact.id,
            storage_key=artifact.storage_key,
            sha256=artifact.sha256,
        )
