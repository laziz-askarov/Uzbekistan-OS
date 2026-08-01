from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    SUCCEEDED = "succeeded"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"


class ChangeStatus(StrEnum):
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class FetchResponse:
    url: str
    status_code: int
    body: bytes
    fetched_at: datetime
    headers: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def header(self, name: str) -> str | None:
        target = name.casefold()
        return next(
            (value for key, value in self.headers.items() if key.casefold() == target),
            None,
        )


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    text: str
    sha256: str
    media_type: str
    sections: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    id: UUID
    source_id: UUID
    storage_key: str
    sha256: str
    normalized_sha256: str
    http_status: int
    content_type: str | None
    etag: str | None
    last_modified: str | None
    fetched_at: datetime
    byte_size: int


@dataclass(frozen=True, slots=True)
class IngestionOutcome:
    status: ChangeStatus
    source_id: UUID
    snapshot_id: UUID | None
    sha256: str | None
    normalized_sha256: str | None
    storage_key: str | None
    extraction_artifact_id: UUID | None = None
    review_item_id: UUID | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status.value,
            "source_id": str(self.source_id),
            "snapshot_id": str(self.snapshot_id) if self.snapshot_id else None,
            "sha256": self.sha256,
            "normalized_sha256": self.normalized_sha256,
            "storage_key": self.storage_key,
            "extraction_artifact_id": (
                str(self.extraction_artifact_id) if self.extraction_artifact_id else None
            ),
            "review_item_id": str(self.review_item_id) if self.review_item_id else None,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "IngestionOutcome":
        snapshot_id = value.get("snapshot_id")
        extraction_artifact_id = value.get("extraction_artifact_id")
        review_item_id = value.get("review_item_id")
        return cls(
            status=ChangeStatus(str(value["status"])),
            source_id=UUID(str(value["source_id"])),
            snapshot_id=UUID(str(snapshot_id)) if snapshot_id else None,
            sha256=str(value["sha256"]) if value.get("sha256") else None,
            normalized_sha256=(
                str(value["normalized_sha256"]) if value.get("normalized_sha256") else None
            ),
            storage_key=str(value["storage_key"]) if value.get("storage_key") else None,
            extraction_artifact_id=(
                UUID(str(extraction_artifact_id)) if extraction_artifact_id else None
            ),
            review_item_id=UUID(str(review_item_id)) if review_item_id else None,
        )


@dataclass(frozen=True, slots=True)
class JobClaim:
    id: UUID
    attempt_count: int
    max_attempts: int
    replay: IngestionOutcome | None = None


@dataclass(frozen=True, slots=True)
class ExtractionArtifactMetadata:
    id: UUID
    source_snapshot_id: UUID
    adapter_key: str
    schema_version: str
    storage_key: str
    sha256: str
    normalized_sha256: str
    section_count: int
    details: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ReviewItemMetadata:
    id: UUID
    extraction_artifact_id: UUID
    priority: int
