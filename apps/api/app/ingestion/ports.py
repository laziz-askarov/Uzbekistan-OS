from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from app.ingestion.models import SourceRegistryEntry
from app.ingestion.types import (
    ExtractionArtifactMetadata,
    FetchResponse,
    IngestionOutcome,
    JobClaim,
    JobStatus,
    ReviewItemMetadata,
    SnapshotMetadata,
)


class SourceFetcher(Protocol):
    def fetch(
        self,
        source: SourceRegistryEntry,
        conditional_headers: Mapping[str, str],
    ) -> FetchResponse: ...


class SnapshotStore(Protocol):
    def put(
        self,
        storage_key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None: ...

    def get(self, storage_key: str) -> bytes: ...


class IngestionRepository(Protocol):
    def claim_job(self, source_id: UUID, idempotency_key: str, max_attempts: int) -> JobClaim: ...

    def latest_snapshot(self, source_id: UUID) -> SnapshotMetadata | None: ...

    def snapshot_by_sha256(
        self,
        source_id: UUID,
        sha256: str,
    ) -> SnapshotMetadata | None: ...

    def record_snapshot(self, snapshot: SnapshotMetadata) -> None: ...

    def record_extraction_artifact(self, artifact: ExtractionArtifactMetadata) -> None: ...

    def enqueue_review(self, review_item: ReviewItemMetadata) -> None: ...

    def mark_succeeded(self, job_id: UUID, outcome: IngestionOutcome) -> None: ...

    def mark_failed(
        self,
        job_id: UUID,
        error: Exception,
        *,
        retryable: bool,
    ) -> JobStatus: ...
