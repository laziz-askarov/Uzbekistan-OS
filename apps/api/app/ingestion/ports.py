from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from app.ingestion.models import SourceRegistryEntry
from app.ingestion.types import (
    FetchResponse,
    IngestionOutcome,
    JobClaim,
    SnapshotMetadata,
)


class SourceFetcher(Protocol):
    def fetch(
        self,
        source: SourceRegistryEntry,
        conditional_headers: Mapping[str, str],
    ) -> FetchResponse: ...


class SnapshotStore(Protocol):
    def put(self, storage_key: str, content: bytes) -> None: ...


class IngestionRepository(Protocol):
    def claim_job(self, source_id: UUID, idempotency_key: str, max_attempts: int) -> JobClaim: ...

    def latest_snapshot(self, source_id: UUID) -> SnapshotMetadata | None: ...

    def record_snapshot(self, snapshot: SnapshotMetadata) -> None: ...

    def mark_succeeded(self, job_id: UUID, outcome: IngestionOutcome) -> None: ...

    def mark_failed(self, job_id: UUID, error: Exception, *, retryable: bool) -> None: ...
