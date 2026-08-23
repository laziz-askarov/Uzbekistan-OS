from base64 import b64decode
from binascii import Error as Base64Error
from datetime import datetime
from pathlib import PurePath
from typing import Literal, Protocol
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.models import SourceRegistry
from app.ingestion.queue import IngestionQueue, IngestionTask
from app.ingestion.service import IngestionService
from app.ingestion.types import FetchResponse, IngestionOutcome

ADMIN_ROLES = frozenset({"admin"})


class AdminIngestionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class SourceDatabaseState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    active: bool
    last_verified_at: datetime | None
    latest_job_status: str | None


class AdminSourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    slug: str
    organization: str
    title: str
    url: AnyHttpUrl
    source_type: str
    domains: list[str]
    languages: list[str]
    crawl_policy: str
    adapter_key: str
    trust_tier: int
    registry_status: str
    active: bool
    production_eligible: bool
    automatic_fetch_eligible: bool
    manual_upload_eligible: bool
    schedule_interval_minutes: int | None
    last_verified_at: datetime | None
    latest_job_status: str | None


class IngestionJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    source_id: UUID
    source_title: str
    idempotency_key: str
    status: str
    attempt_count: int
    max_attempts: int
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None = None
    error_message: str | None = None


class QueueCrawlRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    max_attempts: int = Field(default=3, ge=1, le=20)


class ManualUploadRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal[
        "application/pdf",
        "application/json",
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    ]
    content_base64: str = Field(min_length=1, max_length=14_000_000)
    topic: str = Field(min_length=2, max_length=120)
    max_attempts: int = Field(default=1, ge=1, le=3)

    @field_validator("topic")
    @classmethod
    def topic_must_be_safe_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2 or not cleaned.isprintable():
            raise ValueError("topic must contain printable text")
        return cleaned

    @field_validator("filename")
    @classmethod
    def filename_must_be_plain(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or PurePath(cleaned).name != cleaned or cleaned in {".", ".."}:
            raise ValueError("filename must not contain a directory path")
        return cleaned

    @field_validator("content_type", mode="before")
    @classmethod
    def content_type_must_be_supported(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("upload content type is not supported")
        media_type = value.split(";", 1)[0].strip().casefold()
        if media_type not in {
            "application/pdf",
            "text/html",
            "application/xhtml+xml",
            "application/json",
            "text/plain",
        }:
            raise ValueError("upload content type is not supported")
        return media_type

    @model_validator(mode="after")
    def filename_must_match_content_type(self) -> "ManualUploadRequest":
        suffix = PurePath(self.filename).suffix.casefold()
        allowed_suffixes = {
            "application/pdf": {".pdf"},
            "application/json": {".json"},
            "text/html": {".htm", ".html"},
            "application/xhtml+xml": {".html", ".xhtml"},
            "text/plain": {".txt"},
        }
        if suffix not in allowed_suffixes[self.content_type]:
            raise ValueError("filename extension does not match upload content type")
        return self

    def decoded_content(self) -> bytes:
        try:
            content = b64decode(self.content_base64, validate=True)
        except (Base64Error, ValueError) as error:
            raise AdminIngestionError(
                "invalid_upload_encoding",
                "uploaded document is not valid base64",
            ) from error
        if not content:
            raise AdminIngestionError("empty_upload", "uploaded document is empty")
        if len(content) > 10_000_000:
            raise AdminIngestionError(
                "upload_too_large",
                "uploaded document exceeds 10 MB",
            )
        return content


class ManualUploadResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    filename: str
    topic: str
    status: str
    snapshot_id: UUID | None
    extraction_artifact_id: UUID | None
    review_item_id: UUID | None

    @classmethod
    def from_outcome(
        cls,
        filename: str,
        topic: str,
        outcome: IngestionOutcome,
    ) -> "ManualUploadResult":
        return cls(
            source_id=outcome.source_id,
            filename=filename,
            topic=topic,
            status=outcome.status.value,
            snapshot_id=outcome.snapshot_id,
            extraction_artifact_id=outcome.extraction_artifact_id,
            review_item_id=outcome.review_item_id,
        )


class PreparedCrawlJob(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record: IngestionJobRecord
    created: bool


class AdminIngestionRepository(Protocol):
    def source_states(self) -> tuple[SourceDatabaseState, ...]: ...

    def list_jobs(self, *, limit: int) -> tuple[IngestionJobRecord, ...]: ...

    def list_topics(self) -> tuple[str, ...]: ...

    def prepare_crawl_job(
        self,
        source_id: UUID,
        idempotency_key: str,
        *,
        max_attempts: int,
        scheduled_at: datetime,
    ) -> PreparedCrawlJob: ...


class AdminIngestionService:
    def __init__(
        self,
        *,
        registry: SourceRegistry,
        repository: AdminIngestionRepository,
        queue: IngestionQueue | None = None,
        ingestion_service: IngestionService | None = None,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.queue = queue
        self.ingestion_service = ingestion_service

    def list_sources(
        self,
        principal: AuthenticatedPrincipal,
    ) -> tuple[AdminSourceRecord, ...]:
        self._authorize(principal)
        states = {state.id: state for state in self.repository.source_states()}
        return tuple(
            AdminSourceRecord(
                id=source.id,
                slug=source.slug,
                organization=source.organization.name,
                title=source.title,
                url=source.url,
                source_type=source.source_type.value,
                domains=list(source.domains),
                languages=list(source.languages),
                crawl_policy=source.crawl_policy.value,
                adapter_key=source.adapter_key,
                trust_tier=source.trust_tier,
                registry_status=source.status.value,
                active=states.get(source.id).active if source.id in states else False,
                production_eligible=source.production_eligible,
                automatic_fetch_eligible=source.automatic_fetch_eligible,
                manual_upload_eligible=source.manual_ingestion_eligible,
                schedule_interval_minutes=(
                    source.schedule.interval_minutes if source.schedule else None
                ),
                last_verified_at=(
                    states.get(source.id).last_verified_at if source.id in states else None
                ),
                latest_job_status=(
                    states.get(source.id).latest_job_status if source.id in states else None
                ),
            )
            for source in self.registry.sources
        )

    def list_jobs(
        self,
        principal: AuthenticatedPrincipal,
        *,
        limit: int,
    ) -> tuple[IngestionJobRecord, ...]:
        self._authorize(principal)
        return self.repository.list_jobs(limit=limit)

    def list_topics(self, principal: AuthenticatedPrincipal) -> tuple[str, ...]:
        self._authorize(principal)
        return self.repository.list_topics()

    def queue_crawl(
        self,
        principal: AuthenticatedPrincipal,
        request: QueueCrawlRequest,
        *,
        idempotency_key: str,
        enqueued_at: datetime,
    ) -> IngestionJobRecord:
        self._authorize(principal)
        source = self._source(request.source_id)
        if not source.automatic_fetch_eligible:
            raise AdminIngestionError(
                "source_not_crawl_eligible",
                "source is not approved for automatic crawling",
            )
        if self.queue is None:
            raise AdminIngestionError(
                "ingestion_infrastructure_unavailable",
                "crawler operations are unavailable until the ingestion queue is configured",
            )
        prepared = self.repository.prepare_crawl_job(
            source.id,
            idempotency_key,
            max_attempts=request.max_attempts,
            scheduled_at=enqueued_at,
        )
        if prepared.created:
            self.queue.publish(
                IngestionTask(
                    source_id=source.id,
                    idempotency_key=idempotency_key,
                    max_attempts=request.max_attempts,
                    enqueued_at=enqueued_at,
                )
            )
        return prepared.record

    def upload(
        self,
        principal: AuthenticatedPrincipal,
        source_id: UUID,
        request: ManualUploadRequest,
        *,
        idempotency_key: str,
        uploaded_at: datetime,
    ) -> ManualUploadResult:
        self._authorize(principal)
        source = self._source(source_id)
        if not source.manual_ingestion_eligible:
            raise AdminIngestionError(
                "source_not_upload_eligible",
                "source is not approved for manual evidence uploads",
            )
        if self.ingestion_service is None:
            raise AdminIngestionError(
                "ingestion_infrastructure_unavailable",
                "document uploads are unavailable until evidence storage is configured",
            )
        content = request.decoded_content()
        outcome = self.ingestion_service.run_manual(
            source,
            FetchResponse(
                url=str(source.url),
                status_code=200,
                body=content,
                fetched_at=uploaded_at,
                headers={
                    "Content-Type": request.content_type,
                    "X-Uzbekistan-OS-Filename": request.filename,
                },
            ),
            idempotency_key=idempotency_key,
            max_attempts=request.max_attempts,
            topic=request.topic,
        )
        return ManualUploadResult.from_outcome(request.filename, request.topic, outcome)

    def _source(self, source_id: UUID):
        source = next((item for item in self.registry.sources if item.id == source_id), None)
        if source is None:
            raise AdminIngestionError(
                "source_not_found",
                "source is not present in the configured environment registry",
            )
        return source

    @staticmethod
    def _authorize(principal: AuthenticatedPrincipal) -> None:
        if not principal.roles.intersection(ADMIN_ROLES):
            raise AdminIngestionError("admin_forbidden", "administrator role is required")
