from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.dependencies import (
    get_admin_ingestion_query_service,
    get_admin_ingestion_service,
    get_admin_ingestion_upload_service,
    get_authenticated_principal,
    get_knowledge_lifecycle_service,
    get_publication_service,
    get_review_service,
)
from app.identity.service import AuthenticatedPrincipal
from app.ingestion.admin import (
    AdminIngestionService,
    AdminSourceRecord,
    CreateAdminSourceRequest,
    IngestionJobRecord,
    ManualUploadRequest,
    ManualUploadResult,
    QueueCrawlRequest,
)
from app.ingestion.review import (
    ArtifactComparison,
    ReviewDecision,
    ReviewQueueRecord,
    ReviewRecord,
    ReviewService,
    ReviewStatus,
    SectionChangeType,
)
from app.knowledge.lifecycle import (
    ExpireDocumentRequest,
    ExpireDocumentResult,
    IndexJobResult,
    KnowledgeLifecycleService,
    ReindexDocumentRequest,
)
from app.knowledge.publication import PublicationCandidate, PublicationResult, PublicationService
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get(
    "/sources",
    response_model=SuccessResponse[list[AdminSourceRecord]],
    operation_id="listAdminSources",
    summary="List configured ingestion sources",
)
def list_admin_sources(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[AdminIngestionService, Depends(get_admin_ingestion_query_service)],
) -> SuccessResponse[list[AdminSourceRecord]]:
    return SuccessResponse(
        data=list(service.list_sources(principal)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/sources",
    response_model=SuccessResponse[AdminSourceRecord],
    status_code=201,
    operation_id="createAdminSource",
    summary="Register an official manual evidence source",
)
def create_admin_source(
    payload: CreateAdminSourceRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[AdminIngestionService, Depends(get_admin_ingestion_query_service)],
) -> SuccessResponse[AdminSourceRecord]:
    return SuccessResponse(
        data=service.create_source(
            principal,
            payload,
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/ingestion/jobs",
    response_model=SuccessResponse[list[IngestionJobRecord]],
    operation_id="listIngestionJobs",
    summary="List recent ingestion jobs",
)
def list_ingestion_jobs(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[AdminIngestionService, Depends(get_admin_ingestion_query_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SuccessResponse[list[IngestionJobRecord]]:
    return SuccessResponse(
        data=list(service.list_jobs(principal, limit=limit)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/ingestion/topics",
    response_model=SuccessResponse[list[str]],
    operation_id="listIngestionTopics",
    summary="List topics used by manual evidence uploads",
)
def list_ingestion_topics(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[AdminIngestionService, Depends(get_admin_ingestion_query_service)],
) -> SuccessResponse[list[str]]:
    return SuccessResponse(
        data=list(service.list_topics(principal)),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/ingestion/jobs",
    response_model=SuccessResponse[IngestionJobRecord],
    status_code=202,
    operation_id="createIngestionJob",
    summary="Queue a crawl for an approved source",
)
def create_ingestion_job(
    payload: QueueCrawlRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[AdminIngestionService, Depends(get_admin_ingestion_service)],
) -> SuccessResponse[IngestionJobRecord]:
    return SuccessResponse(
        data=service.queue_crawl(
            principal,
            payload,
            idempotency_key=idempotency_key,
            enqueued_at=datetime.now(UTC),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/sources/{source_id}/uploads",
    response_model=SuccessResponse[ManualUploadResult],
    operation_id="uploadAdminSourceDocument",
    summary="Upload official source evidence for ingestion",
)
def upload_admin_source_document(
    source_id: UUID,
    payload: ManualUploadRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[
        AdminIngestionService,
        Depends(get_admin_ingestion_upload_service),
    ],
) -> SuccessResponse[ManualUploadResult]:
    return SuccessResponse(
        data=service.upload(
            principal,
            source_id,
            payload,
            idempotency_key=idempotency_key,
            uploaded_at=datetime.now(UTC),
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


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
    topic: str | None = None

    @classmethod
    def from_record(cls, record: ReviewQueueRecord) -> "ReviewQueueItemData":
        return cls(
            review=ReviewItemData.from_record(record.review),
            source_id=record.source_id,
            source_title=record.source_title,
            source_url=record.source_url,
            fetched_at=record.fetched_at,
            section_count=record.section_count,
            topic=record.topic,
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
    topic: str | None = None
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
            topic=artifact.topic,
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


@router.post(
    "/documents/{document_id}/expire",
    response_model=SuccessResponse[ExpireDocumentResult],
    operation_id="expireKnowledgeDocument",
    summary="Expire a published knowledge document",
)
def expire_knowledge_document(
    document_id: UUID,
    payload: ExpireDocumentRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[
        KnowledgeLifecycleService,
        Depends(get_knowledge_lifecycle_service),
    ],
) -> SuccessResponse[ExpireDocumentResult]:
    result = service.expire(
        principal,
        document_id,
        payload,
        expired_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/documents/{document_id}/reindex",
    response_model=SuccessResponse[IndexJobResult],
    operation_id="reindexKnowledgeDocument",
    summary="Queue a published knowledge document for re-indexing",
)
def reindex_knowledge_document(
    document_id: UUID,
    payload: ReindexDocumentRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[
        KnowledgeLifecycleService,
        Depends(get_knowledge_lifecycle_service),
    ],
) -> SuccessResponse[IndexJobResult]:
    result = service.reindex(
        principal,
        document_id,
        payload,
        idempotency_key=idempotency_key,
        requested_at=datetime.now(UTC),
    )
    return SuccessResponse(
        data=result,
        meta=ResponseMeta(request_id=request.state.request_id),
    )
