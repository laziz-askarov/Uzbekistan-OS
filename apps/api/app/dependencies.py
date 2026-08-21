from dataclasses import replace
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.ai.answers import GroundedAnswerValidator
from app.ai.gateway import ModelGateway
from app.ai.openai_provider import OpenAIResponsesProvider
from app.ai.orchestration import GroundedAnswerOrchestrator
from app.assistant.service import GroundedAssistantService
from app.database.session import get_database_session
from app.identity.authentication import (
    AuthenticationError,
    DisabledIdentityVerifier,
    IdentityVerifier,
    SupabaseIdentityVerifier,
)
from app.identity.repositories import SqlAlchemyIdentityRepository
from app.identity.service import (
    AuthenticatedPrincipal,
    IdentityError,
    IdentityService,
    VerifiedIdentity,
)
from app.ingestion.admin import AdminIngestionService
from app.ingestion.admin_repositories import SqlAlchemyAdminIngestionRepository
from app.ingestion.fetchers import HttpSourceFetcher
from app.ingestion.models import SourceRegistry
from app.ingestion.ports import SnapshotStore
from app.ingestion.queue import IngestionQueue
from app.ingestion.repositories import SqlAlchemyIngestionRepository
from app.ingestion.review import ReviewService
from app.ingestion.review_repositories import SqlAlchemyReviewRepository
from app.ingestion.service import IngestionService
from app.ingestion.stores import S3SnapshotStore
from app.knowledge.lifecycle import KnowledgeLifecycleService
from app.knowledge.lifecycle_repositories import SqlAlchemyKnowledgeLifecycleRepository
from app.knowledge.publication import PublicationService
from app.knowledge.publication_repositories import SqlAlchemyPublicationRepository
from app.retrieval.evidence import EvidencePackBuilder
from app.retrieval.repositories import SqlAlchemyRetrievalRepository
from app.retrieval.service import HybridRetrievalService

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


@lru_cache
def get_identity_verifier() -> IdentityVerifier:
    from app.config import get_settings

    settings = get_settings()
    if settings.supabase_url and settings.supabase_anon_key:
        return SupabaseIdentityVerifier(
            supabase_url=settings.supabase_url,
            anon_key=settings.supabase_anon_key.get_secret_value(),
        )
    return DisabledIdentityVerifier()


def get_identity_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> IdentityService:
    return IdentityService(SqlAlchemyIdentityRepository(session))


@lru_cache
def get_snapshot_store() -> SnapshotStore:
    from app.config import get_settings

    return S3SnapshotStore.from_settings(get_settings())


@lru_cache
def get_runtime_source_registry() -> SourceRegistry:
    from app.config import get_settings
    from app.worker import load_runtime_registry

    return load_runtime_registry(get_settings())


@lru_cache
def get_ingestion_queue() -> IngestionQueue:
    from app.config import get_settings
    from app.worker import build_queue

    return build_queue(get_settings())


def get_admin_ingestion_service(
    session: Annotated[Session, Depends(get_database_session)],
    object_store: Annotated[SnapshotStore, Depends(get_snapshot_store)],
    registry: Annotated[SourceRegistry, Depends(get_runtime_source_registry)],
    queue: Annotated[IngestionQueue, Depends(get_ingestion_queue)],
) -> AdminIngestionService:
    from app.config import get_settings

    settings = get_settings()
    return AdminIngestionService(
        registry=registry,
        repository=SqlAlchemyAdminIngestionRepository(session),
        queue=queue,
        ingestion_service=IngestionService(
            fetcher=HttpSourceFetcher(),
            snapshot_store=object_store,
            repository=SqlAlchemyIngestionRepository(session),
            max_pdf_pages=settings.ingestion_max_pdf_pages,
            max_normalized_characters=settings.ingestion_max_normalized_characters,
        ),
    )


def get_review_service(
    session: Annotated[Session, Depends(get_database_session)],
    object_store: Annotated[SnapshotStore, Depends(get_snapshot_store)],
) -> ReviewService:
    return ReviewService(
        repository=SqlAlchemyReviewRepository(session),
        object_store=object_store,
    )


def get_publication_service(
    session: Annotated[Session, Depends(get_database_session)],
    object_store: Annotated[SnapshotStore, Depends(get_snapshot_store)],
) -> PublicationService:
    return PublicationService(
        repository=SqlAlchemyPublicationRepository(session),
        object_store=object_store,
    )


def get_knowledge_lifecycle_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> KnowledgeLifecycleService:
    return KnowledgeLifecycleService(SqlAlchemyKnowledgeLifecycleRepository(session))


def get_grounded_assistant_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> GroundedAssistantService:
    from app.ai.settings import load_ai_runtime_configuration
    from app.config import get_settings

    settings = get_settings()
    runtime = load_ai_runtime_configuration(settings)
    providers = {}
    if runtime.generation_enabled and settings.openai_api_key is not None:
        providers["openai"] = OpenAIResponsesProvider(
            api_key=settings.openai_api_key.get_secret_value(),
            model_by_role=runtime.provider_model_by_role,
        )
    return GroundedAssistantService(
        retrieval=HybridRetrievalService(SqlAlchemyRetrievalRepository(session)),
        evidence_builder=EvidencePackBuilder(
            max_items=runtime.policy.evidence_max_items,
            max_characters=runtime.policy.evidence_max_characters,
        ),
        orchestrator=GroundedAnswerOrchestrator(
            prompts=runtime.prompts,
            gateway=ModelGateway(routes=runtime.routes, providers=providers),
            validator=GroundedAnswerValidator(),
        ),
        context_assembler=runtime.policy.build_context_assembler(),
        retrieval_limit=runtime.policy.retrieval_limit,
    )


def get_authenticated_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    verifier: Annotated[IdentityVerifier, Depends(get_identity_verifier)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            "missing_bearer_token",
            "a Bearer access token is required",
        )
    if not credentials.credentials.strip():
        raise AuthenticationError(
            "invalid_bearer_token",
            "the Bearer access token is invalid",
        )

    verified = verifier.verify(credentials.credentials)
    verified = replace(verified, request_id=request.state.request_id)
    try:
        return identity_service.resolve(verified)
    except IdentityError as error:
        raise AuthenticationError(error.code, str(error)) from error


def get_verified_identity(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    verifier: Annotated[IdentityVerifier, Depends(get_identity_verifier)],
) -> VerifiedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("missing_bearer_token", "a Bearer access token is required")
    verified = verifier.verify(credentials.credentials)
    return replace(verified, request_id=request.state.request_id)
