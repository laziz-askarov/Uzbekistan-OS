import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Event

from app.ingestion.models import SourceRegistry
from app.ingestion.queue import IngestionQueue, IngestionTask

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScheduleRunResult:
    eligible_sources: int
    enqueued_sources: int
    duplicate_slots: int


class IngestionScheduler:
    def __init__(
        self,
        *,
        queue: IngestionQueue,
        registry: SourceRegistry,
        poll_seconds: int = 60,
    ) -> None:
        if poll_seconds < 1:
            raise ValueError("scheduler poll interval must be positive")
        self.queue = queue
        self.registry = registry
        self.poll_seconds = poll_seconds

    def run_once(self, *, now: datetime | None = None) -> ScheduleRunResult:
        scheduled_at = now or datetime.now(UTC)
        if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
            raise ValueError("scheduler time must be timezone-aware")
        scheduled_at = scheduled_at.astimezone(UTC)

        eligible_sources = 0
        enqueued_sources = 0
        duplicate_slots = 0
        for source in self.registry.sources:
            if source.schedule is None or not source.automatic_fetch_eligible:
                continue
            eligible_sources += 1
            interval = timedelta(minutes=source.schedule.interval_minutes)
            slot = self._slot_start(scheduled_at, interval)
            task = IngestionTask(
                source_id=source.id,
                idempotency_key=f"scheduled:{slot:%Y%m%dT%H%M%SZ}",
                max_attempts=source.schedule.max_attempts,
                enqueued_at=scheduled_at,
            )
            message_id = self.queue.publish_scheduled(
                task,
                deduplication_ttl=max(interval * 2, timedelta(days=1)),
            )
            if message_id is None:
                duplicate_slots += 1
            else:
                enqueued_sources += 1

        return ScheduleRunResult(
            eligible_sources=eligible_sources,
            enqueued_sources=enqueued_sources,
            duplicate_slots=duplicate_slots,
        )

    def run_forever(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            try:
                result = self.run_once()
                if result.enqueued_sources:
                    logger.info(
                        "scheduled ingestion sources",
                        extra={
                            "eligible_sources": result.eligible_sources,
                            "enqueued_sources": result.enqueued_sources,
                            "duplicate_slots": result.duplicate_slots,
                        },
                    )
            except Exception:
                logger.exception("ingestion scheduler loop failed")
            stop_event.wait(self.poll_seconds)

    @staticmethod
    def _slot_start(now: datetime, interval: timedelta) -> datetime:
        interval_seconds = int(interval.total_seconds())
        slot_timestamp = int(now.timestamp()) // interval_seconds * interval_seconds
        return datetime.fromtimestamp(slot_timestamp, tz=UTC)
