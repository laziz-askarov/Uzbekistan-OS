from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.dependencies import (
    get_admin_ingestion_query_service,
    get_admin_ingestion_service,
    get_admin_ingestion_upload_service,
    get_identity_service,
    get_identity_verifier,
    get_knowledge_lifecycle_service,
    get_publication_service,
    get_review_service,
)
from app.identity.authentication import AuthenticationError
from app.identity.service import AuthenticatedPrincipal, VerifiedIdentity
from app.ingestion.admin import (
    AdminSourceRecord,
    IngestionJobRecord,
    ManualUploadResult,
)
from app.ingestion.artifacts import ExtractedSection, ExtractionArtifact
from app.ingestion.review import (
    ArtifactComparison,
    ReviewDecision,
    ReviewerContext,
    ReviewError,
    ReviewQueueRecord,
    ReviewRecord,
    ReviewStatus,
    SectionChange,
    SectionChangeType,
)
from app.knowledge.lifecycle import ExpireDocumentResult, IndexJobResult
from app.knowledge.publication import PublicationResult
from app.main import create_app
from app.routes.admin import router as admin_router

SOURCE_ID = UUID("00000000-0000-0000-0000-000000002001")


class StubIdentityVerifier:
    def verify(self, bearer_token: str) -> VerifiedIdentity:
        if bearer_token != "trusted-token":
            raise AuthenticationError("invalid_bearer_token", "the Bearer token is invalid")
        return VerifiedIdentity(provider="test-provider", subject="verified-subject")


class StubIdentityService:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal
        self.identities: list[VerifiedIdentity] = []

    def resolve(self, identity: VerifiedIdentity) -> AuthenticatedPrincipal:
        self.identities.append(identity)
        return AuthenticatedPrincipal(
            id=self.principal.id,
            roles=self.principal.roles,
            request_id=identity.request_id,
        )


class StubReviewService:
    def __init__(self, record: ReviewRecord) -> None:
        self.record = record
        self.contexts: list[ReviewerContext] = []
        self.fail_decision = False

    def list_queue(
        self,
        context: ReviewerContext,
        *,
        status: ReviewStatus | None,
        limit: int,
    ) -> tuple[ReviewQueueRecord, ...]:
        self.contexts.append(context)
        assert status in {None, self.record.status}
        assert 1 <= limit <= 100
        return (
            ReviewQueueRecord(
                review=self.record,
                source_id=SOURCE_ID,
                source_title="Official entry guidance",
                source_url="https://government.example/entry",
                fetched_at=datetime(2026, 8, 1, tzinfo=UTC),
                section_count=1,
            ),
        )

    def artifact(self, context: ReviewerContext, artifact_id: UUID) -> ExtractionArtifact:
        assert artifact_id == self.record.extraction_artifact_id
        self.contexts.append(context)
        return ExtractionArtifact(
            source_id=SOURCE_ID,
            snapshot_id=uuid4(),
            adapter_key="generic-html",
            media_type="text/html",
            raw_sha256="0" * 64,
            normalized_sha256="1" * 64,
            extracted_at=datetime(2026, 8, 1, tzinfo=UTC),
            sections=[
                ExtractedSection(
                    id="overview",
                    heading="Overview",
                    body="Verified entry guidance.",
                )
            ],
        )

    def claim(self, context: ReviewerContext, review_item_id: UUID) -> ReviewRecord:
        assert review_item_id == self.record.id
        self.contexts.append(context)
        self.record = ReviewRecord(
            id=self.record.id,
            extraction_artifact_id=self.record.extraction_artifact_id,
            status=ReviewStatus.IN_REVIEW,
            priority=self.record.priority,
            assigned_user_id=context.actor_user_id,
            decision_reason=None,
            decided_at=None,
            updated_at=datetime(2026, 8, 1, 1, tzinfo=UTC),
        )
        return self.record

    def decide(
        self,
        context: ReviewerContext,
        review_item_id: UUID,
        decision: ReviewDecision,
        *,
        reason: str,
    ) -> ReviewRecord:
        assert review_item_id == self.record.id
        if self.fail_decision:
            raise ReviewError("invalid_review_transition", "review cannot be decided")
        self.contexts.append(context)
        target = (
            ReviewStatus.APPROVED if decision is ReviewDecision.APPROVE else ReviewStatus.REJECTED
        )
        self.record = ReviewRecord(
            id=self.record.id,
            extraction_artifact_id=self.record.extraction_artifact_id,
            status=target,
            priority=self.record.priority,
            assigned_user_id=context.actor_user_id,
            decision_reason=reason,
            decided_at=datetime(2026, 8, 1, 2, tzinfo=UTC),
            updated_at=datetime(2026, 8, 1, 2, tzinfo=UTC),
        )
        return self.record

    def compare(self, context: ReviewerContext, artifact_id: UUID) -> ArtifactComparison:
        assert artifact_id == self.record.extraction_artifact_id
        self.contexts.append(context)
        return ArtifactComparison(
            current_artifact_id=artifact_id,
            previous_artifact_id=uuid4(),
            changes=(
                SectionChange(
                    section_id="overview",
                    change_type=SectionChangeType.MODIFIED,
                    previous_heading="Old overview",
                    current_heading="Overview",
                ),
            ),
        )


