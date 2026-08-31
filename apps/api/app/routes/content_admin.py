from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.content.editorial import (
    EditorialAuthorDraft,
    EditorialAuthorRecord,
    EditorialDecision,
    EditorialPostDraft,
    EditorialPostSummaryRecord,
    EditorialRevisionDetailRecord,
    EditorialRevisionDraft,
    EditorialRevisionRecord,
    EditorialService,
    EditorialSourceReference,
    EditorialStatus,
    ReviewedKnowledgeSourceRecord,
)
from app.dependencies import get_authenticated_principal, get_editorial_service
from app.identity.service import AuthenticatedPrincipal
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/admin/content", tags=["editorial content"])


class EditorialRevisionData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    post_id: UUID
    version_number: int
    content_type: str
    status: EditorialStatus
    checksum_sha256: str
    created_by_principal_id: UUID
    include_in_rag: bool
    submitted_at: datetime | None
    reviewed_by_principal_id: UUID | None
    reviewed_at: datetime | None
    decision_reason: str | None
    published_by_principal_id: UUID | None
    published_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_record(cls, record: EditorialRevisionRecord) -> "EditorialRevisionData":
        return cls.model_validate(record)


class EditorialAuthorData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    principal_id: UUID | None
    slug: str
    name: str
    bio: str | None
    avatar_url: str | None
    profile_url: str | None
    is_active: bool

    @classmethod
    def from_record(cls, record: EditorialAuthorRecord) -> "EditorialAuthorData":
        return cls.model_validate(record)


class EditorialPostSummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    slug: str
    translation_group_id: UUID
    content_type: str
    domain_slug: str | None
    language_code: str
    status: EditorialStatus
    published_version_id: UUID | None
    latest_revision_id: UUID
    latest_revision_number: int
    latest_revision_status: EditorialStatus
    latest_title: str
    updated_at: datetime

    @classmethod
    def from_record(cls, record: EditorialPostSummaryRecord) -> "EditorialPostSummaryData":
        return cls.model_validate(record)


class ReviewedKnowledgeSourceData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    source_id: UUID
    document_id: UUID
    document_version_id: UUID
    document_slug: str
    document_title: str
    document_summary: str
    domain_slug: str
    language_code: str
    version_label: str
    source_title: str
    organization: str
    source_url: str
    source_locator: str
    reviewed_at: datetime
    published_at: datetime
    effective_until: date | None

    @classmethod
    def from_record(cls, record: ReviewedKnowledgeSourceRecord) -> "ReviewedKnowledgeSourceData":
        return cls.model_validate(record)


class EditorialRevisionDetailData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: EditorialRevisionData
    slug: str
    domain_slug: str | None
    language_code: str
    translation_group_id: UUID
    title: str
    summary: str
    body_markdown: str
    structured_content: dict[str, object]
    seo_title: str | None
    seo_description: str | None
    canonical_url: str | None
    hero_image_url: str | None
    hero_image_alt: str | None
    include_in_rag: bool
    author: EditorialAuthorData
    sources: list[EditorialSourceReference]

    @classmethod
    def from_record(cls, record: EditorialRevisionDetailRecord) -> "EditorialRevisionDetailData":
        return cls(
            revision=EditorialRevisionData.from_record(record.revision),
            slug=record.slug,
            domain_slug=record.domain_slug,
            language_code=record.language_code,
            translation_group_id=record.translation_group_id,
            title=record.title,
            summary=record.summary,
            body_markdown=record.body_markdown,
            structured_content=record.structured_content,
            seo_title=record.seo_title,
            seo_description=record.seo_description,
            canonical_url=record.canonical_url,
            hero_image_url=record.hero_image_url,
            hero_image_alt=record.hero_image_alt,
            include_in_rag=record.include_in_rag,
            author=EditorialAuthorData.from_record(record.author),
            sources=list(record.sources),
        )


class EditorialDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: EditorialDecision
    reason: str = Field(min_length=1, max_length=2000)


