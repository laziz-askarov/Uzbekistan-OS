from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.content.editorial import (
    ContentType,
    EditorialAuthorRecord,
    EditorialDecision,
    EditorialPostSummaryRecord,
    EditorialRevisionDetailRecord,
    EditorialRevisionRecord,
    EditorialSourceReference,
    EditorialStatus,
    ReviewedKnowledgeSourceRecord,
)
from app.dependencies import (
    get_editorial_service,
    get_identity_service,
    get_identity_verifier,
)
from app.identity.service import AuthenticatedPrincipal, VerifiedIdentity
from app.main import create_app


class StubIdentityVerifier:
    def verify(self, bearer_token: str) -> VerifiedIdentity:
        assert bearer_token == "trusted-token"
        return VerifiedIdentity(provider="test", subject="editorial-admin")


class StubIdentityService:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    def resolve(self, identity: VerifiedIdentity) -> AuthenticatedPrincipal:
        return replace(self.principal, request_id=identity.request_id)


class StubEditorialService:
    def __init__(self, principal_id: UUID) -> None:
        self.author = EditorialAuthorRecord(
            id=uuid4(),
            principal_id=principal_id,
            slug="laziz-askarov",
            name="Laziz Askarov",
            bio="Uzbekistan OS editor.",
            avatar_url=None,
            profile_url=None,
            is_active=True,
        )
        self.post_id = uuid4()
        self.translation_group_id = uuid4()
        self.revision = EditorialRevisionRecord(
            id=uuid4(),
            post_id=self.post_id,
            version_number=1,
            content_type=ContentType.GUIDE,
            status=EditorialStatus.DRAFT,
            checksum_sha256="a" * 64,
            created_by_principal_id=principal_id,
            updated_at=datetime(2026, 8, 31, 12, tzinfo=UTC),
        )
        self.reviewed_source = ReviewedKnowledgeSourceRecord(
            source_id=uuid4(),
            document_id=uuid4(),
            document_version_id=uuid4(),
            document_slug="uzbekistan-entry-requirements",
            document_title="Uzbekistan entry requirements",
            document_summary="Current reviewed entry requirements.",
            domain_slug="immigration",
            language_code="en",
            version_label="1.2.0",
            source_title="Official entry portal",
            organization="Ministry of Foreign Affairs",
            source_url="https://e-visa.gov.uz/",
            source_locator="Entry requirements",
            reviewed_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
            published_at=datetime(2026, 8, 31, 12, tzinfo=UTC),
            effective_until=date(2027, 2, 28),
        )

    def _detail(self) -> EditorialRevisionDetailRecord:
        return EditorialRevisionDetailRecord(
            revision=self.revision,
            slug="uzbekistan-entry-guide",
            domain_slug="immigration",
            language_code="en",
            translation_group_id=self.translation_group_id,
            title="Uzbekistan entry guide",
            summary="Reviewed visitor guidance.",
            body_markdown="# Entry guide",
            structured_content={"faq": []},
            seo_title="Uzbekistan Entry Guide",
            seo_description="Reviewed entry guidance for Uzbekistan.",
            canonical_url=None,
            hero_image_url=None,
            hero_image_alt=None,
            include_in_rag=self.revision.include_in_rag,
            author=self.author,
            sources=(EditorialSourceReference(source_id=uuid4(), locator="Entry requirements"),),
        )

    def list_authors(self, principal):
        del principal
        return (self.author,)

    def create_author(self, principal, payload, *, created_at):
        del principal, payload, created_at
        return self.author

    def list_posts(self, principal, *, status, limit):
        del principal, status, limit
        return (
            EditorialPostSummaryRecord(
                id=self.post_id,
                slug="uzbekistan-entry-guide",
                translation_group_id=self.translation_group_id,
                content_type=ContentType.GUIDE,
                domain_slug="immigration",
                language_code="en",
                status=self.revision.status,
                published_version_id=None,
                latest_revision_id=self.revision.id,
                latest_revision_number=self.revision.version_number,
                latest_revision_status=self.revision.status,
                latest_title="Uzbekistan entry guide",
                updated_at=datetime(2026, 8, 31, 12, tzinfo=UTC),
            ),
        )

    def list_reviewed_sources(self, principal, *, domain_slug, language_code, limit):
        del principal
        assert domain_slug == "immigration"
        assert language_code == "en"
        assert limit == 10
        return (self.reviewed_source,)

    def create_post(self, principal, payload, *, created_at):
        del principal, payload, created_at
        return self.revision

    def create_revision(self, principal, post_id, payload, *, created_at):
        del principal, payload, created_at
        assert post_id == self.post_id
        self.revision = replace(self.revision, id=uuid4(), version_number=2)
        return self.revision

    def get_revision(self, principal, revision_id):
        del principal
        assert revision_id == self.revision.id
        return self._detail()

    def update_draft(self, principal, revision_id, payload, *, updated_at):
        del principal, payload, updated_at
        assert revision_id == self.revision.id
        return self._detail()

    def submit(self, principal, revision_id, *, submitted_at):
        del principal
        assert revision_id == self.revision.id
        self.revision = replace(
            self.revision,
            status=EditorialStatus.IN_REVIEW,
            submitted_at=submitted_at,
        )
        return self.revision

    def decide(self, principal, revision_id, decision, *, reason, reviewed_at):
        assert principal.roles == frozenset({"admin"})
        assert revision_id == self.revision.id
        assert decision is EditorialDecision.APPROVE
        self.revision = replace(
            self.revision,
            status=EditorialStatus.APPROVED,
            reviewed_by_principal_id=principal.id,
            reviewed_at=reviewed_at,
            decision_reason=reason,
        )
        return self.revision

    def publish(self, principal, revision_id, *, published_at):
        assert revision_id == self.revision.id
        self.revision = replace(
            self.revision,
            status=EditorialStatus.PUBLISHED,
            published_by_principal_id=principal.id,
            published_at=published_at,
        )
        return self.revision