class StubPublicationService:
    def __init__(self) -> None:
        self.principals: list[AuthenticatedPrincipal] = []

    def publish(self, principal, candidate, *, published_at) -> PublicationResult:
        self.principals.append(principal)
        return PublicationResult(
            publication_id=uuid4(),
            document_id=uuid4(),
            document_version_id=uuid4(),
            candidate_sha256=candidate.sha256,
            published_at=published_at,
        )


class StubKnowledgeLifecycleService:
    def __init__(self) -> None:
        self.principals: list[AuthenticatedPrincipal] = []

    def expire(self, principal, document_id, request, *, expired_at):
        self.principals.append(principal)
        return ExpireDocumentResult(
            lifecycle_event_id=uuid4(),
            document_id=document_id,
            document_version_id=uuid4(),
            status="expired",
            reason=request.reason,
            expired_at=expired_at,
        )

    def reindex(self, principal, document_id, request, *, idempotency_key, requested_at):
        self.principals.append(principal)
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


class StubAdminIngestionService:
    def __init__(self) -> None:
        self.source_id = SOURCE_ID
        self.job = IngestionJobRecord(
            id=uuid4(),
            source_id=self.source_id,
            source_title="Official entry guidance",
            idempotency_key="crawler-http-test",
            status="queued",
            attempt_count=0,
            max_attempts=3,
            scheduled_at=datetime(2026, 8, 1, tzinfo=UTC),
            started_at=None,
            completed_at=None,
        )
        self.queued_keys: list[str] = []
        self.uploaded_files: list[str] = []

    def list_sources(self, principal):
        del principal
        return (
            AdminSourceRecord(
                id=self.source_id,
                slug="official-entry-guidance",
                organization="Government Example",
                title="Official entry guidance",
                url="https://government.example/entry",
                source_type="html",
                domains=["immigration"],
                languages=["en"],
                crawl_policy="allowed",
                adapter_key="generic-html",
                trust_tier=1,
                registry_status="approved",
                active=True,
                production_eligible=True,
                automatic_fetch_eligible=True,
                manual_upload_eligible=True,
                schedule_interval_minutes=60,
                last_verified_at=None,
                latest_job_status="queued",
            ),
        )

    def list_jobs(self, principal, *, limit):
        del principal
        assert limit == 25
        return (self.job,)

    def list_topics(self, principal):
        del principal
        return ("Entry requirements",)

    def queue_crawl(self, principal, payload, *, idempotency_key, enqueued_at):
        del principal, enqueued_at
        assert payload.source_id == self.source_id
        self.queued_keys.append(idempotency_key)
        return self.job.model_copy(update={"idempotency_key": idempotency_key})

    def upload(
        self,
        principal,
        source_id,
        payload,
        *,
        idempotency_key,
        uploaded_at,
    ):
        del principal, idempotency_key, uploaded_at
        assert source_id == self.source_id
        self.uploaded_files.append(payload.filename)
        return ManualUploadResult(
            source_id=source_id,
            filename=payload.filename,
            topic=payload.topic,
            status="changed",
            snapshot_id=uuid4(),
            extraction_artifact_id=uuid4(),
            review_item_id=uuid4(),
        )


def pending_record() -> ReviewRecord:
    return ReviewRecord(
        id=uuid4(),
        extraction_artifact_id=uuid4(),
        status=ReviewStatus.PENDING,
        priority=50,
        assigned_user_id=None,
        decision_reason=None,
        decided_at=None,
        updated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )


def publication_payload(review_item_id: UUID) -> dict[str, object]:
    return {
        "review_item_id": str(review_item_id),
        "slug": "reviewed-entry-guidance",
        "domain": "immigration",
        "language": "en",
        "version": {"major": 1, "minor": 0, "revision": 0},
        "title": "Reviewed entry guidance",
        "summary": "Reviewed summary.",
        "audiences": ["international-visitor"],
        "keywords": ["entry"],
        "sections": [
            {
                "id": "overview",
                "heading": "Overview",
                "body": "Entry guidance from the reviewed source.",
                "citations": [
                    {
                        "source_id": str(SOURCE_ID),
                        "locator": "Overview section",
                        "quote": "Entry guidance",
                    }
                ],
            }
        ],
        "effective_from": "2026-08-01",
        "effective_until": "2026-08-31",
        "translation_of_id": None,
    }


