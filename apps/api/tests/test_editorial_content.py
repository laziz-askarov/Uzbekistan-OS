from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.content.editorial import (
    ContentType,
    EditorialDecision,
    EditorialError,
    EditorialPostDraft,
    EditorialRevisionDraft,
    EditorialRevisionRecord,
    EditorialService,
    EditorialSourceReference,
    EditorialStatus,
)
from app.identity.service import AuthenticatedPrincipal


class MemoryEditorialRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, EditorialRevisionRecord] = {}
        self.audits = []
        self.eligible_sources = True
        self.current_source_links = True

    def create_post(self, draft, principal, *, created_at):
        record = EditorialRevisionRecord(
            id=uuid4(),
            post_id=uuid4(),
            version_number=1,
            content_type=draft.content_type,
            status=EditorialStatus.DRAFT,
            checksum_sha256=draft.checksum_sha256,
            created_by_principal_id=principal.id,
            include_in_rag=draft.include_in_rag,
            updated_at=created_at,
        )
        self.records[record.id] = record
        return record

    def create_revision(self, post_id, draft, principal, *, created_at):
        record = EditorialRevisionRecord(
            id=uuid4(),
            post_id=post_id,
            version_number=2,
            content_type=ContentType.GUIDE,
            status=EditorialStatus.DRAFT,
            checksum_sha256=draft.checksum_sha256,
            created_by_principal_id=principal.id,
            include_in_rag=draft.include_in_rag,
            updated_at=created_at,
        )
        self.records[record.id] = record
        return record

    def get_for_update(self, revision_id):
        return self.records.get(revision_id)

    def sources_are_eligible(self, revision_id):
        del revision_id
        return self.eligible_sources

    def source_links_are_current(self, revision_id):
        del revision_id
        return self.current_source_links

    def save(self, record):
        self.records[record.id] = record

    def publish(self, record, principal, *, published_at):
        published = replace(
            record,
            status=EditorialStatus.PUBLISHED,
            published_by_principal_id=principal.id,
            published_at=published_at,
            updated_at=published_at,
        )
        self.records[record.id] = published
        return published

    def append_audit(self, record):
        self.audits.append(record)


def principal(role: str) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        id=uuid4(), roles=frozenset({role}), request_id="editorial-request"
    )


def post_draft(*, include_in_rag: bool = False) -> EditorialPostDraft:
    return EditorialPostDraft(
        slug="uzbekistan-entry-guide",
        content_type="guide",
        domain_slug="immigration",
        language_code="en",
        author_id=uuid4(),
        title="Uzbekistan entry guide",
        summary="Reviewed guidance for entering Uzbekistan.",
        body_markdown="# Uzbekistan entry guide\n\nCheck the current requirements.",
        seo_title="Uzbekistan Entry Guide",
        seo_description="Reviewed entry guidance for visitors to Uzbekistan.",
        include_in_rag=include_in_rag,
        sources=(
            EditorialSourceReference(
                source_id=uuid4(),
                locator="Entry requirements",
                quote="Visitors must check current entry requirements.",
            ),
        ),
    )


def test_editorial_revision_follows_separated_author_review_publish_roles() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = principal("content_author")
    reviewer = principal("content_reviewer")
    publisher = principal("knowledge_publisher")
    created_at = datetime(2026, 8, 31, 12, tzinfo=UTC)

    draft = service.create_post(author, post_draft(), created_at=created_at)
    submitted = service.submit(author, draft.id, submitted_at=created_at)
    approved = service.decide(
        reviewer,
        submitted.id,
        EditorialDecision.APPROVE,
        reason="Sources, facts, and metadata verified.",
        reviewed_at=created_at,
    )
    published = service.publish(publisher, approved.id, published_at=created_at)

    assert published.status is EditorialStatus.PUBLISHED
    assert [audit.action for audit in repository.audits] == [
        "content.post_created",
        "content.revision_submitted",
        "content.revision_approved",
        "content.revision_published",
    ]
    assert all(audit.request_id == "editorial-request" for audit in repository.audits)


def test_non_admin_author_cannot_approve_own_revision() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = replace(
        principal("content_author"), roles=frozenset({"content_author", "content_reviewer"})
    )
    draft = service.create_post(author, post_draft())
    submitted = service.submit(author, draft.id)

    with pytest.raises(EditorialError, match="cannot approve their own"):
        service.decide(
            author,
            submitted.id,
            EditorialDecision.APPROVE,
            reason="Self approval should fail.",
        )


def test_guide_cannot_submit_when_official_source_is_no_longer_eligible() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = principal("content_author")
    draft = service.create_post(author, post_draft())
    repository.eligible_sources = False

    with pytest.raises(EditorialError, match="official organization"):
        service.submit(author, draft.id)

    assert repository.records[draft.id].status is EditorialStatus.DRAFT


def test_post_cannot_submit_with_stale_reviewed_source_lineage() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = principal("content_author")
    draft = service.create_post(author, post_draft())
    repository.current_source_links = False

    with pytest.raises(EditorialError, match="current reviewed knowledge publications"):
        service.submit(author, draft.id)

    assert repository.records[draft.id].status is EditorialStatus.DRAFT


def test_customer_role_cannot_author_or_change_editorial_content() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)

    with pytest.raises(EditorialError, match="server-controlled editorial author"):
        service.create_post(principal("customer"), post_draft())

    assert repository.records == {}
    assert repository.audits == []


def test_published_post_can_receive_a_new_draft_revision() -> None:
    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = principal("content_author")
    revision = service.create_revision(
        author,
        uuid4(),
        EditorialRevisionDraft(
            author_id=uuid4(),
            title="Updated Uzbekistan entry guide",
            summary="A corrected edition of the entry guide.",
            body_markdown="# Updated guide\n\nCurrent reviewed guidance.",
            sources=(EditorialSourceReference(source_id=uuid4(), locator="Current requirements"),),
        ),
    )

    assert revision.version_number == 2
    assert revision.status is EditorialStatus.DRAFT
    assert repository.audits[-1].action == "content.revision_created"


def test_guide_draft_requires_domain_and_source_at_validation_boundary() -> None:
    payload = post_draft().model_dump(mode="json")
    payload["sources"] = []

    with pytest.raises(ValueError, match="at least one official source"):
        EditorialPostDraft.model_validate(payload)


def test_editorial_rag_is_opt_in_and_requires_eligible_official_sources() -> None:
    assert post_draft().include_in_rag is False

    repository = MemoryEditorialRepository()
    service = EditorialService(repository)
    author = principal("content_author")
    revision = service.create_post(author, post_draft(include_in_rag=True))
    repository.eligible_sources = False

    with pytest.raises(EditorialError, match="RAG-enabled posts"):
        service.submit(author, revision.id)

    assert repository.records[revision.id].status is EditorialStatus.DRAFT


def test_rag_enabled_article_requires_domain_and_official_source() -> None:
    payload = post_draft().model_dump(mode="json")
    payload.update(
        {
            "content_type": "article",
            "domain_slug": None,
            "include_in_rag": True,
            "sources": [],
        }
    )

    with pytest.raises(ValueError, match="RAG-enabled posts require"):
        EditorialPostDraft.model_validate(payload)
