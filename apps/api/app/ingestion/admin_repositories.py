from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.ingestion import CrawlJob
from app.database.models.knowledge import Source
from app.ingestion.admin import (
    AdminIngestionError,
    IngestionJobRecord,
    PreparedCrawlJob,
    SourceDatabaseState,
)


class SqlAlchemyAdminIngestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def source_states(self) -> tuple[SourceDatabaseState, ...]:
        sources = tuple(self.session.scalars(select(Source).order_by(Source.title)))
        records = []
        for source in sources:
            latest = self.session.scalar(
                select(CrawlJob)
                .where(CrawlJob.source_id == source.id)
                .order_by(CrawlJob.scheduled_at.desc(), CrawlJob.id.desc())
                .limit(1)
            )
            records.append(
                SourceDatabaseState(
                    id=source.id,
                    active=source.is_active,
                    last_verified_at=source.last_verified_at,
                    latest_job_status=latest.status if latest else None,
                )
            )
        return tuple(records)

    def list_jobs(self, *, limit: int) -> tuple[IngestionJobRecord, ...]:
        rows = self.session.execute(
            select(CrawlJob, Source.title)
            .join(Source, Source.id == CrawlJob.source_id)
            .order_by(CrawlJob.scheduled_at.desc(), CrawlJob.id.desc())
            .limit(limit)
        )
        return tuple(self._job_record(job, title) for job, title in rows)

    def prepare_crawl_job(
        self,
        source_id: UUID,
        idempotency_key: str,
        *,
        max_attempts: int,
        scheduled_at: datetime,
    ) -> PreparedCrawlJob:
        source = self.session.get(Source, source_id)
        if source is None:
            raise AdminIngestionError(
                "source_not_synchronized",
                "configured source is not synchronized to the database",
            )
        job = self.session.scalar(
            select(CrawlJob)
            .where(
                CrawlJob.source_id == source_id,
                CrawlJob.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        if job is not None:
            if job.max_attempts != max_attempts:
                raise AdminIngestionError(
                    "ingestion_job_conflict",
                    "idempotency key is already linked to different retry settings",
                )
            return PreparedCrawlJob(record=self._job_record(job, source.title), created=False)
        job = CrawlJob(
            id=uuid4(),
            source_id=source_id,
            idempotency_key=idempotency_key,
            status="queued",
            attempt_count=0,
            max_attempts=max_attempts,
            scheduled_at=scheduled_at,
            error={},
            result={},
        )
        self.session.add(job)
        self.session.flush()
        return PreparedCrawlJob(record=self._job_record(job, source.title), created=True)

    @staticmethod
    def _job_record(job: CrawlJob, source_title: str) -> IngestionJobRecord:
        return IngestionJobRecord(
            id=job.id,
            source_id=job.source_id,
            source_title=source_title,
            idempotency_key=job.idempotency_key,
            status=job.status,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            scheduled_at=job.scheduled_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_code=str(job.error.get("code")) if job.error.get("code") else None,
            error_message=(
                str(job.error.get("message")) if job.error.get("message") else None
            ),
        )
