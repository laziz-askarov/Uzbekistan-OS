from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from json import loads
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.ingestion.errors import IngestionError, SourceNotEligibleError
from app.ingestion.models import SourceRegistryEntry
from app.ingestion.normalizers import normalize_response
from app.ingestion.registry import load_source_registry
from app.ingestion.service import IngestionService
from app.ingestion.stores import LocalSnapshotStore
from app.ingestion.types import (
    ChangeStatus,
    ExtractionArtifactMetadata,
    FetchResponse,
    IngestionOutcome,
    JobClaim,
    JobStatus,
    ReviewItemMetadata,
    SnapshotMetadata,
)

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "data/sources/registry.development.json"


def approved_source() -> SourceRegistryEntry:
    return SourceRegistryEntry.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000002001",
            "slug": "approved-test-source",
            "organization": {
                "id": "00000000-0000-0000-0000-000000002000",
                "slug": "test-organization",
                "name": "Test Organization",
                "website_url": "https://government.example",
                "country_iso2": "UZ",
                "is_official": True,
            },
            "title": "Approved test source",
            "url": "https://government.example/source",
            "source_type": "html",
            "domains": ["tourism"],
            "languages": ["en"],
            "crawl_policy": "allowed",
            "adapter_key": "generic-html",
            "trust_tier": 1,
            "status": "approved",
            "owner": "content-team",
            "reviewed_at": "2026-07-31T12:00:00Z",
            "production_eligible": True,
        }
    )


class FakeFetcher:
    def __init__(self, responses: list[FetchResponse]) -> None:
        self.responses = responses
        self.calls: list[Mapping[str, str]] = []

    def fetch(
        self,
        source: SourceRegistryEntry,
        conditional_headers: Mapping[str, str],
    ) -> FetchResponse:
        del source
        self.calls.append(dict(conditional_headers))
        return self.responses.pop(0)


class MemorySnapshotStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(
        self,
        storage_key: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        del content_type
        self.objects.setdefault(storage_key, content)

    def get(self, storage_key: str) -> bytes:
        return self.objects[storage_key]


@dataclass
class FakeJob:
    id: UUID
    source_id: UUID
    key: str
    attempt_count: int
    max_attempts: int
    status: JobStatus
    outcome: IngestionOutcome | None = None


class MemoryRepository:
    def __init__(self) -> None:
        self.jobs: dict[tuple[UUID, str], FakeJob] = {}
        self.jobs_by_id: dict[UUID, FakeJob] = {}
        self.snapshots: list[SnapshotMetadata] = []
        self.artifacts: list[ExtractionArtifactMetadata] = []
        self.review_items: list[ReviewItemMetadata] = []

    def claim_job(self, source_id: UUID, idempotency_key: str, max_attempts: int) -> JobClaim:
        key = (source_id, idempotency_key)
        job = self.jobs.get(key)
        if job is not None and job.status is JobStatus.SUCCEEDED:
            return JobClaim(job.id, job.attempt_count, job.max_attempts, job.outcome)
        if job is None:
            job = FakeJob(
                id=uuid4(),
                source_id=source_id,
                key=idempotency_key,
                attempt_count=1,
                max_attempts=max_attempts,
                status=JobStatus.RUNNING,
            )
            self.jobs[key] = job
            self.jobs_by_id[job.id] = job
        else:
            job.attempt_count += 1
            job.status = JobStatus.RUNNING
        return JobClaim(job.id, job.attempt_count, job.max_attempts)

    def latest_snapshot(self, source_id: UUID) -> SnapshotMetadata | None:
        return next(
            (snapshot for snapshot in reversed(self.snapshots) if snapshot.source_id == source_id),
            None,
        )

    def record_snapshot(self, snapshot: SnapshotMetadata) -> None:
        self.snapshots.append(snapshot)

    def record_extraction_artifact(self, artifact: ExtractionArtifactMetadata) -> None:
        self.artifacts.append(artifact)

    def enqueue_review(self, review_item: ReviewItemMetadata) -> None:
        self.review_items.append(review_item)

    def mark_succeeded(self, job_id: UUID, outcome: IngestionOutcome) -> None:
        job = self.jobs_by_id[job_id]
        job.status = JobStatus.SUCCEEDED
        job.outcome = outcome

    def mark_failed(
        self,
        job_id: UUID,
        error: Exception,
        *,
        retryable: bool,
    ) -> JobStatus:
        del error
        job = self.jobs_by_id[job_id]
        job.status = (
            JobStatus.RETRY_SCHEDULED
            if retryable and job.attempt_count < job.max_attempts
            else JobStatus.DEAD_LETTERED
        )
        return job.status


def response(source: SourceRegistryEntry, body: bytes, status: int = 200) -> FetchResponse:
    return FetchResponse(
        url=str(source.url),
        status_code=status,
        body=body,
        fetched_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        headers={"Content-Type": "text/html; charset=utf-8", "ETag": '"fixture-v1"'},
    )


def service(
    fetcher: FakeFetcher,
    repository: MemoryRepository,
    store: MemorySnapshotStore | None = None,
) -> IngestionService:
    return IngestionService(
        fetcher=fetcher,
        snapshot_store=store or MemorySnapshotStore(),
        repository=repository,
    )


def test_development_registry_is_valid_but_not_automatically_eligible() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert registry.environment == "development"
    assert len(registry.sources) == 1
    assert registry.sources[0].automatic_fetch_eligible is False


def test_allowed_source_requires_approval_metadata() -> None:
    data = approved_source().model_dump(mode="json")
    data.update({"status": "draft", "owner": None, "reviewed_at": None})

    with pytest.raises(ValidationError, match="automatically crawlable sources must be approved"):
        SourceRegistryEntry.model_validate(data)


def test_unapproved_source_is_rejected_before_fetching() -> None:
    source = load_source_registry(REGISTRY_PATH).sources[0]
    fetcher = FakeFetcher([])

    with pytest.raises(SourceNotEligibleError):
        service(fetcher, MemoryRepository()).run(source, idempotency_key="fixture")

    assert fetcher.calls == []


def test_html_normalization_uses_visible_text_only() -> None:
    source = approved_source()
    fetched = response(
        source,
        (
            b"<html><style>hidden</style><h1>Entry &amp; exit</h1>"
            b"<script>bad()</script><p> Rules </p></html>"
        ),
    )

    normalized = normalize_response(fetched)

    assert normalized.text == "Entry & exit\nRules"
    assert "hidden" not in normalized.text
    assert "bad" not in normalized.text


def test_changed_snapshot_is_stored_and_same_job_is_replayed() -> None:
    source = approved_source()
    fetcher = FakeFetcher([response(source, b"<p>Current rule</p>")])
    repository = MemoryRepository()
    store = MemorySnapshotStore()
    ingestion = service(fetcher, repository, store)

    first = ingestion.run(source, idempotency_key="scheduled:2026-07-31")
    replay = ingestion.run(source, idempotency_key="scheduled:2026-07-31")

    assert first.status is ChangeStatus.CHANGED
    assert replay == first
    assert len(fetcher.calls) == 1
    assert len(repository.snapshots) == 1
    assert len(repository.artifacts) == 1
    assert len(repository.review_items) == 1
    assert store.objects[first.storage_key] == b"<p>Current rule</p>"
    artifact = repository.artifacts[0]
    assert store.objects[artifact.storage_key].startswith(b'{"adapter_key":"generic-html"')
    assert repository.review_items[0].extraction_artifact_id == artifact.id


def test_extraction_artifact_preserves_heading_sections() -> None:
    source = approved_source()
    body = (
        b"<h1>Overview</h1><p>Entry guidance.</p>"
        b"<h2>Requirements</h2><p>Passport required.</p>"
    )
    repository = MemoryRepository()
    store = MemorySnapshotStore()

    outcome = service(FakeFetcher([response(source, body)]), repository, store).run(
        source,
        idempotency_key="scheduled:sections",
    )

    artifact = repository.artifacts[0]
    payload = loads(store.objects[artifact.storage_key])
    assert payload["snapshot_id"] == str(outcome.snapshot_id)
    assert payload["sections"] == [
        {"body": "Entry guidance.", "heading": "Overview", "id": "overview"},
        {
            "body": "Passport required.",
            "heading": "Requirements",
            "id": "requirements",
        },
    ]


def test_identical_content_is_unchanged_and_uses_conditional_headers() -> None:
    source = approved_source()
    fetched = response(source, b"<p>Current rule</p>")
    fetcher = FakeFetcher([fetched, fetched])
    repository = MemoryRepository()
    ingestion = service(fetcher, repository)

    first = ingestion.run(source, idempotency_key="scheduled:first")
    second = ingestion.run(source, idempotency_key="scheduled:second")

    assert first.status is ChangeStatus.CHANGED
    assert second.status is ChangeStatus.UNCHANGED
    assert len(repository.snapshots) == 1
    assert fetcher.calls[1] == {"If-None-Match": '"fixture-v1"'}


def test_not_modified_response_reuses_prior_snapshot() -> None:
    source = approved_source()
    fetcher = FakeFetcher(
        [response(source, b"<p>Current rule</p>"), response(source, b"", 304)]
    )
    repository = MemoryRepository()
    ingestion = service(fetcher, repository)

    first = ingestion.run(source, idempotency_key="scheduled:first")
    second = ingestion.run(source, idempotency_key="scheduled:second")

    assert second.status is ChangeStatus.UNCHANGED
    assert second.snapshot_id == first.snapshot_id
    assert len(repository.snapshots) == 1


def test_response_from_different_url_is_rejected() -> None:
    source = approved_source()
    redirected = FetchResponse(
        url="https://unapproved.example/source",
        status_code=200,
        body=b"<p>Unexpected</p>",
        fetched_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        headers={"Content-Type": "text/html"},
    )
    repository = MemoryRepository()

    with pytest.raises(IngestionError, match="approved registry URL"):
        service(FakeFetcher([redirected]), repository).run(
            source,
            idempotency_key="scheduled:redirect",
        )

    assert next(iter(repository.jobs.values())).status is JobStatus.DEAD_LETTERED


def test_retryable_failure_is_dead_lettered_after_max_attempts() -> None:
    source = approved_source()
    fetcher = FakeFetcher([response(source, b"", 503), response(source, b"", 503)])
    repository = MemoryRepository()
    ingestion = service(fetcher, repository)

    with pytest.raises(IngestionError, match="HTTP 503"):
        ingestion.run(source, idempotency_key="scheduled:failure", max_attempts=2)
    job = next(iter(repository.jobs.values()))
    assert job.status is JobStatus.RETRY_SCHEDULED

    with pytest.raises(IngestionError, match="HTTP 503"):
        ingestion.run(source, idempotency_key="scheduled:failure", max_attempts=2)
    assert job.status is JobStatus.DEAD_LETTERED
    assert job.attempt_count == 2


def test_local_snapshot_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = LocalSnapshotStore(tmp_path)

    with pytest.raises(IngestionError, match="inside the configured root"):
        store.put("../outside.bin", b"unsafe")