@router.get(
    "/authors",
    response_model=SuccessResponse[list[EditorialAuthorData]],
    operation_id="listEditorialAuthors",
    summary="List active editorial authors",
)
def list_editorial_authors(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[list[EditorialAuthorData]]:
    return SuccessResponse(
        data=[EditorialAuthorData.from_record(item) for item in service.list_authors(principal)],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/authors",
    response_model=SuccessResponse[EditorialAuthorData],
    status_code=201,
    operation_id="createEditorialAuthor",
    summary="Create the current staff member's editorial author profile",
)
def create_editorial_author(
    payload: EditorialAuthorDraft,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialAuthorData]:
    record = service.create_author(principal, payload, created_at=datetime.now(UTC))
    return SuccessResponse(
        data=EditorialAuthorData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/reviewed-sources",
    response_model=SuccessResponse[list[ReviewedKnowledgeSourceData]],
    operation_id="listReviewedEditorialSources",
    summary="List current reviewed knowledge publications available for editorial citation",
)
def list_reviewed_editorial_sources(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
    domain: Annotated[
        str | None,
        Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] = None,
    language: Annotated[
        str | None,
        Query(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> SuccessResponse[list[ReviewedKnowledgeSourceData]]:
    records = service.list_reviewed_sources(
        principal,
        domain_slug=domain,
        language_code=language,
        limit=limit,
    )
    return SuccessResponse(
        data=[ReviewedKnowledgeSourceData.from_record(record) for record in records],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/posts",
    response_model=SuccessResponse[list[EditorialPostSummaryData]],
    operation_id="listEditorialPosts",
    summary="List editorial posts by latest revision status",
)
def list_editorial_posts(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
    status: Annotated[EditorialStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> SuccessResponse[list[EditorialPostSummaryData]]:
    return SuccessResponse(
        data=[
            EditorialPostSummaryData.from_record(item)
            for item in service.list_posts(principal, status=status, limit=limit)
        ],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/posts",
    response_model=SuccessResponse[EditorialRevisionData],
    status_code=201,
    operation_id="createEditorialPost",
    summary="Create a new editorial post draft",
)
def create_editorial_post(
    payload: EditorialPostDraft,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionData]:
    record = service.create_post(principal, payload, created_at=datetime.now(UTC))
    return SuccessResponse(
        data=EditorialRevisionData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/posts/{post_id}/revisions",
    response_model=SuccessResponse[EditorialRevisionData],
    status_code=201,
    operation_id="createEditorialRevision",
    summary="Create a new draft revision for a published post",
)
def create_editorial_revision(
    post_id: UUID,
    payload: EditorialRevisionDraft,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionData]:
    record = service.create_revision(
        principal,
        post_id,
        payload,
        created_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=EditorialRevisionData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/revisions/{revision_id}",
    response_model=SuccessResponse[EditorialRevisionDetailData],
    operation_id="getEditorialRevision",
    summary="Get an editorial revision and its source citations",
)
def get_editorial_revision(
    revision_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionDetailData]:
    return SuccessResponse(
        data=EditorialRevisionDetailData.from_record(service.get_revision(principal, revision_id)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put(
    "/revisions/{revision_id}",
    response_model=SuccessResponse[EditorialRevisionDetailData],
    operation_id="updateEditorialRevision",
    summary="Update an editable editorial draft",
)
def update_editorial_revision(
    revision_id: UUID,
    payload: EditorialRevisionDraft,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionDetailData]:
    record = service.update_draft(
        principal,
        revision_id,
        payload,
        updated_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=EditorialRevisionDetailData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/revisions/{revision_id}/submit",
    response_model=SuccessResponse[EditorialRevisionData],
    operation_id="submitEditorialRevision",
    summary="Submit an editorial draft for review",
)
def submit_editorial_revision(
    revision_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionData]:
    record = service.submit(principal, revision_id, submitted_at=datetime.now(UTC))
    return SuccessResponse(
        data=EditorialRevisionData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/revisions/{revision_id}/decision",
    response_model=SuccessResponse[EditorialRevisionData],
    operation_id="decideEditorialRevision",
    summary="Approve an editorial revision or request changes",
)
def decide_editorial_revision(
    revision_id: UUID,
    payload: EditorialDecisionRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionData]:
    record = service.decide(
        principal,
        revision_id,
        payload.decision,
        reason=payload.reason,
        reviewed_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=EditorialRevisionData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/revisions/{revision_id}/publish",
    response_model=SuccessResponse[EditorialRevisionData],
    operation_id="publishEditorialRevision",
    summary="Publish an approved editorial revision",
)
def publish_editorial_revision(
    revision_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[EditorialRevisionData]:
    record = service.publish(principal, revision_id, published_at=datetime.now(UTC))
    return SuccessResponse(
        data=EditorialRevisionData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
