from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ingestion.errors import IngestionError
from app.ingestion.models import CrawlPolicy, RegistryStatus
from app.ingestion.queue import (
    IngestionTask,
    QueueDelivery,
    RedisStreamIngestionQueue,
)
from app.ingestion.registry import load_source_registry
from app.ingestion.worker import IngestionWorker
from app.worker import enqueue_source

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "data/sources/registry.development.json"


def approved_registry():
    registry = load_source_registry(REGISTRY_PATH)
    approved = registry.sources[0].model_copy(
        update={
            "organization": registry.sources[0].organization.model_copy(
                update={"is_official": True}
            ),
            "crawl_policy": CrawlPolicy.ALLOWED,
            "status": RegistryStatus.APPROVED,
            "owner": "content-team",
            "reviewed_at": datetime(2026, 8, 1, tzinfo=UTC),
            "production_eligible": True,
        }
    )
    return registry.model_copy(update={"sources": [approved]})


def task(*, attempt: int = 1, max_attempts: int = 3) -> IngestionTask:
    return IngestionTask(
        source_id=approved_registry().sources[0].id,
        idempotency_key="scheduled:2026-08-01",
        attempt=attempt,
        max_attempts=max_attempts,
        enqueued_at=datetime(2026, 8, 1, tzinfo=UTC),
    )


def delivery(message: IngestionTask | None = None) -> QueueDelivery:
    queued = message or task()
    return QueueDelivery(
        message_id="1-0",
        raw_payload=queued.canonical_json(),
        task=queued,
    )


class MemoryQueue:
    def __init__(self, deliveries: list[QueueDelivery] | None = None) -> None:
        self.deliveries = deliveries or []
        self.published: list[IngestionTask] = []
        self.acknowledged: list[str] = []
        self.retries: list[tuple[QueueDelivery, IngestionTask, timedelta]] = []
        self.dead_letters: list[tuple[QueueDelivery, str, str]] = []
        self.promotions = 0

    def publish(self, message: IngestionTask) -> str:
        self.published.append(message)
        return "2-0"

    def publish_scheduled(
        self,
        message: IngestionTask,
        *,
        deduplication_ttl: timedelta,
    ) -> str | None:
        del deduplication_ttl
        return self.publish(message)

    def promote_due(self, *, now: datetime, limit: int = 100) -> int:
        del now, limit
        self.promotions += 1
        return 0

    def reserve(self, *, block_ms: int) -> QueueDelivery | None:
        del block_ms
        return self.deliveries.pop(0) if self.deliveries else None

    def reclaim_stale(self, *, min_idle_ms: int) -> QueueDelivery | None:
        del min_idle_ms
        return None

    def acknowledge(self, queued: QueueDelivery) -> None:
        self.acknowledged.append(queued.message_id)

    def schedule_retry(
        self,
        queued: QueueDelivery,
        message: IngestionTask,
        *,
        delay: timedelta,
    ) -> None:
        self.retries.append((queued, message, delay))

    def dead_letter(
        self,
        queued: QueueDelivery,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        self.dead_letters.append((queued, error_code, error_message))


class RecordingSession:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("database commit failed")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


class StubIngestionService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, str, int]] = []

    def run(self, source, *, idempotency_key: str, max_attempts: int):
        self.calls.append((source, idempotency_key, max_attempts))
        if self.error is not None:
            raise self.error
        return object()


def worker(
    queue: MemoryQueue,
    session: RecordingSession,
    service: StubIngestionService,
) -> IngestionWorker:
    return IngestionWorker(
        queue=queue,
        registry=approved_registry(),
        session_factory=lambda: session,
        service_factory=lambda _: service,
        block_ms=1,
        stale_after_ms=100,
        retry_base_seconds=10,
        retry_max_seconds=60,
    )


