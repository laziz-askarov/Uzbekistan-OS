from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.identity.service import AuthenticatedPrincipal

PUBLISHER_ROLES = frozenset({"knowledge_publisher", "admin"})
IndexJobStatus = Literal[
    "queued",
    "running",
    "retry_scheduled",
    "succeeded",
    "dead_lettered",
    "cancelled",
]


class KnowledgeLifecycleError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ExpireDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("expiration reason cannot be blank")
        return value


class ReindexDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_key: str = Field(min_length=1, max_length=160)
    max_attempts: int = Field(default=3, ge=1, le=10)

    @field_validator("model_key")
    @classmethod
    def value_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("index request values cannot be blank")
        return value


class ExpireDocumentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lifecycle_event_id: UUID
    document_id: UUID
    document_version_id: UUID
    status: Literal["expired"]
    reason: str
    expired_at: datetime


class IndexJobResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index_job_id: UUID
    document_id: UUID
    document_version_id: UUID
    idempotency_key: str
    model_key: str
    status: IndexJobStatus
    attempt_count: int
    max_attempts: int
    scheduled_at: datetime


class KnowledgeLifecycleRepository(Protocol):
    def expire_document(
        self,
        document_id: UUID,
        reason: str,
        principal: AuthenticatedPrincipal,
        *,
        expired_at: datetime,
    ) -> ExpireDocumentResult: ...

    def queue_reindex(
        self,
        document_id: UUID,
        request: ReindexDocumentRequest,
        principal: AuthenticatedPrincipal,
        *,
        idempotency_key: str,
        requested_at: datetime,
    ) -> IndexJobResult: ...


class KnowledgeLifecycleService:
    def __init__(self, repository: KnowledgeLifecycleRepository) -> None:
        self.repository = repository

    def expire(
        self,
        principal: AuthenticatedPrincipal,
        document_id: UUID,
        request: ExpireDocumentRequest,
        *,
        expired_at: datetime,
    ) -> ExpireDocumentResult:
        self._authorize(principal)
        self._validate_time(expired_at)
        return self.repository.expire_document(
            document_id,
            request.reason,
            principal,
            expired_at=expired_at,
        )

    def reindex(
        self,
        principal: AuthenticatedPrincipal,
        document_id: UUID,
        request: ReindexDocumentRequest,
        *,
        idempotency_key: str,
        requested_at: datetime,
    ) -> IndexJobResult:
        self._authorize(principal)
        self._validate_time(requested_at)
        return self.repository.queue_reindex(
            document_id,
            request,
            principal,
            idempotency_key=idempotency_key,
            requested_at=requested_at,
        )

    @staticmethod
    def _authorize(principal: AuthenticatedPrincipal) -> None:
        if not principal.roles.intersection(PUBLISHER_ROLES):
            raise KnowledgeLifecycleError(
                "publication_forbidden",
                "knowledge publisher or administrator role is required",
            )

    @staticmethod
    def _validate_time(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise KnowledgeLifecycleError(
                "invalid_lifecycle_time",
                "knowledge lifecycle time must be timezone-aware",
            )
