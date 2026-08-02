from dataclasses import replace
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.identity.service import AuthenticatedPrincipal
from app.knowledge.lifecycle import (
    ExpireDocumentRequest,
    ExpireDocumentResult,
    IndexJobResult,
    KnowledgeLifecycleError,
    KnowledgeLifecycleService,
    ReindexDocumentRequest,
)
from app.knowledge.lifecycle_repositories import SqlAlchemyKnowledgeLifecycleRepository


class MemoryLifecycleRepository:
    def __init__(self) -> None:
        self.expirations: list[tuple] = []
        self.index_requests: list[tuple] = []

    def expire_document(self, document_id, reason, principal, *, expired_at):
        self.expirations.append((document_id, reason, principal, expired_at))
        return ExpireDocumentResult(
            lifecycle_event_id=uuid4(),
            document_id=document_id,
            document_version_id=uuid4(),
            status="expired",
            reason=reason,
            expired_at=expired_at,
        )

    def queue_reindex(
        self,
        document_id,
        request,
        principal,
        *,
        idempotency_key,
        requested_at,
    ):
        self.index_requests.append(
            (document_id, request, principal, idempotency_key, requested_at)
        )
        return IndexJobResult(
            index_job_id=uuid4(),
            document_id=document_id,
            document_version_id=uuid4(),
            idempotency_key=idempotency_key,
            model_key=request.model_key,
            status="queued",
            attempt_count=0,
            max_attempts=request.max_attempts,
            scheduled_at=requested_at,
        )


def publisher() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        id=uuid4(),
        roles=frozenset({"knowledge_publisher"}),
        request_id="lifecycle-request",
    )


def test_publisher_can_expire_and_queue_reindex() -> None:
    repository = MemoryLifecycleRepository()
    service = KnowledgeLifecycleService(repository)
    principal = publisher()
    document_id = uuid4()
    now = datetime(2026, 8, 1, tzinfo=UTC)

    expiration = service.expire(
        principal,
        document_id,
        ExpireDocumentRequest(reason="Official guidance was withdrawn."),
        expired_at=now,
    )
    index_job = service.reindex(
        principal,
        document_id,
        ReindexDocumentRequest(
            model_key="configured-embedding-role",
        ),
        idempotency_key="document-v1-model-a",
        requested_at=now,
    )

    assert expiration.status == "expired"
    assert index_job.status == "queued"
    assert repository.expirations[0][2].request_id == "lifecycle-request"
    assert repository.index_requests[0][1].max_attempts == 3
    assert repository.index_requests[0][3] == "document-v1-model-a"


def test_non_publisher_cannot_change_document_lifecycle() -> None:
    repository = MemoryLifecycleRepository()
    service = KnowledgeLifecycleService(repository)
    reviewer = replace(publisher(), roles=frozenset({"content_reviewer"}))

    with pytest.raises(KnowledgeLifecycleError, match="publisher"):
        service.expire(
            reviewer,
            uuid4(),
            ExpireDocumentRequest(reason="Not authorized."),
            expired_at=datetime(2026, 8, 1, tzinfo=UTC),
        )

    assert repository.expirations == []


def test_lifecycle_timestamp_must_be_timezone_aware() -> None:
    service = KnowledgeLifecycleService(MemoryLifecycleRepository())

    with pytest.raises(KnowledgeLifecycleError, match="timezone-aware"):
        service.reindex(
            publisher(),
            uuid4(),
            ReindexDocumentRequest(model_key="model"),
            idempotency_key="job",
            requested_at=datetime(2026, 8, 1),
        )


def test_retrieval_eligibility_requires_current_published_effective_version() -> None:
    version_id = uuid4()
    today = date(2026, 8, 1)
    version = SimpleNamespace(
        id=version_id,
        published_at=datetime(2026, 7, 31, tzinfo=UTC),
        effective_from=date(2026, 7, 31),
        effective_until=None,
    )
    document = SimpleNamespace(status="published", current_version_id=version_id)

    assert SqlAlchemyKnowledgeLifecycleRepository._is_retrievable(
        document,
        version,
        on_date=today,
    )

    document.status = "expired"
    assert not SqlAlchemyKnowledgeLifecycleRepository._is_retrievable(
        document,
        version,
        on_date=today,
    )
    document.status = "published"
    version.effective_until = date(2026, 7, 31)
    assert not SqlAlchemyKnowledgeLifecycleRepository._is_retrievable(
        document,
        version,
        on_date=today,
    )
