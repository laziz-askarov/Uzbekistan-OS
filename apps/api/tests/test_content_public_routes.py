from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.content.editorial import (
    ContentType,
    EditorialAuthorRecord,
    EditorialError,
    PublishedEditorialPostRecord,
    PublishedEditorialSourceRecord,
    PublishedEditorialSummaryRecord,
    PublishedEditorialTranslationRecord,
)
from app.dependencies import get_editorial_service
from app.main import create_app


class StubPublicEditorialService:
    def __init__(self) -> None:
        self.published_at = datetime(2026, 8, 31, 15, tzinfo=UTC)
        self.author = EditorialAuthorRecord(
            id=uuid4(),
            principal_id=None,
            slug="uzbekistan-os-editorial",
            name="Uzbekistan OS Editorial",
            bio="Reviewed guidance about Uzbekistan.",
            avatar_url=None,
            profile_url="https://www.uzbekistanos.com/blog",
            is_active=True,
        )
        self.source = PublishedEditorialSourceRecord(
            source_id=uuid4(),
            title="Official tourism portal",
            organization="Uzbekistan Travel",
            url="https://uzbekistan.travel/",
            locator="Visitor guidance",
        )

    def list_published_posts(self, *, domain_slug, language_code, limit):
        assert domain_slug == "tourism"
        assert language_code == "en"
        assert limit == 12
        return (
            PublishedEditorialSummaryRecord(
                id=uuid4(),
                slug="best-time-to-visit-uzbekistan",
                content_type=ContentType.ARTICLE,
                domain_slug="tourism",
                language_code="en",
                title="Best time to visit Uzbekistan",
                summary="A seasonal guide to visiting Uzbekistan.",
                hero_image_url=None,
                hero_image_alt=None,
                author_name=self.author.name,
                author_slug=self.author.slug,
                published_at=self.published_at,
                updated_at=self.published_at,
            ),
        )

    def get_published_post(self, slug):
        if slug != "best-time-to-visit-uzbekistan":
            raise EditorialError(
                "editorial_publication_not_found",
                "published editorial post does not exist",
            )
        return PublishedEditorialPostRecord(
            id=uuid4(),
            version_id=uuid4(),
            version_number=1,
            slug=slug,
            content_type=ContentType.ARTICLE,
            domain_slug="tourism",
            language_code="en",
            title="Best time to visit Uzbekistan",
            summary="A seasonal guide to visiting Uzbekistan.",
            body_markdown="# Seasons\n\nSpring and autumn are popular.",
            structured_content={"faq": []},
            seo_title="Best Time to Visit Uzbekistan",
            seo_description="Plan an Uzbekistan trip by season.",
            canonical_url=None,
            hero_image_url=None,
            hero_image_alt=None,
            author=self.author,
            sources=(self.source,),
            translations=(
                PublishedEditorialTranslationRecord(
                    language_code="en",
                    slug=slug,
                    title="Best time to visit Uzbekistan",
                ),
            ),
            published_at=self.published_at,
            updated_at=self.published_at,
            review_due_at=datetime(2027, 2, 27, 15, tzinfo=UTC),
        )


def setup_client() -> TestClient:
    app = create_app()
    service = StubPublicEditorialService()
    app.dependency_overrides[get_editorial_service] = lambda: service
    return TestClient(app)


def test_public_posts_are_readable_without_customer_authentication() -> None:
    response = setup_client().get(
        "/api/v1/content/posts?domain=tourism&language=en&limit=12",
        headers={"X-Request-ID": "public-blog-list"},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["slug"] == "best-time-to-visit-uzbekistan"
    assert response.json()["meta"]["request_id"] == "public-blog-list"


def test_public_post_includes_author_source_lineage_and_machine_readable_content() -> None:
    response = setup_client().get(
        "/api/v1/content/posts/best-time-to-visit-uzbekistan",
        headers={"X-Request-ID": "public-blog-detail"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version_number"] == 1
    assert data["body_markdown"].startswith("# Seasons")
    assert data["author"]["name"] == "Uzbekistan OS Editorial"
    assert data["sources"][0]["organization"] == "Uzbekistan Travel"
    assert data["translations"][0]["language_code"] == "en"


def test_unpublished_or_unknown_post_is_not_exposed_by_public_route() -> None:
    response = setup_client().get("/api/v1/content/posts/private-draft")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "editorial_publication_not_found"
