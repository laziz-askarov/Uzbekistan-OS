from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.ingestion import (
    CrawlJob,
    ExtractionArtifact,
    ReviewItem,
    SourceSnapshot,
)
from app.ingestion.errors import IngestionError
from app.ingestion.types import (
    ExtractionArtifactMetadata,
    IngestionOutcome,
    JobClaim,
    JobStatus,
    ReviewItemMetadata,
    SnapshotMetadata,
)


class SqlAlchemyIngestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def claim_job(self, source_id: UUID, idempotency_key: str, max_attempts: int) -> JobClaim:
        if max_attempts < 1:
            raise IngestionError(
                "invalid_max_attempts",
                "max attempts must be positive",
                retryable=False,
            )

        job = self.session.scalar(
            select(CrawlJob)
            .where(
                CrawlJob.source_id == source_id,
                CrawlJob.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        if job is not None and job.status == JobStatus.SUCCEEDED:
            return JobClaim(
                id=job.id,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                replay=IngestionOutcome.from_dict(job.result),
            )
        if job is not None and job.status == JobStatus.RUNNING:
            raise IngestionError(
                "job_in_progress",
                "an ingestion job with this idempotency key is already running",
                retryable=True,
            )
        if job is not None and job.status in {JobStatus.DEAD_LETTERED, JobStatus.CANCELLED}:
            raise IngestionError(
                "job_terminal",
                f"ingestion job is already {job.status}",
                retryable=False,
            )

        now = datetime.now(UTC)
        if job is None:
            job = CrawlJob(
                id=uuid4(),
                source_id=source_id,
                idempotency_key=idempotency_key,
                status=JobStatus.RUNNING,
                attempt_count=1,
                max_attempts=max_attempts,
                started_at=now,
                error={},
                result={},
            )
            self.session.add(job)
        else:
            job.status = JobStatus.RUNNING
            job.attempt_count += 1
            job.started_at = now
            job.completed_at = None
            job.error = {}
        self.session.flush()
        return JobClaim(
            id=job.id,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
        )

    def latest_snapshot(self, source_id: UUID) -> SnapshotMetadata | None:
        snapshot = self.session.scalar(
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.fetched_at.desc(), SourceSnapshot.id.desc())
            .limit(1)
        )
        return self._snapshot_metadata(snapshot) if snapshot is not None else None

    def snapshot_by_sha256(
        self,
        source_id: UUID,
        sha256: str,
    ) -> SnapshotMetadata | None:
        snapshot = self.session.scalar(
            select(SourceSnapshot).where(
                SourceSnapshot.source_id == source_id,
                SourceSnapshot.sha256 == sha256,
            )
        )
        return self._snapshot_metadata(snapshot) if snapshot is not None else None

    @staticmethod
    def _snapshot_metadata(snapshot: SourceSnapshot) -> SnapshotMetadata:
        return SnapshotMetadata(
            id=snapshot.id,
            source_id=snapshot.source_id,
            storage_key=snapshot.storage_key,
            sha256=snapshot.sha256,
            normalized_sha256=snapshot.normalized_sha256,
            http_status=snapshot.http_status,
            content_type=snapshot.content_type,
            etag=snapshot.etag,
            last_modified=snapshot.last_modified,
            fetched_at=snapshot.fetched_at,
            byte_size=snapshot.byte_size,
        )

    def record_snapshot(self, snapshot: SnapshotMetadata) -> None:
        self.session.add(
            SourceSnapshot(
                id=snapshot.id,
                source_id=snapshot.source_id,
                storage_key=snapshot.storage_key,
                sha256=snapshot.sha256,
                normalized_sha256=snapshot.normalized_sha256,
                byte_size=snapshot.byte_size,
                http_status=snapshot.http_status,
                content_type=snapshot.content_type,
                etag=snapshot.etag,
                last_modified=snapshot.last_modified,
                fetched_at=snapshot.fetched_at,
            )
        )
        self.session.flush()

    def record_extraction_artifact(self, artifact: ExtractionArtifactMetadata) -> None:
        self.session.add(
            ExtractionArtifact(
                id=artifact.id,
                source_snapshot_id=artifact.source_snapshot_id,
                adapter_key=artifact.adapter_key,
                schema_version=artifact.schema_version,
                storage_key=artifact.storage_key,
                sha256=artifact.sha256,
                normalized_sha256=artifact.normalized_sha256,
                section_count=artifact.section_count,
                details=dict(artifact.details),
            )
        )
        self.session.flush()

    def enqueue_review(self, review_item: ReviewItemMetadata) -> None:
        self.session.add(
            ReviewItem(
                id=review_item.id,
                extraction_artifact_id=review_item.extraction_artifact_id,
                priority=review_item.priority,
                status="pending",
            )
        )
        self.session.flush()

    def mark_succeeded(self, job_id: UUID, outcome: IngestionOutcome) -> None:
        job = self._get_job(job_id)
        job.status = JobStatus.SUCCEEDED
        job.source_snapshot_id = outcome.snapshot_id
        job.result = outcome.as_dict()
        job.error = {}
        job.completed_at = datetime.now(UTC)
        self.session.flush()

    def mark_failed(
        self,
        job_id: UUID,
        error: Exception,
        *,
        retryable: bool,
    ) -> JobStatus:
        job = self._get_job(job_id)
        job.error = {
            "code": getattr(error, "code", "ingestion_error"),
            "message": str(error),
            "retryable": retryable,
        }
        if retryable and job.attempt_count < job.max_attempts:
            job.status = JobStatus.RETRY_SCHEDULED
            job.started_at = None
        else:
            job.status = JobStatus.DEAD_LETTERED
            job.completed_at = datetime.now(UTC)
        self.session.flush()
        return JobStatus(job.status)

    def _get_job(self, job_id: UUID) -> CrawlJob:
        job = self.session.get(CrawlJob, job_id)
        if job is None:
            raise RuntimeError(f"ingestion job does not exist: {job_id}")
        return job
