from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.content.editorial import (
    EditorialAuthorRecord,
    EditorialService,
    PublishedEditorialPostRecord,
    PublishedEditorialSourceRecord,
    PublishedEditorialSummaryRecord,
    PublishedEditorialTranslationRecord,
)
from app.dependencies import get_editorial_service
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/content", tags=["editorial content"])


class PublishedAuthorData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    slug: str
    name: str
    bio: str | None
    avatar_url: str | None
    profile_url: str | None

    @classmethod
    def from_record(cls, record: EditorialAuthorRecord) -> "PublishedAuthorData":
        return cls.model_validate(record)


class PublishedSourceData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    source_id: UUID
    document_version_id: UUID | None
    document_slug: str | None
    document_title: str | None
    reviewed_at: datetime | None
    title: str
    organization: str
    url: str
    locator: str

    @classmethod
    def from_record(cls, record: PublishedEditorialSourceRecord) -> "PublishedSourceData":
        return cls.model_validate(record)


class PublishedTranslationData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    language_code: str
    slug: str
    title: str

    @classmethod
    def from_record(cls, record: PublishedEditorialTranslationRecord) -> "PublishedTranslationData":
        return cls.model_validate(record)


class PublishedPostSummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    slug: str
    translation_group_id: UUID
    content_type: str
    domain_slug: str | None
    language_code: str
    title: str
    summary: str
    hero_image_url: str | None
    hero_image_alt: str | None
    author_name: str
    author_slug: str
    published_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: PublishedEditorialSummaryRecord) -> "PublishedPostSummaryData":
        return cls.model_validate(record)


class PublishedPostData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    version_id: UUID
    version_number: int
    slug: str
    content_type: str
    domain_slug: str | None
    language_code: str
    title: str
    summary: str
    body_markdown: str
    structured_content: dict[str, object]
    seo_title: str | None
    seo_description: str | None
    canonical_url: str | None
    hero_image_url: str | None
    hero_image_alt: str | None
    author: PublishedAuthorData
    sources: list[PublishedSourceData]
    translations: list[PublishedTranslationData]
    published_at: datetime
    updated_at: datetime
    review_due_at: datetime | None

    @classmethod
    def from_record(cls, record: PublishedEditorialPostRecord) -> "PublishedPostData":
        return cls(
            id=record.id,
            version_id=record.version_id,
            version_number=record.version_number,
            slug=record.slug,
            content_type=record.content_type,
            domain_slug=record.domain_slug,
            language_code=record.language_code,
            title=record.title,
            summary=record.summary,
            body_markdown=record.body_markdown,
            structured_content=record.structured_content,
            seo_title=record.seo_title,
            seo_description=record.seo_description,
            canonical_url=record.canonical_url,
            hero_image_url=record.hero_image_url,
            hero_image_alt=record.hero_image_alt,
            author=PublishedAuthorData.from_record(record.author),
            sources=[PublishedSourceData.from_record(item) for item in record.sources],
            translations=[
                PublishedTranslationData.from_record(item) for item in record.translations
            ],
            published_at=record.published_at,
            updated_at=record.updated_at,
            review_due_at=record.review_due_at,
        )


@router.get(
    "/posts",
    response_model=SuccessResponse[list[PublishedPostSummaryData]],
    operation_id="listPublishedEditorialPosts",
    summary="List currently published editorial posts",
)
def list_published_editorial_posts(
    request: Request,
    service: Annotated[EditorialService, Depends(get_editorial_service)],
    domain: Annotated[
        str | None,
        Query(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] = None,
    language: Annotated[
        str | None,
        Query(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> SuccessResponse[list[PublishedPostSummaryData]]:
    records = service.list_published_posts(
        domain_slug=domain,
        language_code=language,
        limit=limit,
    )
    return SuccessResponse(
        data=[PublishedPostSummaryData.from_record(record) for record in records],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/posts/{slug}",
    response_model=SuccessResponse[PublishedPostData],
    operation_id="getPublishedEditorialPost",
    summary="Get the current published revision of an editorial post",
)
def get_published_editorial_post(
    slug: str,
    request: Request,
    service: Annotated[EditorialService, Depends(get_editorial_service)],
) -> SuccessResponse[PublishedPostData]:
    record = service.get_published_post(slug)
    return SuccessResponse(
        data=PublishedPostData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
