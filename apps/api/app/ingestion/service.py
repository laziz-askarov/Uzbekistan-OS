from collections.abc import Mapping
from hashlib import sha256
from uuid import uuid4

from app.ingestion.errors import IngestionError, SourceNotEligibleError
from app.ingestion.models import SourceRegistryEntry
from app.ingestion.normalizers import normalize_response
from app.ingestion.ports import IngestionRepository, SnapshotStore, SourceFetcher
from app.ingestion.types import ChangeStatus, IngestionOutcome, SnapshotMetadata


class IngestionService:
    def __init__(
        self,
        *,
        fetcher: SourceFetcher,
        snapshot_store: SnapshotStore,
        repository: IngestionRepository,
        max_response_bytes: int = 10_000_000,
    ) -> None:
        self.fetcher = fetcher
        self.snapshot_store = snapshot_store
        self.repository = repository
        self.max_response_bytes = max_response_bytes

    def run(
        self,
        source: SourceRegistryEntry,
        *,
        idempotency_key: str,
        max_attempts: int = 3,
    ) -> IngestionOutcome:
        if not source.automatic_fetch_eligible:
            raise SourceNotEligibleError
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
            outcome = self._fetch_and_snapshot(source)
        except IngestionError as error:
            self.repository.mark_failed(claim.id, error, retryable=error.retryable)
            raise
        except Exception as error:
            self.repository.mark_failed(claim.id, error, retryable=True)
            raise

        self.repository.mark_succeeded(claim.id, outcome)
        return outcome

    def _fetch_and_snapshot(self, source: SourceRegistryEntry) -> IngestionOutcome:
        previous = self.repository.latest_snapshot(source.id)
        response = self.fetcher.fetch(source, self._conditional_headers(previous))

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

        raw_sha256 = sha256(response.body).hexdigest()
        if previous is not None and previous.sha256 == raw_sha256:
            return self._unchanged(source, previous)

        normalized = normalize_response(response)
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
        self.snapshot_store.put(storage_key, response.body)
        self.repository.record_snapshot(snapshot)
        return IngestionOutcome(
            status=ChangeStatus.CHANGED,
            source_id=source.id,
            snapshot_id=snapshot_id,
            sha256=raw_sha256,
            normalized_sha256=normalized.sha256,
            storage_key=storage_key,
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
