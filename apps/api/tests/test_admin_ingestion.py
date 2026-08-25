from base64 import b64encode
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.admin import (
    AdminIngestionError,
    AdminIngestionService,
    CreateAdminSourceRequest,
    IngestionJobRecord,
    ManualUploadRequest,
    PreparedCrawlJob,
    QueueCrawlRequest,
)
from app.ingestion.models import SourceRegistry, SourceRegistryEntry
from app.ingestion.types import ChangeStatus, IngestionOutcome

NOW = datetime(2026, 8, 1, 12, tzinfo=UTC)


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


def principal(*roles: str) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(id=uuid4(), roles=frozenset(roles), request_id="request-1")


class MemoryAdminRepository:
    def __init__(self) -> None:
        self.jobs: dict[tuple[UUID, str], IngestionJobRecord] = {}
        self.managed: list[SourceRegistryEntry] = []
        self.created: dict[str, tuple[str, SourceRegistryEntry]] = {}

    def source_states(self):
        return ()

    def managed_sources(self):
        return tuple(self.managed)

    def create_managed_source(
        self,
        request,
        principal,
        *,
        idempotency_key,
        created_at,
    ):
        del principal
        replay = self.created.get(idempotency_key)
        if replay is not None:
            request_hash, source = replay
            if request_hash != request.sha256:
                raise AdminIngestionError("source_idempotency_conflict", "different details")
            return source
        source = SourceRegistryEntry.model_validate(
            {
                "id": str(uuid4()),
                "slug": "new-official-source",
                "organization": {
                    "id": str(uuid4()),
                    "slug": "new-official-organization",
                    "name": request.organization_name,
                    "website_url": str(request.organization_website_url),
                    "country_iso2": "UZ",
                    "is_official": True,
                },
                "title": request.title,
                "url": str(request.url),
                "source_type": "manual",
                "domains": request.domains,
                "languages": request.languages,
                "crawl_policy": "manual_only",
                "adapter_key": "generic-manual",
                "trust_tier": 1,
                "status": "approved",
                "owner": "admin",
                "reviewed_at": created_at,
                "production_eligible": True,
            }
        )
        self.managed.append(source)
        self.created[idempotency_key] = (request.sha256, source)
        return source

    def list_jobs(self, *, limit: int):
        return tuple(list(self.jobs.values())[:limit])

    def list_topics(self):
        return ("Entry requirements",)

    def prepare_crawl_job(
        self,
        source_id: UUID,
        idempotency_key: str,
        *,
        max_attempts: int,
        scheduled_at: datetime,
    ) -> PreparedCrawlJob:
        key = (source_id, idempotency_key)
        existing = self.jobs.get(key)
        if existing is not None:
            return PreparedCrawlJob(record=existing, created=False)
        record = IngestionJobRecord(
            id=uuid4(),
            source_id=source_id,
            source_title="Approved test source",
            idempotency_key=idempotency_key,
            status="queued",
            attempt_count=0,
            max_attempts=max_attempts,
            scheduled_at=scheduled_at,
            started_at=None,
            completed_at=None,
        )
        self.jobs[key] = record
        return PreparedCrawlJob(record=record, created=True)


class MemoryQueue:
    def __init__(self) -> None:
        self.tasks = []

    def publish(self, task):
        self.tasks.append(task)
        return str(len(self.tasks))


class StubIngestionService:
    def __init__(self) -> None:
        self.calls = []

    def run_manual(
        self,
        source,
        response,
        *,
        idempotency_key,
        max_attempts,
        topic,
    ):
        self.calls.append((source, response, idempotency_key, max_attempts, topic))
        return IngestionOutcome(
            status=ChangeStatus.CHANGED,
            source_id=source.id,
            snapshot_id=uuid4(),
            sha256="1" * 64,
            normalized_sha256="2" * 64,
            storage_key=f"sources/{source.id}/snapshot.bin",
            extraction_artifact_id=uuid4(),
            review_item_id=uuid4(),
        )


def admin_service():
    source = approved_source()
    repository = MemoryAdminRepository()
    queue = MemoryQueue()
    ingestion = StubIngestionService()
    service = AdminIngestionService(
        registry=SourceRegistry(
            registry_version="1.1",
            environment="development",
            sources=[source],
        ),
        repository=repository,
        queue=queue,
        ingestion_service=ingestion,
    )
    return service, source, repository, queue, ingestion


def test_admin_lists_source_eligibility_and_queues_crawl_idempotently() -> None:
    service, source, _, queue, _ = admin_service()
    actor = principal("admin")

    records = service.list_sources(actor)
    first = service.queue_crawl(
        actor,
        QueueCrawlRequest(source_id=source.id),
        idempotency_key="manual-crawl-1",
        enqueued_at=NOW,
    )
    replay = service.queue_crawl(
        actor,
        QueueCrawlRequest(source_id=source.id),
        idempotency_key="manual-crawl-1",
        enqueued_at=NOW,
    )

    assert records[0].manual_upload_eligible is True
    assert records[0].automatic_fetch_eligible is True
    assert records[0].active is False
    assert replay.id == first.id
    assert len(queue.tasks) == 1
    assert queue.tasks[0].source_id == source.id