def configured_client():
    application = create_app()
    principal = AuthenticatedPrincipal(
        id=uuid4(),
        roles=frozenset({"content_reviewer", "knowledge_publisher"}),
    )
    identity_service = StubIdentityService(principal)
    review_service = StubReviewService(pending_record())
    publication_service = StubPublicationService()
    lifecycle_service = StubKnowledgeLifecycleService()
    application.dependency_overrides[get_identity_verifier] = StubIdentityVerifier
    application.dependency_overrides[get_identity_service] = lambda: identity_service
    application.dependency_overrides[get_review_service] = lambda: review_service
    application.dependency_overrides[get_publication_service] = lambda: publication_service
    application.dependency_overrides[get_knowledge_lifecycle_service] = lambda: lifecycle_service
    return (
        TestClient(application),
        identity_service,
        review_service,
        publication_service,
        lifecycle_service,
    )


def auth_headers() -> dict[str, str]:
    return {
        "authorization": "Bearer trusted-token",
        "x-request-id": "admin-request",
    }


def test_admin_routes_require_a_bearer_token() -> None:
    application = create_app()

    with TestClient(application) as client:
        response = client.get("/api/v1/auth/me", headers={"x-request-id": "missing-auth"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "missing_bearer_token",
            "message": "a Bearer access token is required",
            "details": {},
        },
        "meta": {"request_id": "missing-auth"},
    }


def test_manual_upload_route_uses_synchronous_service_without_redis_queue() -> None:
    route = next(
        item
        for item in admin_router.routes
        if getattr(item, "path", None) == "/admin/sources/{source_id}/uploads"
    )
    dependency_calls = {dependency.call for dependency in route.dependant.dependencies}

    assert get_admin_ingestion_upload_service in dependency_calls
    assert get_admin_ingestion_service not in dependency_calls


