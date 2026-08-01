import argparse
import logging
import os
import signal
import socket
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import UUID

from redis import Redis
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_session_factory
from app.ingestion.fetchers import HttpSourceFetcher
from app.ingestion.models import SourceRegistry
from app.ingestion.queue import IngestionQueue, IngestionTask, RedisStreamIngestionQueue
from app.ingestion.registry import load_source_registry
from app.ingestion.repositories import SqlAlchemyIngestionRepository
from app.ingestion.service import IngestionService
from app.ingestion.stores import S3SnapshotStore
from app.ingestion.worker import IngestionWorker


def build_queue(settings: Settings) -> RedisStreamIngestionQueue:
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
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


def build_worker() -> IngestionWorker:
    settings = get_settings()
    registry = load_source_registry(Path(settings.worker_registry_path))
    queue = build_queue(settings)
    snapshot_store = S3SnapshotStore.from_settings(settings)
    fetcher = HttpSourceFetcher()

    def service_factory(session: Session) -> IngestionService:
        return IngestionService(
            fetcher=fetcher,
            snapshot_store=snapshot_store,
            repository=SqlAlchemyIngestionRepository(session),
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
    stop_event = Event()

    def stop_worker(signum: int, frame: object) -> None:
        del signum, frame
        stop_event.set()

    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    build_worker().run_forever(stop_event)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Uzbekistan OS ingestion worker")
    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("run", help="run the ingestion consumer loop")
    enqueue = subcommands.add_parser("enqueue", help="enqueue one approved source")
    enqueue.add_argument("--source-id", required=True, type=UUID)
    enqueue.add_argument("--idempotency-key", required=True)
    enqueue.add_argument("--max-attempts", type=int, default=3)
    arguments = parser.parse_args()

    if arguments.command in {None, "run"}:
        run_worker()
        return

    settings = get_settings()
    registry = load_source_registry(Path(settings.worker_registry_path))
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
