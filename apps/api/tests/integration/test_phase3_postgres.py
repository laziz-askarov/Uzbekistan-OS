import os
from datetime import UTC, date, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.database.models.geography import Language
from app.database.models.identity import Principal
from app.database.models.knowledge import Chunk, Document, DocumentVersion, Domain
from app.identity.service import AuthenticatedPrincipal
from app.knowledge.lifecycle import KnowledgeLifecycleError, ReindexDocumentRequest
from app.knowledge.lifecycle_repositories import SqlAlchemyKnowledgeLifecycleRepository

DATABASE_URL = os.getenv("PHASE3_INTEGRATION_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="PHASE3_INTEGRATION_DATABASE_URL is required for infrastructure tests",
)


def test_expired_document_is_removed_from_retrievable_view() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        domain = session.scalar(select(Domain).where(Domain.slug == "tourism"))
        language = session.scalar(select(Language).where(Language.code == "en"))
        assert domain is not None
        assert language is not None

        principal = Principal(
            id=uuid4(),
            provider="phase3-integration",
            subject=str(uuid4()),
            status="active",
        )
        document = Document(
            id=uuid4(),
            slug=f"phase3-retrieval-{uuid4()}",
            domain_id=domain.id,
            canonical_language_id=language.id,
            status="draft",
        )
        session.add_all([principal, document])
        session.flush()

        content = "Infrastructure-backed eligibility evidence."
        version = DocumentVersion(
            id=uuid4(),
            document_id=document.id,
            language_id=language.id,
            version_major=1,
            version_minor=0,
            version_revision=0,
            title="Phase 3 eligibility proof",
            summary="Temporary integration fixture.",
            content={"fixture": True},
            checksum_sha256=sha256(content.encode()).hexdigest(),
            effective_from=date(2026, 8, 1),
            reviewed_at=datetime(2026, 8, 1, tzinfo=UTC),
            published_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        session.add(version)
        session.flush()
        chunk = Chunk(
            id=uuid4(),
            document_version_id=version.id,
            section_id="eligibility",
            ordinal=0,
            content=content,
            content_hash=sha256(content.encode()).hexdigest(),
            token_count=3,
            attributes={},
        )
        session.add(chunk)
        session.flush()
        document.current_version_id = version.id
        document.status = "published"
        session.flush()

        before = session.scalar(
            text(
                "SELECT count(*) FROM knowledge.retrievable_chunks "
                "WHERE document_id = :document_id"
            ),
            {"document_id": document.id},
        )
        assert before == 1

        repository = SqlAlchemyKnowledgeLifecycleRepository(session)
        actor = AuthenticatedPrincipal(
            id=principal.id,
            roles=frozenset({"knowledge_publisher"}),
            request_id="phase3-integration",
        )
        index_request = ReindexDocumentRequest(
            model_key="integration-embedding-role",
            max_attempts=3,
        )
        first_job = repository.queue_reindex(
            document.id,
            index_request,
            actor,
            idempotency_key="phase3-integration-index",
            requested_at=datetime(2026, 8, 1, 0, 30, tzinfo=UTC),
        )
        replayed_job = repository.queue_reindex(
            document.id,
            index_request,
            actor,
            idempotency_key="phase3-integration-index",
            requested_at=datetime(2026, 8, 1, 0, 31, tzinfo=UTC),
        )
        assert replayed_job.index_job_id == first_job.index_job_id

        repository.expire_document(
            document.id,
            "Integration proof of fail-closed expiration.",
            actor,
            expired_at=datetime(2026, 8, 1, 1, tzinfo=UTC),
        )

        after = session.scalar(
            text(
                "SELECT count(*) FROM knowledge.retrievable_chunks "
                "WHERE document_id = :document_id"
            ),
            {"document_id": document.id},
        )
        assert after == 0

        with pytest.raises(KnowledgeLifecycleError, match="published, effective"):
            repository.queue_reindex(
                document.id,
                index_request,
                actor,
                idempotency_key="phase3-integration-after-expiry",
                requested_at=datetime(2026, 8, 1, 1, 1, tzinfo=UTC),
            )
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()