def test_worker_commits_before_acknowledging_success() -> None:
    queue = MemoryQueue([delivery()])
    session = RecordingSession()
    service = StubIngestionService()

    handled = worker(queue, session, service).run_once()

    assert handled is True
    assert session.commits == 1
    assert queue.acknowledged == ["1-0"]
    assert queue.retries == []
    assert queue.dead_letters == []


def test_retryable_failure_is_committed_and_scheduled_with_backoff() -> None:
    queue = MemoryQueue([delivery(task(attempt=1, max_attempts=3))])
    session = RecordingSession()
    service = StubIngestionService(
        IngestionError("fetch_unavailable", "source unavailable", retryable=True)
    )

    worker(queue, session, service).run_once()

    assert session.commits == 1
    assert len(queue.retries) == 1
    _, retry_task, delay = queue.retries[0]
    assert retry_task.attempt == 2
    assert delay == timedelta(seconds=10)
    assert queue.dead_letters == []


def test_database_exhausted_or_permanent_failure_is_dead_lettered() -> None:
    final_queue = MemoryQueue([delivery(task(attempt=3, max_attempts=3))])
    final_service = StubIngestionService(
        IngestionError("fetch_unavailable", "source unavailable", retryable=False)
    )
    worker(final_queue, RecordingSession(), final_service).run_once()

    permanent_queue = MemoryQueue([delivery()])
    permanent_service = StubIngestionService(
        IngestionError("source_not_eligible", "source is not eligible", retryable=False)
    )
    worker(permanent_queue, RecordingSession(), permanent_service).run_once()

    assert final_queue.dead_letters[0][1] == "fetch_unavailable"
    assert permanent_queue.dead_letters[0][1] == "source_not_eligible"


def test_database_retry_decision_wins_when_queue_attempt_is_at_maximum() -> None:
    queued_task = task(attempt=3, max_attempts=3)
    queue = MemoryQueue([delivery(queued_task)])
    service = StubIngestionService(
        IngestionError("fetch_unavailable", "source unavailable", retryable=True)
    )

    worker(queue, RecordingSession(), service).run_once()

    assert queue.retries[0][1].attempt == 3
    assert queue.dead_letters == []


def test_concurrent_in_progress_delivery_retries_without_consuming_attempt() -> None:
    queued_task = task(attempt=3, max_attempts=3)
    queue = MemoryQueue([delivery(queued_task)])
    service = StubIngestionService(
        IngestionError("job_in_progress", "job is already running", retryable=True)
    )

    worker(queue, RecordingSession(), service).run_once()

    assert queue.retries[0][1].attempt == 3
    assert queue.dead_letters == []


def test_commit_failure_leaves_delivery_unacknowledged_for_recovery() -> None:
    queue = MemoryQueue([delivery()])
    session = RecordingSession(fail_commit=True)

    handled = worker(queue, session, StubIngestionService()).run_once()

    assert handled is False
    assert session.rollbacks == 1
    assert session.closes == 1
    assert queue.acknowledged == []
    assert queue.retries == []
    assert queue.dead_letters == []


def test_invalid_or_unknown_messages_are_dead_lettered_without_database_work() -> None:
    invalid = QueueDelivery(
        message_id="invalid-0",
        raw_payload="{}",
        task=None,
        validation_error="missing fields",
    )
    unknown_task = task().model_copy(update={"source_id": uuid4()})
    queue = MemoryQueue([invalid, delivery(unknown_task)])

    def no_session():
        raise AssertionError("database should not open")

    ingestion_worker = IngestionWorker(
        queue=queue,
        registry=approved_registry(),
        session_factory=no_session,
        service_factory=lambda _: StubIngestionService(),
        block_ms=1,
    )

    assert ingestion_worker.run_once() is True
    assert ingestion_worker.run_once() is True
    assert [item[1] for item in queue.dead_letters] == [
        "invalid_queue_message",
        "source_not_registered",
    ]


