from datetime import datetime, timedelta
from math import isfinite
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class IndexChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    content: str = Field(min_length=1)


class IndexWork(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    document_version_id: UUID
    model_key: str
    attempt_count: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    chunks: list[IndexChunk] = Field(min_length=1)


class EmbeddingBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vectors: list[list[float]] = Field(min_length=1)
    token_count: int = Field(ge=0)
    duration_ms: int = Field(ge=0)
    cost_microusd: int = Field(ge=0)


class IndexingOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    status: str
    attempt_count: int
    retry_at: datetime | None = None


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str], *, model_key: str) -> EmbeddingBatch: ...


class IndexingRepository(Protocol):
    def complete(
        self,
        work: IndexWork,
        batch: EmbeddingBatch,
        *,
        completed_at: datetime,
    ) -> None: ...

    def fail(
        self,
        work: IndexWork,
        error: Exception,
        *,
        retry_at: datetime | None,
        failed_at: datetime,
    ) -> None: ...


class IndexingService:
    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        repository: IndexingRepository,
        retry_base_seconds: int = 30,
        retry_max_seconds: int = 900,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds

    def process(self, work: IndexWork, *, now: datetime) -> IndexingOutcome:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("indexing time must be timezone-aware")
        try:
            batch = self.provider.embed(
                [chunk.content for chunk in work.chunks],
                model_key=work.model_key,
            )
            self._validate_batch(work, batch)
            self.repository.complete(work, batch, completed_at=now)
            return IndexingOutcome(
                job_id=work.job_id,
                status="succeeded",
                attempt_count=work.attempt_count,
            )
        except Exception as error:
            retry_at = self._retry_at(work, error, now=now)
            self.repository.fail(
                work,
                error,
                retry_at=retry_at,
                failed_at=now,
            )
            return IndexingOutcome(
                job_id=work.job_id,
                status="retry_scheduled" if retry_at else "dead_lettered",
                attempt_count=work.attempt_count,
                retry_at=retry_at,
            )

    @staticmethod
    def _validate_batch(work: IndexWork, batch: EmbeddingBatch) -> None:
        if len(batch.vectors) != len(work.chunks):
            raise EmbeddingProviderError(
                "embedding_count_mismatch",
                "embedding provider returned a different vector count",
                retryable=False,
            )
        dimensions = {len(vector) for vector in batch.vectors}
        if len(dimensions) != 1 or not dimensions or next(iter(dimensions)) <= 0:
            raise EmbeddingProviderError(
                "embedding_dimensions_invalid",
                "embedding vectors must share a positive dimension",
                retryable=False,
            )
        if any(not isfinite(value) for vector in batch.vectors for value in vector):
            raise EmbeddingProviderError(
                "embedding_value_invalid",
                "embedding vectors must contain only finite values",
                retryable=False,
            )

    def _retry_at(self, work: IndexWork, error: Exception, *, now: datetime) -> datetime | None:
        retryable = isinstance(error, EmbeddingProviderError) and error.retryable
        if not retryable or work.attempt_count >= work.max_attempts:
            return None
        delay = min(
            self.retry_base_seconds * (2 ** (work.attempt_count - 1)),
            self.retry_max_seconds,
        )
        return now + timedelta(seconds=delay)
