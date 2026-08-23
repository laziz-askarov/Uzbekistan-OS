from hashlib import sha256
from json import dumps
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.audit import AuditEvent
from app.database.models.geography import Language
from app.database.models.ingestion import ExtractionArtifact, ReviewItem, SourceSnapshot
from app.database.models.knowledge import (
    Chunk,
    Document,
    DocumentSource,
    DocumentVersion,
    Domain,
    PublicationRecord,
    Source,
    SourceOrganization,
)
from app.identity.service import AuthenticatedPrincipal
from app.knowledge.chunking import chunk_sections
from app.knowledge.publication import (
    PublicationCandidate,
    PublicationError,
    PublicationResult,
    ReviewedLineage,
)


class SqlAlchemyPublicationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_review_lineage(self, review_item_id):
        review = self.session.scalar(
            select(ReviewItem).where(ReviewItem.id == review_item_id).with_for_update()
        )
        if review is None:
            return None
        artifact = self.session.get(ExtractionArtifact, review.extraction_artifact_id)
        if artifact is None:
            raise RuntimeError("review item extraction artifact is missing")
        snapshot = self.session.get(SourceSnapshot, artifact.source_snapshot_id)
        if snapshot is None:
            raise RuntimeError("extraction artifact source snapshot is missing")
        publication = self.session.scalar(
            select(PublicationRecord).where(PublicationRecord.review_item_id == review.id)
        )
        existing = None
        if publication is not None:
            version = self.session.get(DocumentVersion, publication.document_version_id)
            if version is None:
                raise RuntimeError("publication document version is missing")
            existing = PublicationResult(
                publication_id=publication.id,
                document_id=version.document_id,
                document_version_id=version.id,
                candidate_sha256=publication.candidate_sha256,
                published_at=publication.published_at,
            )
        return ReviewedLineage(
            review_item_id=review.id,
            review_status=review.status,
            reviewed_at=review.decided_at,
            source_id=snapshot.source_id,
            snapshot_sha256=snapshot.sha256,
            artifact_storage_key=artifact.storage_key,
            artifact_sha256=artifact.sha256,
            existing_publication=existing,
        )

    def publish_candidate(
        self,
        candidate: PublicationCandidate,
        lineage: ReviewedLineage,
        principal: AuthenticatedPrincipal,
        *,
        published_at,
    ) -> PublicationResult:
        domain = self.session.scalar(select(Domain).where(Domain.slug == candidate.domain))
        language = self.session.scalar(select(Language).where(Language.code == candidate.language))
        if domain is None or not domain.is_active:
            raise PublicationError("domain_not_found", "candidate domain is not active")
        if language is None or not language.is_active:
            raise PublicationError("language_not_found", "candidate language is not active")

        snapshot = self.session.scalar(
            select(SourceSnapshot).where(
                SourceSnapshot.source_id == lineage.source_id,
                SourceSnapshot.sha256 == lineage.snapshot_sha256,
            )
        )
        source = self.session.get(Source, lineage.source_id)
        if snapshot is None or source is None:
            raise PublicationError(
                "source_lineage_missing",
                "reviewed source lineage is unavailable",
            )
        organization = self.session.get(SourceOrganization, source.organization_id)
        self._ensure_source_eligible(source, organization)

        document = self.session.scalar(
            select(Document).where(Document.slug == candidate.slug).with_for_update()
        )
        if document is None:
            document = Document(
                id=uuid4(),
                slug=candidate.slug,
                domain_id=domain.id,
                canonical_language_id=language.id,
                status="draft",
            )
            self.session.add(document)
            self.session.flush()
        elif document.domain_id != domain.id or document.canonical_language_id != language.id:
            raise PublicationError(
                "document_identity_conflict",
                "existing document domain or canonical language differs",
            )

        current_version = (
            self.session.get(DocumentVersion, document.current_version_id)
            if document.current_version_id
            else None
        )
        candidate_version = (
            candidate.version.major,
            candidate.version.minor,
            candidate.version.revision,
        )
        if current_version is not None:
            current_number = (
                current_version.version_major,
                current_version.version_minor,
                current_version.version_revision,
            )
            if candidate_version <= current_number:
                raise PublicationError(
                    "version_not_monotonic",
                    "candidate version must be newer than the current version",
                )

        document_version_id = uuid4()
        content = self._knowledge_content(
            candidate,
            lineage,
            document.id,
            organization,
            source,
            snapshot,
            published_at,
        )
        checksum = sha256(
            dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        version = DocumentVersion(
            id=document_version_id,
            document_id=document.id,
            language_id=language.id,
            translation_of_id=candidate.translation_of_id,
            version_major=candidate.version.major,
            version_minor=candidate.version.minor,
            version_revision=candidate.version.revision,
            title=candidate.title,
            summary=candidate.summary,
            content=content,
            checksum_sha256=checksum,
            effective_from=candidate.effective_from,
            effective_until=candidate.effective_until,
            reviewed_at=lineage.reviewed_at,
            published_at=published_at,
        )
        self.session.add(version)
        self.session.flush()

        locators = sorted(
            {citation.locator for section in candidate.sections for citation in section.citations}
        )
        self.session.add(
            DocumentSource(
                document_version_id=document_version_id,
                source_id=source.id,
                locator=" | ".join(locators),
                snapshot_sha256=snapshot.sha256,
            )
        )
        for semantic_chunk in chunk_sections(candidate.sections):
            chunk_attributes = dict(semantic_chunk.attributes)
            if candidate.topic:
                chunk_attributes["topic"] = candidate.topic
            self.session.add(
                Chunk(
                    id=uuid4(),
                    document_version_id=document_version_id,
                    section_id=semantic_chunk.section_id,
                    ordinal=semantic_chunk.ordinal,
                    content=semantic_chunk.content,
                    content_hash=semantic_chunk.content_hash,
                    token_count=semantic_chunk.token_count,
                    attributes=chunk_attributes,
                )
            )

        document.current_version_id = document_version_id
        document.status = "published"
        publication = PublicationRecord(
            id=uuid4(),
            review_item_id=lineage.review_item_id,
            document_version_id=document_version_id,
            published_by_principal_id=principal.id,
            candidate_sha256=candidate.sha256,
            published_at=published_at,
        )
        self.session.add(publication)
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=principal.id,
                action="knowledge.published",
                entity_type="knowledge.document_version",
                entity_id=document_version_id,
                request_id=principal.request_id,
                payload={
                    "document_id": str(document.id),
                    "review_item_id": str(lineage.review_item_id),
                    "candidate_sha256": candidate.sha256,
                },
                occurred_at=published_at,
            )
        )
        self.session.flush()
        return PublicationResult(
            publication_id=publication.id,
            document_id=document.id,
            document_version_id=document_version_id,
            candidate_sha256=candidate.sha256,
            published_at=published_at,
        )

    @staticmethod
    def _ensure_source_eligible(source, organization) -> None:
        if not source.is_active or source.crawl_policy not in {"allowed", "manual_only"}:
            raise PublicationError(
                "source_not_publication_eligible",
                "reviewed source is not approved for publication",
            )
        if organization is None or not organization.is_active or not organization.is_official:
            raise PublicationError(
                "source_organization_not_eligible",
                "reviewed source organization is not active and official",
            )

    @staticmethod
    def _knowledge_content(
        candidate,
        lineage,
        document_id,
        organization,
        source,
        snapshot,
        published_at,
    ):
        return {
            "id": str(document_id),
            "slug": candidate.slug,
            "domain": candidate.domain,
            "topic": candidate.topic,
            "language": candidate.language,
            "status": "published",
            "version": candidate.version.model_dump(mode="json"),
            "title": candidate.title,
            "summary": candidate.summary,
            "audiences": candidate.audiences,
            "keywords": candidate.keywords,
            "applicability": {
                "audiences": candidate.audiences,
                "nationalities": candidate.nationalities,
                "residency_statuses": candidate.residency_statuses,
                "locations": candidate.locations,
                "conditions": candidate.applicability_conditions,
            },
            "requirements": [
                requirement.model_dump(mode="json") for requirement in candidate.requirements
            ],
            "steps": [step.model_dump(mode="json") for step in candidate.steps],
            "fees": [fee.model_dump(mode="json") for fee in candidate.fees],
            "processing_time": (
                candidate.processing_time.model_dump(mode="json")
                if candidate.processing_time
                else None
            ),
            "sections": [section.model_dump(mode="json") for section in candidate.sections],
            "sources": [
                {
                    "id": str(source.id),
                    "organization": organization.name,
                    "title": source.title,
                    "url": source.url,
                    "retrieved_at": snapshot.fetched_at.isoformat(),
                    "snapshot_sha256": snapshot.sha256,
                }
            ],
            "effective_from": candidate.effective_from.isoformat(),
            "effective_until": (
                candidate.effective_until.isoformat() if candidate.effective_until else None
            ),
            "reviewed_at": lineage.reviewed_at.isoformat(),
            "published_at": published_at.isoformat(),
            "translation_of": (
                str(candidate.translation_of_id) if candidate.translation_of_id else None
            ),
        }
