from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.knowledge import Chunk, Document, DocumentVersion, Embedding, IndexJob
from app.knowledge.indexing import EmbeddingBatch, IndexChunk, IndexWork
from app.knowledge.lifecycle_repositories import SqlAlchemyKnowledgeLifecycleRepository


class SqlAlchemyIndexingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def claim(self, job_id: UUID, *, now: datetime) -> IndexWork | None:
        job = self.session.scalar(select(IndexJob).where(IndexJob.id == job_id).with_for_update())
        if job is None:
            raise RuntimeError("index job does not exist")
        if job.status not in {"queued", "retry_scheduled"} or job.scheduled_at > now:
            return None

        version = self.session.get(DocumentVersion, job.document_version_id)
        document = self.session.get(Document, version.document_id) if version else None
        if version is None or document is None:
            raise RuntimeError("index job document lineage is missing")
        if not SqlAlchemyKnowledgeLifecycleRepository._is_retrievable(
            document,
            version,
            on_date=now.date(),
        ):
            job.status = "cancelled"
            job.completed_at = now
            job.error = {
                "code": "document_not_retrievable",
                "message": "document became ineligible before indexing",
                "retryable": False,
            }
            self.session.flush()
            return None

        chunks = tuple(
            self.session.scalars(
                select(Chunk)
                .where(Chunk.document_version_id == version.id)
                .order_by(Chunk.ordinal)
            )
        )
        if not chunks:
            job.status = "dead_lettered"
            job.completed_at = now
            job.error = {
                "code": "document_chunks_missing",
                "message": "published document version has no chunks",
                "retryable": False,
            }
            self.session.flush()
            return None

        job.status = "running"
        job.attempt_count += 1
        job.started_at = now
        job.error = {}
        self.session.flush()
        return IndexWork(
            job_id=job.id,
            document_version_id=version.id,
            model_key=job.model_key,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            chunks=[IndexChunk(id=chunk.id, content=chunk.content) for chunk in chunks],
        )

    def complete(
        self,
        work: IndexWork,
        batch: EmbeddingBatch,
        *,
        completed_at: datetime,
    ) -> None:
        job = self._lock_running_job(work.job_id)
        for chunk, vector in zip(work.chunks, batch.vectors, strict=True):
            embedding = self.session.scalar(
                select(Embedding).where(
                    Embedding.chunk_id == chunk.id,
                    Embedding.model_key == work.model_key,
                )
            )
            if embedding is None:
                embedding = Embedding(
                    id=uuid4(),
                    chunk_id=chunk.id,
                    model_key=work.model_key,
                    dimensions=len(vector),
                    vector=vector,
                    token_count=0,
                )
                self.session.add(embedding)
            else:
                embedding.dimensions = len(vector)
                embedding.vector = vector
            embedding.token_count = max(1, len(chunk.content.split()))

        job.status = "succeeded"
        job.completed_at = completed_at
        job.token_count = batch.token_count
        job.duration_ms = batch.duration_ms
        job.cost_microusd = batch.cost_microusd
        job.error = {}
        job.result = {
            "chunk_count": len(work.chunks),
            "dimensions": len(batch.vectors[0]),
            "model_key": work.model_key,
        }
        self.session.flush()

    def fail(
        self,
        work: IndexWork,
        error: Exception,
        *,
        retry_at: datetime | None,
        failed_at: datetime,
    ) -> None:
        job = self._lock_running_job(work.job_id)
        retryable = retry_at is not None
        job.status = "retry_scheduled" if retryable else "dead_lettered"
        job.scheduled_at = retry_at or job.scheduled_at
        job.completed_at = None if retryable else failed_at
        job.error = {
            "code": getattr(error, "code", "embedding_provider_error"),
            "message": str(error),
            "retryable": retryable,
        }
        self.session.flush()

    def _lock_running_job(self, job_id: UUID) -> IndexJob:
        job = self.session.scalar(select(IndexJob).where(IndexJob.id == job_id).with_for_update())
        if job is None or job.status != "running":
            raise RuntimeError("index job is not owned by this worker")
        return job