def test_admin_creates_manual_only_source_idempotently_without_expanding_crawler_scope() -> None:
    service, _, repository, _, _ = admin_service()
    actor = principal("admin")
    request = CreateAdminSourceRequest(
        title="Official tourism handbook",
        url="https://tourism.gov.uz/handbook",
        organization_name="Tourism Committee",
        organization_website_url="https://gov.uz",
        domains=["tourism"],
        languages=["uz"],
        confirmed_official=True,
    )

    created = service.create_source(
        actor,
        request,
        idempotency_key="create-source-1",
        created_at=NOW,
    )
    replay = service.create_source(
        actor,
        request,
        idempotency_key="create-source-1",
        created_at=NOW,
    )

    assert created.id == replay.id
    assert created.manual_upload_eligible is True
    assert created.automatic_fetch_eligible is False
    assert created.crawl_policy == "manual_only"
    assert created.trust_tier == 1
    assert len(repository.managed) == 1
    assert any(source.id == created.id for source in service.list_sources(actor))


def test_source_creation_requires_matching_public_https_organization_domain() -> None:
    with pytest.raises(ValueError, match="official organization website domain"):
        CreateAdminSourceRequest(
            title="Unrelated source",
            url="https://example.com/rules",
            organization_name="Tourism Committee",
            organization_website_url="https://gov.uz",
            domains=["tourism"],
            confirmed_official=True,
        )

    with pytest.raises(ValueError, match="HTTPS"):
        CreateAdminSourceRequest(
            title="Insecure source",
            url="http://gov.uz/rules",
            organization_name="Tourism Committee",
            organization_website_url="https://gov.uz",
            domains=["tourism"],
            confirmed_official=True,
        )


def test_non_admin_cannot_read_or_mutate_ingestion_operations() -> None:
    service, source, _, _, _ = admin_service()
    actor = principal("content_reviewer")

    with pytest.raises(AdminIngestionError, match="administrator role") as denied:
        service.list_sources(actor)
    assert denied.value.code == "admin_forbidden"

    with pytest.raises(AdminIngestionError, match="administrator role"):
        service.queue_crawl(
            actor,
            QueueCrawlRequest(source_id=source.id),
            idempotency_key="manual-crawl-1",
            enqueued_at=NOW,
        )


def test_read_only_service_does_not_require_queue_or_object_storage() -> None:
    source = approved_source()
    repository = MemoryAdminRepository()
    service = AdminIngestionService(
        registry=SourceRegistry(
            registry_version="1.1",
            environment="production",
            sources=[source],
        ),
        repository=repository,
    )
    actor = principal("admin")

    assert service.list_sources(actor)[0].id == source.id
    assert service.list_jobs(actor, limit=50) == ()
    assert service.list_topics(actor) == ("Entry requirements",)

    with pytest.raises(AdminIngestionError) as unavailable:
        service.queue_crawl(
            actor,
            QueueCrawlRequest(source_id=source.id),
            idempotency_key="manual-crawl-1",
            enqueued_at=NOW,
        )
    assert unavailable.value.code == "ingestion_infrastructure_unavailable"
    assert repository.jobs == {}


def test_admin_upload_decodes_content_and_runs_manual_ingestion() -> None:
    service, source, _, _, ingestion = admin_service()
    document = b"<h1>Official guidance</h1><p>Verified rule.</p>"
    request = ManualUploadRequest(
        filename="official-guidance.html",
        content_type="text/html",
        content_base64=b64encode(document).decode("ascii"),
        topic="Entry requirements",
    )

    result = service.upload(
        principal("admin"),
        source.id,
        request,
        idempotency_key="upload-guidance-v1",
        uploaded_at=NOW,
    )

    assert result.status == "changed"
    assert result.review_item_id is not None
    _, response, key, attempts, topic = ingestion.calls[0]
    assert response.body == document
    assert response.headers["X-Uzbekistan-OS-Filename"] == request.filename
    assert key == "upload-guidance-v1"
    assert attempts == 1
    assert topic == "Entry requirements"
    assert result.topic == "Entry requirements"


def test_upload_rejects_invalid_base64_and_file_paths() -> None:
    service, source, _, _, _ = admin_service()
    actor = principal("admin")
    request = ManualUploadRequest(
        filename="official.txt",
        content_type="text/plain",
        content_base64="not-base64!",
        topic="Entry requirements",
    )

    with pytest.raises(AdminIngestionError) as invalid:
        service.upload(
            actor,
            source.id,
            request,
            idempotency_key="upload-invalid",
            uploaded_at=NOW,
        )
    assert invalid.value.code == "invalid_upload_encoding"

    with pytest.raises(ValueError, match="directory path"):
        ManualUploadRequest(
            filename="../official.txt",
            content_type="text/plain",
            content_base64=b64encode(b"safe").decode("ascii"),
            topic="Entry requirements",
        )

    with pytest.raises(ValueError, match="extension"):
        ManualUploadRequest(
            filename="official.pdf",
            content_type="application/json",
            content_base64=b64encode(b"{}").decode("ascii"),
            topic="Entry requirements",
        )
