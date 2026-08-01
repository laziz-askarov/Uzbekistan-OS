import argparse
import logging
import os
import signal
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from time import sleep
from uuid import UUID

from redis import Redis
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_session_factory
from app.ingestion.fetchers import HttpSourceFetcher
from app.ingestion.models import SourceRegistry
from app.ingestion.queue import IngestionQueue, IngestionTask, RedisStreamIngestionQueue
from app.ingestion.registry import load_source_registry
from app.ingestion.registry_repositories import SqlAlchemySourceRegistryRepository
from app.ingestion.registry_sync import RegistrySyncResult, RegistrySyncService
from app.ingestion.repositories import SqlAlchemyIngestionRepository
from app.ingestion.scheduler import IngestionScheduler
from app.ingestion.service import IngestionService
from app.ingestion.stores import S3SnapshotStore
from app.ingestion.worker import IngestionWorker
from app.observability import configure_logging


def build_queue(settings: Settings) -> RedisStreamIngestionQueue:
    block_seconds = settings.worker_block_ms / 1000
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=block_seconds + 1,
    )
    consumer = settings.worker_consumer_name or f"{socket.gethostname()}-{os.getpid()}"
    queue = RedisStreamIngestionQueue(
        client=redis_client,
        stream=settings.worker_stream,
        group=settings.worker_group,
        consumer=consumer,
        retry_set=settings.worker_retry_set,
        dead_letter_stream=settings.worker_dead_letter_stream,
    )
    queue.ensure_group()
    return queue


def load_runtime_registry(settings: Settings) -> SourceRegistry:
    registry = load_source_registry(Path(settings.worker_registry_path))
    if registry.environment != settings.app_env:
        raise ValueError(
            f"registry environment {registry.environment!r} does not match "
            f"APP_ENV {settings.app_env!r}"
        )
    return registry


def synchronize_registry(
    settings: Settings,
    registry: SourceRegistry,
) -> RegistrySyncResult:
    session = get_session_factory()()
    try:
        result = RegistrySyncService(
            repository=SqlAlchemySourceRegistryRepository(session),
            environment=settings.app_env,
        ).synchronize(registry)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_worker(
    *,
    settings: Settings | None = None,
    registry: SourceRegistry | None = None,
) -> IngestionWorker:
    settings = settings or get_settings()
    registry = registry or load_runtime_registry(settings)
    queue = build_queue(settings)
    snapshot_store = S3SnapshotStore.from_settings(settings)
    fetcher = HttpSourceFetcher()

    def service_factory(session: Session) -> IngestionService:
        return IngestionService(
            fetcher=fetcher,
            snapshot_store=snapshot_store,
            repository=SqlAlchemyIngestionRepository(session),
            max_pdf_pages=settings.ingestion_max_pdf_pages,
            max_normalized_characters=settings.ingestion_max_normalized_characters,
        )

    return IngestionWorker(
        queue=queue,
        registry=registry,
        session_factory=get_session_factory(),
        service_factory=service_factory,
        block_ms=settings.worker_block_ms,
        stale_after_ms=settings.worker_stale_after_ms,
        retry_base_seconds=settings.worker_retry_base_seconds,
        retry_max_seconds=settings.worker_retry_max_seconds,
    )


def enqueue_source(
    *,
    queue: IngestionQueue,
    registry: SourceRegistry,
    source_id: UUID,
    idempotency_key: str,
    max_attempts: int,
) -> str:
    return queue.publish(
        build_ingestion_task(
            registry=registry,
            source_id=source_id,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
        )
    )


def build_ingestion_task(
    *,
    registry: SourceRegistry,
    source_id: UUID,
    idempotency_key: str,
    max_attempts: int,
) -> IngestionTask:
    source = next((item for item in registry.sources if item.id == source_id), None)
    if source is None:
        raise ValueError("source is not present in the configured registry")
    if not source.automatic_fetch_eligible:
        raise ValueError("source is not approved for automatic production ingestion")
    return IngestionTask(
        source_id=source_id,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
        enqueued_at=datetime.now(UTC),
    )


def run_worker() -> None:
    settings = get_settings()
    registry = load_runtime_registry(settings)
    synchronize_registry(settings, registry)
    stop_event = Event()

    def stop_worker(signum: int, frame: object) -> None:
        del signum, frame
        stop_event.set()

    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    build_worker(settings=settings, registry=registry).run_forever(stop_event)


def run_scheduler() -> None:
    settings = get_settings()
    registry = load_runtime_registry(settings)
    synchronize_registry(settings, registry)
    stop_event = Event()

    def stop_scheduler(signum: int, frame: object) -> None:
        del signum, frame
        stop_event.set()

    signal.signal(signal.SIGTERM, stop_scheduler)
    signal.signal(signal.SIGINT, stop_scheduler)
    IngestionScheduler(
        queue=build_queue(settings),
        registry=registry,
        poll_seconds=settings.worker_scheduler_poll_seconds,
    ).run_forever(stop_event)


def ensure_object_store(
    *,
    settings: Settings | None = None,
    attempts: int = 20,
    delay_seconds: float = 3,
    sleeper: Callable[[float], None] = sleep,
) -> None:
    if attempts < 1:
        raise ValueError("object-store readiness attempts must be positive")
    settings = settings or get_settings()
    logger = logging.getLogger(__name__)
    for attempt in range(1, attempts + 1):
        try:
            S3SnapshotStore.from_settings(settings).ensure_bucket(region=settings.s3_region)
        except Exception:
            if attempt == attempts:
                raise
            logger.warning(
                "object store is not ready",
                extra={"attempt": attempt, "max_attempts": attempts},
            )
            sleeper(delay_seconds)
        else:
            logger.info("object store bucket is ready")
            return


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser(description="Uzbekistan OS ingestion worker")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("run", help="run the ingestion consumer loop")
    subcommands.add_parser("schedule", help="run the approved-source scheduler")
    subcommands.add_parser("sync-registry", help="synchronize the registry to PostgreSQL")
    subcommands.add_parser("ensure-object-store", help="provision the evidence bucket")
    enqueue = subcommands.add_parser("enqueue", help="enqueue one approved source")
    enqueue.add_argument("--source-id", required=True, type=UUID)
    enqueue.add_argument("--idempotency-key", required=True)
    enqueue.add_argument("--max-attempts", type=int, default=3)
    arguments = parser.parse_args()

    if arguments.command in {None, "run"}:
        run_worker()
        return
    if arguments.command == "schedule":
        run_scheduler()
        return
    if arguments.command == "ensure-object-store":
        ensure_object_store()
        return

    settings = get_settings()
    registry = load_runtime_registry(settings)
    sync_result = synchronize_registry(settings, registry)
    if arguments.command == "sync-registry":
        logging.getLogger(__name__).info(
            "registry synchronization complete: %s",
            sync_result,
        )
        return
    task = build_ingestion_task(
        registry=registry,
        source_id=arguments.source_id,
        idempotency_key=arguments.idempotency_key,
        max_attempts=arguments.max_attempts,
    )
    message_id = build_queue(settings).publish(task)
    logging.getLogger(__name__).info("queued ingestion message %s", message_id)


if __name__ == "__main__":
    main()
