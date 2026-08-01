from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ingestion.models import (
    CrawlPolicy,
    RegistryStatus,
    SourceRegistryEntry,
    SourceSchedule,
)
from app.ingestion.registry import load_source_registry
from app.ingestion.scheduler import IngestionScheduler

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "data/sources/registry.development.json"


class ScheduledQueue:
    def __init__(self) -> None:
        self.slots: set[tuple[object, str]] = set()
        self.published: list[tuple[object, timedelta]] = []

    def publish_scheduled(self, task, *, deduplication_ttl: timedelta) -> str | None:
        key = (task.source_id, task.idempotency_key)
        if key in self.slots:
            return None
        self.slots.add(key)
        self.published.append((task, deduplication_ttl))
        return "1-0"


def scheduled_registry():
    registry = load_source_registry(REGISTRY_PATH)
    scheduled = registry.sources[0].model_copy(
        update={
            "organization": registry.sources[0].organization.model_copy(
                update={"is_official": True}
            ),
            "crawl_policy": CrawlPolicy.ALLOWED,
            "status": RegistryStatus.APPROVED,
            "owner": "content-team",
            "reviewed_at": datetime(2026, 8, 1, tzinfo=UTC),
            "production_eligible": True,
            "schedule": SourceSchedule(interval_minutes=60, max_attempts=4),
        }
    )
    return registry.model_copy(update={"sources": [scheduled]})


def test_scheduler_uses_deterministic_slots_and_deduplicates_repeated_polls() -> None:
    queue = ScheduledQueue()
    scheduler = IngestionScheduler(queue=queue, registry=scheduled_registry())
    now = datetime(2026, 8, 1, 12, 37, tzinfo=UTC)

    first = scheduler.run_once(now=now)
    repeated = scheduler.run_once(now=now + timedelta(minutes=1))

    task, ttl = queue.published[0]
    assert task.idempotency_key == "scheduled:20260801T120000Z"
    assert task.max_attempts == 4
    assert ttl == timedelta(days=1)
    assert first.enqueued_sources == 1
    assert repeated.duplicate_slots == 1


def test_scheduler_ignores_sources_without_an_opt_in_schedule() -> None:
    queue = ScheduledQueue()
    registry = load_source_registry(REGISTRY_PATH)

    result = IngestionScheduler(queue=queue, registry=registry).run_once(
        now=datetime(2026, 8, 1, tzinfo=UTC)
    )

    assert result.eligible_sources == 0
    assert queue.published == []


def test_scheduler_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        IngestionScheduler(queue=ScheduledQueue(), registry=scheduled_registry()).run_once(
            now=datetime(2026, 8, 1)
        )


def test_registry_rejects_schedule_without_production_approval() -> None:
    source = load_source_registry(REGISTRY_PATH).sources[0]
    payload = source.model_dump(mode="json")
    payload["schedule"] = {"interval_minutes": 60, "max_attempts": 3}

    with pytest.raises(ValidationError, match="scheduled sources must be approved"):
        SourceRegistryEntry.model_validate(payload)


def test_registry_rejects_production_eligibility_for_unofficial_organization() -> None:
    source = load_source_registry(REGISTRY_PATH).sources[0]
    payload = source.model_dump(mode="json")
    payload.update(
        {
            "crawl_policy": "allowed",
            "status": "approved",
            "owner": "content-team",
            "reviewed_at": "2026-08-01T00:00:00Z",
            "production_eligible": True,
        }
    )

    with pytest.raises(ValidationError, match="must be official"):
        SourceRegistryEntry.model_validate(payload)
