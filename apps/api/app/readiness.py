import logging
from collections.abc import Callable

import boto3
from botocore.client import Config
from redis import Redis
from sqlalchemy import text

from app.config import Settings
from app.database.session import get_engine

DependencyCheck = Callable[[Settings], None]
logger = logging.getLogger(__name__)


def _check_database(settings: Settings) -> None:
    del settings
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def _check_redis(settings: Settings) -> None:
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        client.ping()
    finally:
        client.close()


def _check_object_store(settings: Settings) -> None:
    if settings.snapshot_store_backend == "database":
        with get_engine().connect() as connection:
            relation = connection.execute(
                text("SELECT to_regclass('ingestion.snapshot_objects')")
            ).scalar_one()
            if relation is None:
                raise RuntimeError("private snapshot object table is unavailable")
        return
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4",
            connect_timeout=settings.readiness_timeout_seconds,
            read_timeout=settings.readiness_timeout_seconds,
            retries={"max_attempts": 0},
            s3={"addressing_style": "path"},
        ),
    )
    client.head_bucket(Bucket=settings.s3_bucket)


DEPENDENCY_CHECKS: tuple[tuple[str, DependencyCheck], ...] = (
    ("postgresql", _check_database),
    ("redis", _check_redis),
    ("object_store", _check_object_store),
)


def check_dependencies(settings: Settings) -> dict[str, str]:
    results: dict[str, str] = {}
    for name, check in DEPENDENCY_CHECKS:
        try:
            check(settings)
        except Exception:
            results[name] = "unavailable"
            logger.exception(
                "readiness dependency unavailable",
                extra={"dependency": name},
            )
        else:
            results[name] = "ok"
    return results