def setup_client():
    principal = AuthenticatedPrincipal(id=uuid4(), roles=frozenset({"admin"}))
    service = StubEditorialService(principal.id)
    app = create_app()
    app.dependency_overrides[get_identity_verifier] = lambda: StubIdentityVerifier()
    app.dependency_overrides[get_identity_service] = lambda: StubIdentityService(principal)
    app.dependency_overrides[get_editorial_service] = lambda: service
    return TestClient(app), service


def request_headers() -> dict[str, str]:
    return {"Authorization": "Bearer trusted-token", "X-Request-ID": "editorial-route-test"}


def revision_payload(author_id: UUID) -> dict[str, object]:
    return {
        "author_id": str(author_id),
        "title": "Uzbekistan entry guide",
        "summary": "Reviewed visitor guidance.",
        "body_markdown": "# Entry guide",
        "structured_content": {"faq": []},
        "seo_title": "Uzbekistan Entry Guide",
        "seo_description": "Reviewed entry guidance for Uzbekistan.",
        "include_in_rag": True,
        "sources": [{"source_id": str(uuid4()), "locator": "Entry requirements"}],
    }


def test_editorial_admin_routes_cover_the_complete_publication_workflow() -> None:
    client, service = setup_client()

    authors = client.get("/api/v1/admin/content/authors", headers=request_headers())
    posts = client.get("/api/v1/admin/content/posts", headers=request_headers())
    sources = client.get(
        "/api/v1/admin/content/reviewed-sources?domain=immigration&language=en&limit=10",
        headers=request_headers(),
    )
    created = client.post(
        "/api/v1/admin/content/posts",
        headers=request_headers(),
        json={
            **revision_payload(service.author.id),
            "slug": "uzbekistan-entry-guide",
            "content_type": "guide",
            "domain_slug": "immigration",
            "language_code": "en",
        },
    )
    detail = client.get(
        f"/api/v1/admin/content/revisions/{service.revision.id}", headers=request_headers()
    )
    updated = client.put(
        f"/api/v1/admin/content/revisions/{service.revision.id}",
        headers=request_headers(),
        json=revision_payload(service.author.id),
    )
    submitted = client.post(
        f"/api/v1/admin/content/revisions/{service.revision.id}/submit",
        headers=request_headers(),
    )
    decided = client.post(
        f"/api/v1/admin/content/revisions/{service.revision.id}/decision",
        headers=request_headers(),
        json={"decision": "approve", "reason": "Sources and metadata verified."},
    )
    published = client.post(
        f"/api/v1/admin/content/revisions/{service.revision.id}/publish",
        headers=request_headers(),
    )

    assert authors.status_code == 200
    assert posts.status_code == 200
    assert sources.status_code == 200
    assert sources.json()["data"][0]["version_label"] == "1.2.0"
    assert sources.json()["data"][0]["document_version_id"] == str(
        service.reviewed_source.document_version_id
    )
    assert created.status_code == 201
    assert detail.status_code == 200
    assert detail.json()["data"]["include_in_rag"] is False
    assert updated.status_code == 200
    assert submitted.json()["data"]["status"] == "in_review"
    assert decided.json()["data"]["status"] == "approved"
    assert published.json()["data"]["status"] == "published"
    assert published.json()["meta"]["request_id"] == "editorial-route-test"


def test_editorial_admin_routes_require_bearer_authentication() -> None:
    client, _ = setup_client()

    response = client.get("/api/v1/admin/content/posts")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_bearer_token"
