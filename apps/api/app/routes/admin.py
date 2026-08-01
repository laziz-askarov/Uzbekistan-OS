from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.dependencies import (
    get_authenticated_principal,
    get_publication_service,
    get_review_service,
)
from app.identity.service import AuthenticatedPrincipal
from app.ingestion.review import (
    ArtifactComparison,
    ReviewDecision,
    ReviewQueueRecord,
    ReviewRecord,
    ReviewService,
    ReviewStatus,
    SectionChangeType,
)
from app.knowledge.publication import PublicationCandidate, PublicationResult, PublicationService
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/admin", tags=["administration"])


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    reason: str = Field(min_length=1, max_length=2000)


class ReviewItemData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    extraction_artifact_id: UUID
    status: ReviewStatus
    priority: int = Field(ge=0, le=100)
    assigned_principal_id: UUID | None
    decision_reason: str | None
    decided_at: datetime | None
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ReviewRecord) -> "ReviewItemData":
        return cls(
            id=record.id,
            extraction_artifact_id=record.extraction_artifact_id,
            status=record.status,
            priority=record.priority,
            assigned_principal_id=record.assigned_user_id,
            decision_reason=record.decision_reason,
            decided_at=record.decided_at,
            updated_at=record.updated_at,
        )


class ReviewQueueItemData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review: ReviewItemData
    source_id: UUID
    source_title: str
    source_url: AnyHttpUrl
    fetched_at: datetime
    section_count: int = Field(ge=1)

    @classmethod
    def from_record(cls, record: ReviewQueueRecord) -> "ReviewQueueItemData":
        return cls(
            review=ReviewItemData.from_record(record.review),
            source_id=record.source_id,
            source_title=record.source_title,
            source_url=record.source_url,
            fetched_at=record.fetched_at,
            section_count=record.section_count,
        )


class ArtifactSectionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    heading: str
    body: str


class ArtifactDetailData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source_id: UUID
    snapshot_id: UUID
    adapter_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    media_type: str
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extracted_at: datetime
    sections: list[ArtifactSectionData] = Field(min_length=1)


class SectionChangeData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    change_type: SectionChangeType
    previous_heading: str | None
    current_heading: str | None


class ArtifactComparisonData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_artifact_id: UUID
    previous_artifact_id: UUID | None
    changed: bool
    changes: list[SectionChangeData]

    @classmethod
    def from_comparison(cls, comparison: ArtifactComparison) -> "ArtifactComparisonData":
        return cls(
            current_artifact_id=comparison.current_artifact_id,
            previous_artifact_id=comparison.previous_artifact_id,
            changed=comparison.changed,
            changes=[
                SectionChangeData(
                    section_id=change.section_id,
                    change_type=change.change_type,
                    previous_heading=change.previous_heading,
                    current_heading=change.current_heading,
                )
                for change in comparison.changes
            ],
        )


@router.get(
    "/reviews",
    response_model=SuccessResponse[list[ReviewQueueItemData]],
    operation_id="listReviewQueue",
    summary="List review queue items",
)
def list_review_queue(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ReviewService, Depends(get_review_service)],
    status: Annotated[ReviewStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessResponse[list[ReviewQueueItemData]]:
    records = service.list_queue(
        principal.reviewer_context(),
        status=status,
        limit=limit,
    )
    return SuccessResponse(
        data=[ReviewQueueItemData.from_record(record) for record in records],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/reviews/{review_item_id}/claim",
    response_model=SuccessResponse[ReviewItemData],
    operation_id="claimReviewItem",
    summary="Claim a pending review item",
)
def claim_review_item(
    review_item_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> SuccessResponse[ReviewItemData]:
    record = service.claim(principal.reviewer_context(), review_item_id)
    return SuccessResponse(
        data=ReviewItemData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/reviews/{review_item_id}/decision",
    response_model=SuccessResponse[ReviewItemData],
    operation_id="decideReviewItem",
    summary="Approve or reject an assigned review item",
)
def decide_review_item(
    review_item_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> SuccessResponse[ReviewItemData]:
    record = service.decide(
        principal.reviewer_context(),
        review_item_id,
        payload.decision,
        reason=payload.reason,
    )
    return SuccessResponse(
        data=ReviewItemData.from_record(record),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/artifacts/{artifact_id}",
    response_model=SuccessResponse[ArtifactDetailData],
    operation_id="getExtractionArtifact",
    summary="Get a checksum-verified extraction artifact",
)
def get_extraction_artifact(
    artifact_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> SuccessResponse[ArtifactDetailData]:
    artifact = service.artifact(principal.reviewer_context(), artifact_id)
    return SuccessResponse(
        data=ArtifactDetailData(
            id=artifact_id,
            source_id=artifact.source_id,
            snapshot_id=artifact.snapshot_id,
            adapter_key=artifact.adapter_key,
            media_type=artifact.media_type,
            raw_sha256=artifact.raw_sha256,
            normalized_sha256=artifact.normalized_sha256,
            extracted_at=artifact.extracted_at,
            sections=[
                ArtifactSectionData(id=section.id, heading=section.heading, body=section.body)
                for section in artifact.sections
            ],
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/artifacts/{artifact_id}/comparison",
    response_model=SuccessResponse[ArtifactComparisonData],
    operation_id="compareExtractionArtifact",
    summary="Compare an extraction artifact with its previous approved version",
)
def compare_extraction_artifact(
    artifact_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> SuccessResponse[ArtifactComparisonData]:
    comparison = service.compare(principal.reviewer_context(), artifact_id)
    return SuccessResponse(
        data=ArtifactComparisonData.from_comparison(comparison),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/publications",
    response_model=SuccessResponse[PublicationResult],
    operation_id="publishKnowledgeCandidate",
    summary="Publish an approved knowledge candidate",
)
def publish_knowledge_candidate(
    candidate: PublicationCandidate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[PublicationService, Depends(get_publication_service)],
) -> SuccessResponse[PublicationResult]:
    result = service.publish(
        principal,
        candidate,
        published_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