def test_default_token_verifier_fails_closed() -> None:
    application = create_app()

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={"authorization": "Bearer unverified", "x-request-id": "fail-closed"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "authentication_unconfigured"


def test_invalid_token_is_rejected_before_identity_resolution() -> None:
    client, identity_service, _, _, _ = configured_client()

    response = client.get(
        "/api/v1/auth/me",
        headers={"authorization": "Bearer invalid", "x-request-id": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "invalid_bearer_token"
    assert identity_service.identities == []


def test_verified_identity_resolves_to_internal_principal() -> None:
    client, identity_service, _, _, _ = configured_client()

    response = client.get("/api/v1/auth/me", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["data"]["roles"] == ["content_reviewer", "knowledge_publisher"]
    assert identity_service.identities == [
        VerifiedIdentity(
            provider="test-provider",
            subject="verified-subject",
            request_id="admin-request",
        )
    ]


def test_reviewer_can_claim_decide_and_compare_through_http() -> None:
    client, _, review_service, _, _ = configured_client()
    review_item_id = review_service.record.id
    artifact_id = review_service.record.extraction_artifact_id

    claim = client.post(
        f"/api/v1/admin/reviews/{review_item_id}/claim",
        headers=auth_headers(),
    )
    decision = client.post(
        f"/api/v1/admin/reviews/{review_item_id}/decision",
        headers=auth_headers(),
        json={"decision": "approve", "reason": "Evidence verified."},
    )
    comparison = client.get(
        f"/api/v1/admin/artifacts/{artifact_id}/comparison",
        headers=auth_headers(),
    )

    assert claim.status_code == 200
    assert claim.json()["data"]["status"] == "in_review"
    assert decision.status_code == 200
    assert decision.json()["data"]["status"] == "approved"
    assert comparison.status_code == 200
    assert comparison.json()["data"]["changed"] is True
    assert comparison.json()["data"]["changes"][0]["change_type"] == "modified"
    assert all(context.request_id == "admin-request" for context in review_service.contexts)


def test_reviewer_can_list_queue_and_read_verified_artifact_through_http() -> None:
    client, _, review_service, _, _ = configured_client()

    queue = client.get(
        "/api/v1/admin/reviews?status=pending&limit=25",
        headers=auth_headers(),
    )
    detail = client.get(
        f"/api/v1/admin/artifacts/{review_service.record.extraction_artifact_id}",
        headers=auth_headers(),
    )

    assert queue.status_code == 200
    assert queue.json()["data"][0]["source_title"] == "Official entry guidance"
    assert queue.json()["data"][0]["review"]["status"] == "pending"
    assert detail.status_code == 200
    assert detail.json()["data"]["sections"][0]["body"] == "Verified entry guidance."
    assert all(context.request_id == "admin-request" for context in review_service.contexts)


def test_review_domain_errors_use_the_standard_error_envelope() -> None:
    client, _, review_service, _, _ = configured_client()
    review_service.fail_decision = True

    response = client.post(
        f"/api/v1/admin/reviews/{review_service.record.id}/decision",
        headers=auth_headers(),
        json={"decision": "approve", "reason": "Evidence verified."},
    )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "invalid_review_transition",
        "message": "review cannot be decided",
        "details": {},
    }


def test_request_validation_errors_use_the_standard_error_envelope() -> None:
    client, _, review_service, _, _ = configured_client()

    response = client.post(
        f"/api/v1/admin/reviews/{review_service.record.id}/decision",
        headers=auth_headers(),
        json={"decision": "approve", "reason": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert response.json()["error"]["details"]["issues"]
    assert response.json()["meta"] == {"request_id": "admin-request"}


def test_publisher_can_publish_candidate_through_http() -> None:
    client, _, review_service, publication_service, _ = configured_client()

    response = client.post(
        "/api/v1/admin/publications",
        headers=auth_headers(),
        json=publication_payload(review_service.record.id),
    )

    assert response.status_code == 200
    assert response.json()["data"]["candidate_sha256"]
    assert response.json()["meta"] == {"request_id": "admin-request"}
    assert publication_service.principals[0].request_id == "admin-request"


def test_publisher_can_expire_and_reindex_through_http() -> None:
    client, _, _, _, lifecycle_service = configured_client()
    document_id = uuid4()

    expiration = client.post(
        f"/api/v1/admin/documents/{document_id}/expire",
        headers=auth_headers(),
        json={"reason": "Official guidance was withdrawn."},
    )
    reindex = client.post(
        f"/api/v1/admin/documents/{document_id}/reindex",
        headers={**auth_headers(), "Idempotency-Key": "document-v1-configured-role"},
        json={
            "model_key": "configured-embedding-role",
            "max_attempts": 3,
        },
    )

    assert expiration.status_code == 200
    assert expiration.json()["data"]["status"] == "expired"
    assert reindex.status_code == 200
    assert reindex.json()["data"]["status"] == "queued"
    assert all(
        principal.request_id == "admin-request" for principal in lifecycle_service.principals
    )


def test_admin_can_list_sources_queue_crawl_and_upload_through_http() -> None:
    application = create_app()
    identity_service = StubIdentityService(
        AuthenticatedPrincipal(id=uuid4(), roles=frozenset({"admin"}))
    )
    admin_service = StubAdminIngestionService()
    application.dependency_overrides[get_identity_verifier] = StubIdentityVerifier
    application.dependency_overrides[get_identity_service] = lambda: identity_service
    application.dependency_overrides[get_admin_ingestion_service] = lambda: admin_service
    application.dependency_overrides[get_admin_ingestion_upload_service] = (
        lambda: admin_service
    )
    application.dependency_overrides[get_admin_ingestion_query_service] = lambda: admin_service
    client = TestClient(application)

    sources = client.get("/api/v1/admin/sources", headers=auth_headers())
    jobs = client.get("/api/v1/admin/ingestion/jobs?limit=25", headers=auth_headers())
    topics = client.get("/api/v1/admin/ingestion/topics", headers=auth_headers())
    crawl = client.post(
        "/api/v1/admin/ingestion/jobs",
        headers={**auth_headers(), "Idempotency-Key": "crawler-http-test"},
        json={"source_id": str(SOURCE_ID), "max_attempts": 3},
    )
    upload = client.post(
        f"/api/v1/admin/sources/{SOURCE_ID}/uploads",
        headers={**auth_headers(), "Idempotency-Key": "upload-http-test"},
        json={
            "filename": "official.html",
            "content_type": "text/html",
            "content_base64": "PGgxPk9mZmljaWFsPC9oMT4=",
            "topic": "Entry requirements",
        },
    )

    assert sources.status_code == 200
    assert sources.json()["data"][0]["automatic_fetch_eligible"] is True
    assert jobs.status_code == 200
    assert jobs.json()["data"][0]["status"] == "queued"
    assert topics.json()["data"] == ["Entry requirements"]
    assert crawl.status_code == 202
    assert crawl.json()["data"]["idempotency_key"] == "crawler-http-test"
    assert upload.status_code == 200
    assert upload.json()["data"]["review_item_id"]
    assert upload.json()["data"]["topic"] == "Entry requirements"
    assert admin_service.queued_keys == ["crawler-http-test"]
    assert admin_service.uploaded_files == ["official.html"]
