from base64 import b64decode
from binascii import Error as Base64Error
from datetime import datetime
from hashlib import sha256
from ipaddress import ip_address
from json import dumps
from pathlib import PurePath
from typing import Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.identity.service import AuthenticatedPrincipal
from app.ingestion.models import DomainSlug, LanguageCode, SourceRegistry, SourceRegistryEntry
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
    organization_website_url: AnyHttpUrl
    title: str
    url: AnyHttpUrl
    source_type: str
    domains: list[DomainSlug]
    languages: list[LanguageCode]
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
    editable: bool


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


class CreateAdminSourceRequest(BaseModel):
    """Register a manual-only official source without expanding crawler scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(min_length=2, max_length=500)
    url: HttpUrl
    organization_name: str = Field(min_length=2, max_length=240)
    organization_website_url: HttpUrl
    domains: list[DomainSlug] = Field(min_length=1)
    languages: list[LanguageCode] = Field(default_factory=lambda: ["uz"], min_length=1)
    confirmed_official: Literal[True]

    @field_validator("title", "organization_name")
    @classmethod
    def text_must_be_safe(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2 or not cleaned.isprintable():
            raise ValueError("source text must contain printable characters")
        return cleaned

    @field_validator("url", "organization_website_url")
    @classmethod
    def url_must_be_public_https(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlsplit(str(value))
        hostname = parsed.hostname or ""
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("source URLs must use HTTPS without credentials or fragments")
        if hostname.casefold() == "localhost" or "." not in hostname:
            raise ValueError("source URLs must use a public hostname")
        try:
            address = ip_address(hostname)
        except ValueError:
            return value
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_unspecified
        ):
            raise ValueError("source URLs must not use private or reserved addresses")
        raise ValueError("source URLs must use a public domain name instead of an IP address")

    @model_validator(mode="after")
    def validate_scope_and_organization(self) -> "CreateAdminSourceRequest":
        if len(self.domains) != len(set(self.domains)):
            raise ValueError("source domains must be unique")
        if len(self.languages) != len(set(self.languages)):
            raise ValueError("source languages must be unique")
        source_host = (urlsplit(str(self.url)).hostname or "").casefold()
        organization_host = (urlsplit(str(self.organization_website_url)).hostname or "").casefold()
        if source_host != organization_host and not source_host.endswith(f".{organization_host}"):
            raise ValueError("source URL must use the official organization website domain")
        return self

    @property
    def sha256(self) -> str:
        canonical = dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return sha256(canonical).hexdigest()


class UpdateAdminSourceRequest(CreateAdminSourceRequest):
    """Update audited source metadata without changing crawler implementation details."""

    active: bool = True


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
    manual_correction: bool = False
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
    manual_correction: bool
    status: str
    snapshot_id: UUID | None
    extraction_artifact_id: UUID | None
    review_item_id: UUID | None

    @classmethod
    def from_outcome(
        cls,
        filename: str,
        topic: str,
        manual_correction: bool,
        outcome: IngestionOutcome,
    ) -> "ManualUploadResult":
        return cls(
            source_id=outcome.source_id,
            filename=filename,
            topic=topic,
            manual_correction=manual_correction,
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

    def managed_sources(self) -> tuple[SourceRegistryEntry, ...]: ...

    def create_managed_source(
        self,
        request: CreateAdminSourceRequest,
        principal: AuthenticatedPrincipal,
        *,
        idempotency_key: str,
        created_at: datetime,
    ) -> SourceRegistryEntry: ...

    def update_managed_source(
        self,
        current: SourceRegistryEntry,
        request: UpdateAdminSourceRequest,
        principal: AuthenticatedPrincipal,
        *,
        updated_at: datetime,
    ) -> SourceRegistryEntry: ...

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
        sources = self._configured_sources()
        return tuple(self._source_record(source, states.get(source.id)) for source in sources)

    def create_source(
        self,
        principal: AuthenticatedPrincipal,
        request: CreateAdminSourceRequest,
        *,
        idempotency_key: str,
        created_at: datetime,
    ) -> AdminSourceRecord:
        self._authorize(principal)
        source = self.repository.create_managed_source(
            request,
            principal,
            idempotency_key=idempotency_key,
            created_at=created_at,
        )
        state = next(
            (item for item in self.repository.source_states() if item.id == source.id),
            None,
        )
        return self._source_record(source, state)

    def update_source(
        self,
        principal: AuthenticatedPrincipal,
        source_id: UUID,
        request: UpdateAdminSourceRequest,
        *,
        updated_at: datetime,
    ) -> AdminSourceRecord:
        self._authorize(principal)
        current = self._source(source_id)
        source = self.repository.update_managed_source(
            current,
            request,
            principal,
            updated_at=updated_at,
        )
        state = next(
            (item for item in self.repository.source_states() if item.id == source.id),
            None,
        )
        return self._source_record(source, state)

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
            filename=request.filename,
            manual_correction=request.manual_correction,
        )
        return ManualUploadResult.from_outcome(
            request.filename,
            request.topic,
            request.manual_correction,
            outcome,
        )

    def _source(self, source_id: UUID):
        source = next((item for item in self._configured_sources() if item.id == source_id), None)
        if source is None:
            raise AdminIngestionError(
                "source_not_found",
                "source is not present in the configured or admin-managed sources",
            )
        return source

    def _configured_sources(self) -> tuple[SourceRegistryEntry, ...]:
        sources = {source.id: source for source in self.registry.sources}
        # Database-managed metadata intentionally wins over the static registry.
        # Adapter keys and crawl policy remain copied from the reviewed registry,
        # while audited source metadata can be corrected without a code deploy.
        sources.update({source.id: source for source in self.repository.managed_sources()})
        return tuple(sorted(sources.values(), key=lambda source: (source.title, str(source.id))))

    @staticmethod
    def _source_record(
        source: SourceRegistryEntry,
        state: SourceDatabaseState | None,
    ) -> AdminSourceRecord:
        return AdminSourceRecord(
            id=source.id,
            slug=source.slug,
            organization=source.organization.name,
            organization_website_url=source.organization.website_url,
            title=source.title,
            url=source.url,
            source_type=source.source_type.value,
            domains=list(source.domains),
            languages=list(source.languages),
            crawl_policy=source.crawl_policy.value,
            adapter_key=source.adapter_key,
            trust_tier=source.trust_tier,
            registry_status=source.status.value,
            active=state.active if state else False,
            production_eligible=source.production_eligible,
            automatic_fetch_eligible=source.automatic_fetch_eligible,
            manual_upload_eligible=source.manual_ingestion_eligible,
            schedule_interval_minutes=(
                source.schedule.interval_minutes if source.schedule else None
            ),
            last_verified_at=state.last_verified_at if state else None,
            latest_job_status=state.latest_job_status if state else None,
            editable=state is not None,
        )

    @staticmethod
    def _authorize(principal: AuthenticatedPrincipal) -> None:
        if not principal.roles.intersection(ADMIN_ROLES):
            raise AdminIngestionError("admin_forbidden", "administrator role is required")