def test_task_schema_rejects_invalid_attempts_and_naive_time() -> None:
    with pytest.raises(ValidationError, match="attempt cannot exceed"):
        task(attempt=4, max_attempts=3)

    with pytest.raises(ValidationError, match="timezone-aware"):
        IngestionTask(
            source_id=uuid4(),
            idempotency_key="scheduled:naive",
            enqueued_at=datetime(2026, 8, 1),
        )


def test_manual_enqueue_fails_closed_for_unapproved_registry() -> None:
    queue = MemoryQueue()
    development_registry = load_source_registry(REGISTRY_PATH)

    with pytest.raises(ValueError, match="not approved"):
        enqueue_source(
            queue=queue,
            registry=development_registry,
            source_id=development_registry.sources[0].id,
            idempotency_key="manual:test",
            max_attempts=3,
        )

    message_id = enqueue_source(
        queue=queue,
        registry=approved_registry(),
        source_id=approved_registry().sources[0].id,
        idempotency_key="manual:test",
        max_attempts=3,
    )
    assert message_id == "2-0"
    assert queue.published[0].attempt == 1


class StreamClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def xreadgroup(self, *args, **kwargs):
        del args, kwargs
        return [(b"stream", [(b"9-0", {b"payload": self.payload.encode()})])]


class RecordingPipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def zadd(self, *args):
        self.calls.append(("zadd", args))
        return self

    def xack(self, *args):
        self.calls.append(("xack", args))
        return self

    def execute(self):
        self.calls.append(("execute", ()))
        return [1, 1]


class RetryClient:
    def __init__(self) -> None:
        self.transaction: bool | None = None
        self.recording_pipeline = RecordingPipeline()

    def pipeline(self, *, transaction: bool):
        self.transaction = transaction
        return self.recording_pipeline


class ScheduledPublishClient:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def eval(self, *args):
        self.calls.append(args)
        return self.result


def test_redis_stream_delivery_decodes_bytes_and_validates_payload() -> None:
    queued_task = task()
    queue = RedisStreamIngestionQueue(
        client=StreamClient(queued_task.canonical_json()),
        stream="stream",
        group="group",
        consumer="consumer",
        retry_set="retries",
        dead_letter_stream="dead",
    )

    reserved = queue.reserve(block_ms=1)

    assert reserved is not None
    assert reserved.message_id == "9-0"
    assert reserved.task == queued_task


def test_redis_retry_schedule_and_ack_share_one_transaction() -> None:
    client = RetryClient()
    queue = RedisStreamIngestionQueue(
        client=client,
        stream="stream",
        group="group",
        consumer="consumer",
        retry_set="retries",
        dead_letter_stream="dead",
    )
    queued = delivery()

    queue.schedule_retry(
        queued,
        task(attempt=2),
        delay=timedelta(seconds=30),
    )

    assert client.transaction is True
    assert [call[0] for call in client.recording_pipeline.calls] == [
        "zadd",
        "xack",
        "execute",
    ]


def test_redis_scheduled_publish_atomically_deduplicates_a_slot() -> None:
    client = ScheduledPublishClient(b"12-0")
    queue = RedisStreamIngestionQueue(
        client=client,
        stream="stream",
        group="group",
        consumer="consumer",
        retry_set="retries",
        dead_letter_stream="dead",
    )

    message_id = queue.publish_scheduled(task(), deduplication_ttl=timedelta(days=1))

    assert message_id == "12-0"
    expected_key = f"stream:scheduled:{task().source_id}:scheduled:2026-08-01"
    assert client.calls[0][1:4] == (2, expected_key, "stream")
    assert client.calls[0][-1] == 86400

    duplicate_queue = RedisStreamIngestionQueue(
        client=ScheduledPublishClient(None),
        stream="stream",
        group="group",
        consumer="consumer",
        retry_set="retries",
        dead_letter_stream="dead",
    )
    assert duplicate_queue.publish_scheduled(
        task(), deduplication_ttl=timedelta(days=1)
    ) is None
