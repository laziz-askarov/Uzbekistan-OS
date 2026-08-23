from collections.abc import Callable, Mapping
from hashlib import sha256
from uuid import uuid4

from app.ingestion.adapters import SourceAdapterRegistry
from app.ingestion.errors import IngestionError, SourceNotEligibleError
from app.ingestion.extractors import extract_artifact
from app.ingestion.models import SourceRegistryEntry, SourceType
from app.ingestion.normalizers import JSON_MEDIA_TYPES, PDF_MEDIA_TYPES
from app.ingestion.ports import IngestionRepository, SnapshotStore, SourceFetcher
from app.ingestion.types import (
    ChangeStatus,
    ExtractionArtifactMetadata,
    FetchResponse,
    IngestionOutcome,
    JobStatus,
    ReviewItemMetadata,
    SnapshotMetadata,
)


class IngestionService:
    def __init__(
        self,
        *,
        fetcher: SourceFetcher,
        snapshot_store: SnapshotStore,
        repository: IngestionRepository,
        max_response_bytes: int = 10_000_000,
        max_pdf_pages: int = 250,
        max_normalized_characters: int = 2_000_000,
        adapter_registry: SourceAdapterRegistry | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.snapshot_store = snapshot_store
        self.repository = repository
        self.max_response_bytes = max_response_bytes
        self.max_pdf_pages = max_pdf_pages
        self.max_normalized_characters = max_normalized_characters
        self.adapter_registry = adapter_registry or SourceAdapterRegistry()

    def run(
        self,
        source: SourceRegistryEntry,
        *,
        idempotency_key: str,
        max_attempts: int = 3,
    ) -> IngestionOutcome:
        if not source.automatic_fetch_eligible:
            raise SourceNotEligibleError
        return self._run_claimed(
            source,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            operation=lambda: self._fetch_and_snapshot(source),
        )

    def run_manual(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        idempotency_key: str,
        max_attempts: int = 1,
        topic: str | None = None,
    ) -> IngestionOutcome:
        if not source.manual_ingestion_eligible:
            raise SourceNotEligibleError
        return self._run_claimed(
            source,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            operation=lambda: self._snapshot_response(
                source,
                response,
                self.repository.latest_snapshot(source.id),
                manual_upload=True,
                topic=topic,
            ),
        )

    def _run_claimed(
        self,
        source: SourceRegistryEntry,
        *,
        idempotency_key: str,
        max_attempts: int,
        operation: Callable[[], IngestionOutcome],
    ) -> IngestionOutcome:
        if not idempotency_key or len(idempotency_key) > 128:
            raise IngestionError(
                "invalid_idempotency_key",
                "idempotency key must contain between 1 and 128 characters",
                retryable=False,
            )
        if max_attempts < 1:
            raise IngestionError(
                "invalid_max_attempts",
                "max attempts must be positive",
                retryable=False,
            )

        claim = self.repository.claim_job(source.id, idempotency_key, max_attempts)
        if claim.replay is not None:
            return claim.replay

        try:
            outcome = operation()
        except IngestionError as error:
            status = self.repository.mark_failed(
                claim.id,
                error,
                retryable=error.retryable,
            )
            error.retryable = status is JobStatus.RETRY_SCHEDULED
            raise
        except Exception as error:
            status = self.repository.mark_failed(claim.id, error, retryable=True)
            raise IngestionError(
                "ingestion_error",
                "ingestion failed unexpectedly",
                retryable=status is JobStatus.RETRY_SCHEDULED,
            ) from error

        self.repository.mark_succeeded(claim.id, outcome)
        return outcome

    def _fetch_and_snapshot(self, source: SourceRegistryEntry) -> IngestionOutcome:
        previous = self.repository.latest_snapshot(source.id)
        response = self.fetcher.fetch(source, self._conditional_headers(previous))

        return self._snapshot_response(source, response, previous)

    def _snapshot_response(
        self,
        source: SourceRegistryEntry,
        response: FetchResponse,
        previous: SnapshotMetadata | None,
        *,
        manual_upload: bool = False,
        topic: str | None = None,
    ) -> IngestionOutcome:

        if response.url != str(source.url):
            raise IngestionError(
                "unexpected_response_url",
                "source response URL differs from its approved registry URL",
                retryable=False,
            )
        if response.status_code == 304:
            if previous is None:
                raise IngestionError(
                    "invalid_not_modified",
                    "source returned not-modified without a prior snapshot",
                    retryable=True,
                )
            return self._unchanged(source, previous)
        if not 200 <= response.status_code < 300:
            retryable = response.status_code in {408, 425, 429} or response.status_code >= 500
            raise IngestionError(
                "fetch_http_error",
                f"source returned HTTP {response.status_code}",
                retryable=retryable,
            )
        if len(response.body) > self.max_response_bytes:
            raise IngestionError(
                "response_too_large",
                f"source response exceeds {self.max_response_bytes} bytes",
                retryable=False,
            )

        self._validate_source_media_type(source, response, manual_upload=manual_upload)

        raw_sha256 = sha256(response.body).hexdigest()
        existing = self.repository.snapshot_by_sha256(source.id, raw_sha256)
        if existing is not None:
            return self._unchanged(source, existing)

        if manual_upload:
            adapter_key, adapter = self.adapter_registry.resolve_manual(source, response)
        else:
            adapter_key = source.adapter_key
            adapter = self.adapter_registry.resolve(source.adapter_key)
        normalized = adapter.normalize(
            source,
            response,
            max_pdf_pages=self.max_pdf_pages,
            max_characters=self.max_normalized_characters,
        )
        snapshot_id = uuid4()
        storage_key = f"sources/{source.id}/{raw_sha256}.bin"
        snapshot = SnapshotMetadata(
            id=snapshot_id,
            source_id=source.id,
            storage_key=storage_key,
            sha256=raw_sha256,
            normalized_sha256=normalized.sha256,
            http_status=response.status_code,
            content_type=response.header("content-type"),
            etag=response.header("etag"),
            last_modified=response.header("last-modified"),
            fetched_at=response.fetched_at,
            byte_size=len(response.body),
        )
        artifact = extract_artifact(
            source,
            snapshot,
            response,
            normalized,
            adapter_key=adapter_key,
            topic=topic,
        )
        artifact_id = uuid4()
        artifact_bytes = artifact.canonical_bytes()
        artifact_storage_key = (
            f"sources/{source.id}/{raw_sha256}.{adapter_key}.extraction.json"
        )
        normalized_storage_key = None
        if normalized.media_type == "text/markdown":
            normalized_storage_key = f"sources/{source.id}/{raw_sha256}.normalized.md"
        artifact_details: dict[str, object] = {
            "media_type": artifact.media_type,
            "source_media_type": response.header("content-type") or "",
        }
        if topic:
            artifact_details["topic"] = topic
        if normalized_storage_key:
            artifact_details["normalized_storage_key"] = normalized_storage_key
        review_item_id = uuid4()
        self.snapshot_store.put(
            storage_key,
            response.body,
            content_type=response.header("content-type") or "application/octet-stream",
        )
        self.snapshot_store.put(
            artifact_storage_key,
            artifact_bytes,
            content_type="application/json",
        )
        if normalized_storage_key is not None:
            self.snapshot_store.put(
                normalized_storage_key,
                normalized.text.encode("utf-8"),
                content_type="text/markdown; charset=utf-8",
            )
        self.repository.record_snapshot(snapshot)
        self.repository.record_extraction_artifact(
            ExtractionArtifactMetadata(
                id=artifact_id,
                source_snapshot_id=snapshot_id,
                adapter_key=adapter_key,
                schema_version=artifact.schema_version,
                storage_key=artifact_storage_key,
                sha256=artifact.sha256,
                normalized_sha256=normalized.sha256,
                section_count=len(artifact.sections),
                details=artifact_details,
            )
        )
        self.repository.enqueue_review(
            ReviewItemMetadata(
                id=review_item_id,
                extraction_artifact_id=artifact_id,
                priority=50,
            )
        )
        return IngestionOutcome(
            status=ChangeStatus.CHANGED,
            source_id=source.id,
            snapshot_id=snapshot_id,
            sha256=raw_sha256,
            normalized_sha256=normalized.sha256,
            storage_key=storage_key,
            extraction_artifact_id=artifact_id,
            review_item_id=review_item_id,
        )

    @staticmethod
    def _conditional_headers(previous: SnapshotMetadata | None) -> Mapping[str, str]:
        if previous is None:
            return {}
        headers: dict[str, str] = {}
        if previous.etag:
            headers["If-None-Match"] = previous.etag
        if previous.last_modified:
            headers["If-Modified-Since"] = previous.last_modified
        return headers

    @staticmethod
    def _validate_source_media_type(
        source: SourceRegistryEntry,
        response: FetchResponse,
        *,
        manual_upload: bool = False,
    ) -> None:
        media_type = (response.header("content-type") or "").split(";", 1)[0].strip().casefold()
        is_pdf = media_type in PDF_MEDIA_TYPES
        is_json = media_type in JSON_MEDIA_TYPES
        if manual_upload and (is_pdf or is_json):
            return
        if source.source_type is SourceType.PDF and not is_pdf:
            raise IngestionError(
                "source_content_type_mismatch",
                "registered PDF source did not return application/pdf",
                retryable=False,
            )
        if source.source_type is not SourceType.PDF and is_pdf:
            raise IngestionError(
                "source_content_type_mismatch",
                "PDF response requires a source registered with type pdf",
                retryable=False,
            )
        if source.source_type is SourceType.FEED and not is_json:
            raise IngestionError(
                "source_content_type_mismatch",
                "registered feed source did not return JSON",
                retryable=False,
            )
        if source.source_type is not SourceType.FEED and is_json:
            raise IngestionError(
                "source_content_type_mismatch",
                "JSON response requires a source registered with type feed",
                retryable=False,
            )

    @staticmethod
    def _unchanged(
        source: SourceRegistryEntry,
        previous: SnapshotMetadata,
    ) -> IngestionOutcome:
        return IngestionOutcome(
            status=ChangeStatus.UNCHANGED,
            source_id=source.id,
            snapshot_id=previous.id,
            sha256=previous.sha256,
            normalized_sha256=previous.normalized_sha256,
            storage_key=previous.storage_key,
        )
