from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.audit import AuditEvent
from app.database.models.knowledge import (
    Document,
    DocumentLifecycleEvent,
    DocumentVersion,
    IndexJob,
)
from app.identity.service import AuthenticatedPrincipal
from app.knowledge.lifecycle import (
    ExpireDocumentResult,
    IndexJobResult,
    KnowledgeLifecycleError,
    ReindexDocumentRequest,
)


class SqlAlchemyKnowledgeLifecycleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def expire_document(
        self,
        document_id,
        reason,
        principal: AuthenticatedPrincipal,
        *,
        expired_at,
    ) -> ExpireDocumentResult:
        document = self.session.scalar(
            select(Document).where(Document.id == document_id).with_for_update()
        )
        if document is None:
            raise KnowledgeLifecycleError("document_not_found", "knowledge document not found")
        if document.current_version_id is None:
            raise KnowledgeLifecycleError(
                "document_not_published",
                "knowledge document has no current published version",
            )

        existing = self.session.scalar(
            select(DocumentLifecycleEvent).where(
                DocumentLifecycleEvent.document_version_id == document.current_version_id,
                DocumentLifecycleEvent.event_type == "expired",
            )
        )
        if existing is not None:
            return self._expiration_result(existing)
        if document.status != "published":
            raise KnowledgeLifecycleError(
                "document_not_published",
                "only a published knowledge document can be expired",
            )

        event = DocumentLifecycleEvent(
            id=uuid4(),
            document_id=document.id,
            document_version_id=document.current_version_id,
            event_type="expired",
            reason=reason,
            actor_principal_id=principal.id,
            occurred_at=expired_at,
        )
        document.status = "expired"
        self.session.add(event)
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=principal.id,
                action="knowledge.expired",
                entity_type="knowledge.document_version",
                entity_id=document.current_version_id,
                request_id=principal.request_id,
                payload={"document_id": str(document.id), "reason": reason},
                occurred_at=expired_at,
            )
        )
        self.session.flush()
        return self._expiration_result(event)

    def queue_reindex(
        self,
        document_id,
        request: ReindexDocumentRequest,
        principal: AuthenticatedPrincipal,
        *,
        idempotency_key,
        requested_at,
    ) -> IndexJobResult:
        document = self.session.scalar(
            select(Document).where(Document.id == document_id).with_for_update()
        )
        if document is None:
            raise KnowledgeLifecycleError("document_not_found", "knowledge document not found")
        if document.current_version_id is None:
            raise KnowledgeLifecycleError(
                "document_not_retrievable",
                "knowledge document has no current version to index",
            )
        version = self.session.get(DocumentVersion, document.current_version_id)
        if version is None:
            raise RuntimeError("current knowledge document version is missing")
        if not self._is_retrievable(document, version, on_date=requested_at.date()):
            raise KnowledgeLifecycleError(
                "document_not_retrievable",
                "only a current, published, effective knowledge document can be indexed",
            )

        existing = self.session.scalar(
            select(IndexJob).where(
                IndexJob.document_version_id == version.id,
                IndexJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.model_key != request.model_key:
                raise KnowledgeLifecycleError(
                    "index_job_conflict",
                    "idempotency key is already linked to a different model",
                )
            return self._index_result(document.id, existing)

        job = IndexJob(
            id=uuid4(),
            document_version_id=version.id,
            requested_by_principal_id=principal.id,
            idempotency_key=idempotency_key,
            model_key=request.model_key,
            status="queued",
            max_attempts=request.max_attempts,
            scheduled_at=requested_at,
        )
        self.session.add(job)
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=principal.id,
                action="knowledge.reindex_requested",
                entity_type="knowledge.document_version",
                entity_id=version.id,
                request_id=principal.request_id,
                payload={
                    "document_id": str(document.id),
                    "index_job_id": str(job.id),
                    "idempotency_key": idempotency_key,
                    "model_key": request.model_key,
                },
                occurred_at=requested_at,
            )
        )
        self.session.flush()
        return self._index_result(document.id, job)

    @staticmethod
    def _is_retrievable(document, version, *, on_date) -> bool:
        return (
            document.status == "published"
            and document.current_version_id == version.id
            and version.published_at is not None
            and version.effective_from <= on_date
            and (version.effective_until is None or version.effective_until >= on_date)
        )

    @staticmethod
    def _expiration_result(event) -> ExpireDocumentResult:
        return ExpireDocumentResult(
            lifecycle_event_id=event.id,
            document_id=event.document_id,
            document_version_id=event.document_version_id,
            status="expired",
            reason=event.reason,
            expired_at=event.occurred_at,
        )

    @staticmethod
    def _index_result(document_id, job) -> IndexJobResult:
        return IndexJobResult(
            index_job_id=job.id,
            document_id=document_id,
            document_version_id=job.document_version_id,
            idempotency_key=job.idempotency_key,
            model_key=job.model_key,
            status=job.status,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            scheduled_at=job.scheduled_at,
        )
