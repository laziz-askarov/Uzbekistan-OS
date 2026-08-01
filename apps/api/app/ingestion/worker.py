import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Event

from sqlalchemy.orm import Session

from app.ingestion.models import SourceRegistry
from app.ingestion.queue import IngestionQueue, QueueDelivery
from app.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(
        self,
        *,
        queue: IngestionQueue,
        registry: SourceRegistry,
        session_factory: Callable[[], Session],
        service_factory: Callable[[Session], IngestionService],
        block_ms: int = 5000,
        stale_after_ms: int = 120000,
        retry_base_seconds: int = 30,
        retry_max_seconds: int = 900,
    ) -> None:
        self.queue = queue
        self.sources = {source.id: source for source in registry.sources}
        self.session_factory = session_factory
        self.service_factory = service_factory
        self.block_ms = block_ms
        self.stale_after_ms = stale_after_ms
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds

    def run_once(self) -> bool:
        self.queue.promote_due(now=datetime.now(UTC))
        delivery = self.queue.reclaim_stale(min_idle_ms=self.stale_after_ms)
        if delivery is None:
            delivery = self.queue.reserve(block_ms=self.block_ms)
        if delivery is None:
            return False
        if delivery.task is None:
            self.queue.dead_letter(
                delivery,
                error_code="invalid_queue_message",
                error_message="ingestion queue message failed schema validation",
            )
            return True

        source = self.sources.get(delivery.task.source_id)
        if source is None:
            self.queue.dead_letter(
                delivery,
                error_code="source_not_registered",
                error_message="queue message source is not present in the loaded registry",
            )
            return True

        session = self.session_factory()
        try:
            service = self.service_factory(session)
            try:
                service.run(
                    source,
                    idempotency_key=delivery.task.idempotency_key,
                    max_attempts=delivery.task.max_attempts,
                )
            except Exception as error:
                session.commit()
                self._handle_failure(delivery, error)
            else:
                session.commit()
                self.queue.acknowledge(delivery)
        except Exception:
            session.rollback()
            logger.exception(
                "ingestion delivery remains pending after transaction or queue failure",
                extra={"message_id": delivery.message_id},
            )
            return False
        finally:
            session.close()
        return True

    def run_forever(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("ingestion worker loop failed")
                stop_event.wait(1)

    def _handle_failure(self, delivery: QueueDelivery, error: Exception) -> None:
        task = delivery.task
        if task is None:
            raise RuntimeError("validated task is required")
        error_code = str(getattr(error, "code", "ingestion_error"))
        retryable_value = getattr(error, "retryable", None)
        retryable = (
            bool(retryable_value)
            if retryable_value is not None
            else task.attempt < task.max_attempts
        )
        increment_attempt = error_code != "job_in_progress"
        if retryable:
            retry_task = task.retry(increment_attempt=increment_attempt)
            self.queue.schedule_retry(
                delivery,
                retry_task,
                delay=self._retry_delay(task.attempt),
            )
            return
        self.queue.dead_letter(
            delivery,
            error_code=error_code,
            error_message=str(error),
        )

    def _retry_delay(self, attempt: int) -> timedelta:
        seconds = min(
            self.retry_base_seconds * (2 ** max(attempt - 1, 0)),
            self.retry_max_seconds,
        )
        return timedelta(seconds=seconds)
