from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.dependencies import (
    get_identity_service,
    get_identity_verifier,
    get_publication_service,
    get_review_service,
)
from app.identity.authentication import AuthenticationError
from app.identity.service import AuthenticatedPrincipal, VerifiedIdentity
from app.ingestion.review import (
    ArtifactComparison,
    ReviewDecision,
    ReviewerContext,
    ReviewError,
    ReviewRecord,
    ReviewStatus,
    SectionChange,
    SectionChangeType,
)
from app.knowledge.publication import PublicationResult
from app.main import create_app

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
            ReviewStatus.APPROVED
            if decision is ReviewDecision.APPROVE
            else ReviewStatus.REJECTED
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
        "effective_until": None,
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
    application.dependency_overrides[get_identity_verifier] = StubIdentityVerifier
    application.dependency_overrides[get_identity_service] = lambda: identity_service
    application.dependency_overrides[get_review_service] = lambda: review_service
    application.dependency_overrides[get_publication_service] = lambda: publication_service
    return (
        TestClient(application),
        identity_service,
        review_service,
        publication_service,
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
    client, identity_service, _, _ = configured_client()

    response = client.get(
        "/api/v1/auth/me",
        headers={"authorization": "Bearer invalid", "x-request-id": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "invalid_bearer_token"
    assert identity_service.identities == []


def test_verified_identity_resolves_to_internal_principal() -> None:
    client, identity_service, _, _ = configured_client()

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
    client, _, review_service, _ = configured_client()
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


def test_review_domain_errors_use_the_standard_error_envelope() -> None:
    client, _, review_service, _ = configured_client()
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
    client, _, review_service, _ = configured_client()

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
    client, _, review_service, publication_service = configured_client()

    response = client.post(
        "/api/v1/admin/publications",
        headers=auth_headers(),
        json=publication_payload(review_service.record.id),
    )

    assert response.status_code == 200
    assert response.json()["data"]["candidate_sha256"]
    assert response.json()["meta"] == {"request_id": "admin-request"}
    assert publication_service.principals[0].request_id == "admin-request"
