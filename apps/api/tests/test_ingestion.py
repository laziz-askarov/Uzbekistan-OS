from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from json import loads
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.ingestion.errors import IngestionError, SourceNotEligibleError
from app.ingestion.models import SourceRegistryEntry, SourceType
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
STAGING_REGISTRY_PATH = ROOT / "data/sources/registry.staging.json"
PROPOSED_REGISTRY_PATH = ROOT / "data/sources/registry.production.proposed.json"


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


def approved_pdf_source() -> SourceRegistryEntry:
    source = approved_source()
    return source.model_copy(
        update={
            "slug": "approved-pdf-source",
            "url": "https://government.example/source.pdf",
            "source_type": SourceType.PDF,
            "adapter_key": "generic-pdf",
        }
    )


def approved_manual_source() -> SourceRegistryEntry:
    source = approved_source()
    return source.model_copy(
        update={
            "slug": "approved-manual-source",
            "crawl_policy": "manual_only",
            "source_type": SourceType.MANUAL,
            "adapter_key": "generic-manual",
        }
    )


def pdf_bytes(*pages: str, password: str | None = None) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    for page_text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        commands = ["BT", "/F1 12 Tf", "72 720 Td"]
        for line_number, line in enumerate(page_text.splitlines()):
            if line_number:
                commands.append("0 -18 Td")
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj")
        commands.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if password is not None:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


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

    def snapshot_by_sha256(
        self,
        source_id: UUID,
        sha256: str,
    ) -> SnapshotMetadata | None:
        return next(
            (
                snapshot
                for snapshot in self.snapshots
                if snapshot.source_id == source_id and snapshot.sha256 == sha256
            ),
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


def response(
    source: SourceRegistryEntry,
    body: bytes,
    status: int = 200,
    *,
    content_type: str = "text/html; charset=utf-8",
) -> FetchResponse:
    return FetchResponse(
        url=str(source.url),
        status_code=status,
        body=body,
        fetched_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        headers={"Content-Type": content_type, "ETag": '"fixture-v1"'},
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


def test_staging_registry_is_valid_empty_and_fail_closed() -> None:
    registry = load_source_registry(STAGING_REGISTRY_PATH)

    assert registry.environment == "staging"
    assert registry.sources == []


def test_proposed_production_registry_is_valid_and_fails_closed() -> None:
    registry = load_source_registry(PROPOSED_REGISTRY_PATH)

    assert registry.environment == "production"
    assert len(registry.sources) == 5
    assert all(source.automatic_fetch_eligible is False for source in registry.sources)


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


def test_manual_only_source_accepts_uploads_but_not_automatic_fetching() -> None:
    source = approved_manual_source()

    assert source.manual_ingestion_eligible is True
    assert source.automatic_fetch_eligible is False


def test_manual_upload_uses_ingestion_guards_and_replays_idempotently() -> None:
    source = approved_manual_source()
    repository = MemoryRepository()
    fetcher = FakeFetcher([])
    ingestion = service(fetcher, repository)
    uploaded = response(source, b"Official manual guidance", content_type="text/plain")

    first = ingestion.run_manual(source, uploaded, idempotency_key="upload:official-v1")
    replay = ingestion.run_manual(source, uploaded, idempotency_key="upload:official-v1")

    assert first.status is ChangeStatus.CHANGED
    assert replay == first
    assert fetcher.calls == []
    assert len(repository.snapshots) == 1
    assert len(repository.artifacts) == 1
    assert len(repository.review_items) == 1


def test_uploading_an_older_known_snapshot_does_not_duplicate_evidence() -> None:
    source = approved_manual_source()
    repository = MemoryRepository()
    ingestion = service(FakeFetcher([]), repository)
    first = response(source, b"Official version one", content_type="text/plain")
    second = response(source, b"Official version two", content_type="text/plain")

    first_outcome = ingestion.run_manual(source, first, idempotency_key="upload:v1")
    ingestion.run_manual(source, second, idempotency_key="upload:v2")
    reverted = ingestion.run_manual(source, first, idempotency_key="upload:v1-again")

    assert reverted.status is ChangeStatus.UNCHANGED
    assert reverted.snapshot_id == first_outcome.snapshot_id
    assert len(repository.snapshots) == 2
    assert len(repository.review_items) == 2


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
    body = b"<h1>Overview</h1><p>Entry guidance.</p><h2>Requirements</h2><p>Passport required.</p>"
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


def test_pdf_normalization_and_artifact_preserve_page_boundaries() -> None:
    source = approved_pdf_source()
    body = pdf_bytes(
        "Entry guidance\nApplicants must use the official form.",
        "Required documents\nPassport\nApplication receipt",
    )
    fetched = response(source, body, content_type="application/pdf")

    normalized = normalize_response(fetched)

    assert normalized.media_type == "application/pdf"
    assert normalized.sections == (
        ("Page 1", "Entry guidance\nApplicants must use the official form."),
        ("Page 2", "Required documents\nPassport\nApplication receipt"),
    )

    repository = MemoryRepository()
    store = MemorySnapshotStore()
    outcome = service(FakeFetcher([fetched]), repository, store).run(
        source,
        idempotency_key="scheduled:pdf",
    )
    artifact = repository.artifacts[0]
    payload = loads(store.objects[artifact.storage_key])
    assert outcome.status is ChangeStatus.CHANGED
    assert artifact.adapter_key == "generic-pdf"
    assert artifact.details == {"media_type": "application/pdf"}
    assert payload["sections"] == [
        {
            "body": "Entry guidance\nApplicants must use the official form.",
            "heading": "Page 1",
            "id": "page-1",
        },
        {
            "body": "Required documents\nPassport\nApplication receipt",
            "heading": "Page 2",
            "id": "page-2",
        },
    ]


def test_pdf_parser_rejects_encrypted_scanned_and_oversized_documents() -> None:
    source = approved_pdf_source()

    with pytest.raises(IngestionError, match="encrypted PDF") as encrypted:
        normalize_response(
            response(
                source,
                pdf_bytes("Protected", password="secret"),
                content_type="application/pdf",
            )
        )
    assert encrypted.value.code == "encrypted_pdf_unsupported"

    with pytest.raises(IngestionError, match="OCR is not enabled") as scanned:
        normalize_response(response(source, pdf_bytes(""), content_type="application/pdf"))
    assert scanned.value.code == "pdf_text_unavailable"

    with pytest.raises(IngestionError, match="1 page limit") as oversized:
        normalize_response(
            response(source, pdf_bytes("One", "Two"), content_type="application/pdf"),
            max_pdf_pages=1,
        )
    assert oversized.value.code == "pdf_page_limit_exceeded"


def test_registered_source_type_must_match_pdf_response() -> None:
    pdf_source = approved_pdf_source()
    repository = MemoryRepository()
    with pytest.raises(IngestionError, match="did not return application/pdf") as html_error:
        service(
            FakeFetcher([response(pdf_source, b"<p>HTML error page</p>")]),
            repository,
        ).run(pdf_source, idempotency_key="pdf-returned-html")
    assert html_error.value.code == "source_content_type_mismatch"

    html_source = approved_source()
    with pytest.raises(IngestionError, match="registered with type pdf") as pdf_error:
        service(
            FakeFetcher(
                [
                    response(
                        html_source,
                        pdf_bytes("Unexpected PDF"),
                        content_type="application/pdf",
                    )
                ]
            ),
            MemoryRepository(),
        ).run(html_source, idempotency_key="html-returned-pdf")
    assert pdf_error.value.code == "source_content_type_mismatch"


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
    fetcher = FakeFetcher([response(source, b"<p>Current rule</p>"), response(source, b"", 304)])
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
