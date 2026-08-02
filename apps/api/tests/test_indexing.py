from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.knowledge.indexing import (
    EmbeddingBatch,
    EmbeddingProviderError,
    IndexChunk,
    IndexingService,
    IndexWork,
)


class StubProvider:
    def __init__(self, result) -> None:
        self.result = result

    def embed(self, texts, *, model_key):
        assert texts == ["First reviewed chunk.", "Second reviewed chunk."]
        assert model_key == "configured-embedding-role"
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class MemoryIndexingRepository:
    def __init__(self) -> None:
        self.completed = []
        self.failed = []

    def complete(self, work, batch, *, completed_at):
        self.completed.append((work, batch, completed_at))

    def fail(self, work, error, *, retry_at, failed_at):
        self.failed.append((work, error, retry_at, failed_at))


def work(*, attempt_count: int = 1, max_attempts: int = 3) -> IndexWork:
    return IndexWork(
        job_id=uuid4(),
        document_version_id=uuid4(),
        model_key="configured-embedding-role",
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        chunks=[
            IndexChunk(id=uuid4(), content="First reviewed chunk."),
            IndexChunk(id=uuid4(), content="Second reviewed chunk."),
        ],
    )


def test_indexing_records_provider_cost_latency_and_tokens() -> None:
    repository = MemoryIndexingRepository()
    batch = EmbeddingBatch(
        vectors=[[0.1, 0.2], [0.3, 0.4]],
        token_count=8,
        duration_ms=42,
        cost_microusd=17,
    )
    service = IndexingService(provider=StubProvider(batch), repository=repository)
    now = datetime(2026, 8, 1, tzinfo=UTC)

    outcome = service.process(work(), now=now)

    assert outcome.status == "succeeded"
    assert repository.completed[0][1] == batch
    assert repository.completed[0][2] == now
    assert repository.failed == []


def test_transient_index_failure_uses_bounded_exponential_retry() -> None:
    repository = MemoryIndexingRepository()
    service = IndexingService(
        provider=StubProvider(
            EmbeddingProviderError("provider_timeout", "provider timed out", retryable=True)
        ),
        repository=repository,
        retry_base_seconds=30,
        retry_max_seconds=60,
    )
    now = datetime(2026, 8, 1, tzinfo=UTC)

    retry = service.process(work(attempt_count=2), now=now)
    exhausted = service.process(work(attempt_count=3), now=now)

    assert retry.status == "retry_scheduled"
    assert retry.retry_at == now + timedelta(seconds=60)
    assert exhausted.status == "dead_lettered"
    assert exhausted.retry_at is None


def test_invalid_embedding_batch_is_dead_lettered_without_retry() -> None:
    repository = MemoryIndexingRepository()
    service = IndexingService(
        provider=StubProvider(
            EmbeddingBatch(
                vectors=[[0.1, 0.2]],
                token_count=4,
                duration_ms=10,
                cost_microusd=2,
            )
        ),
        repository=repository,
    )

    outcome = service.process(work(), now=datetime(2026, 8, 1, tzinfo=UTC))

    assert outcome.status == "dead_lettered"
    assert repository.completed == []
    assert repository.failed[0][1].code == "embedding_count_mismatch"
