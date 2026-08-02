from dataclasses import replace
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.identity.authentication import (
    AuthenticationError,
    DisabledIdentityVerifier,
    IdentityVerifier,
)
from app.identity.repositories import SqlAlchemyIdentityRepository
from app.identity.service import AuthenticatedPrincipal, IdentityError, IdentityService
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

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


@lru_cache
def get_identity_verifier() -> IdentityVerifier:
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
