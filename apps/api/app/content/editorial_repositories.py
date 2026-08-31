from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, aliased

from app.content.editorial import (
    ContentType,
    EditorialAuditRecord,
    EditorialAuthorDraft,
    EditorialAuthorRecord,
    EditorialError,
    EditorialPostDraft,
    EditorialPostSummaryRecord,
    EditorialRevisionDetailRecord,
    EditorialRevisionDraft,
    EditorialRevisionRecord,
    EditorialSourceReference,
    EditorialStatus,
    PublishedEditorialPostRecord,
    PublishedEditorialSourceRecord,
    PublishedEditorialSummaryRecord,
    PublishedEditorialTranslationRecord,
)
from app.content.rag import chunk_editorial_markdown
from app.database.models.audit import AuditEvent
from app.database.models.content import (
    ContentAuthor,
    ContentPost,
    ContentPostSource,
    ContentPostVersion,
    ContentPublicationRecord,
    ContentRagChunk,
)
from app.database.models.geography import Language
from app.database.models.knowledge import (
    DocumentSource,
    Domain,
    Source,
    SourceOrganization,
)
from app.identity.service import AuthenticatedPrincipal

REVIEW_DAYS_BY_DOMAIN = {
    "immigration": 30,
    "business-registration": 30,
    "healthcare": 30,
    "everyday-living": 60,
    "tourism": 180,
}


class SqlAlchemyEditorialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_published_posts(
        self,
        *,
        domain_slug: str | None,
        language_code: str | None,
        limit: int,
    ) -> tuple[PublishedEditorialSummaryRecord, ...]:
        statement = (
            select(
                ContentPost,
                ContentPostVersion,
                Domain.slug,
                Language.code,
                ContentAuthor,
            )
            .join(
                ContentPostVersion,
                ContentPostVersion.id == ContentPost.published_version_id,
            )
            .outerjoin(Domain, Domain.id == ContentPost.domain_id)
            .join(Language, Language.id == ContentPost.language_id)
            .join(ContentAuthor, ContentAuthor.id == ContentPostVersion.author_id)
            .where(
                ContentPost.status == EditorialStatus.PUBLISHED.value,
                ContentPostVersion.status == EditorialStatus.PUBLISHED.value,
                ContentAuthor.is_active.is_(True),
            )
            .order_by(ContentPostVersion.published_at.desc(), ContentPost.id.asc())
            .limit(limit)
        )
        if domain_slug is not None:
            statement = statement.where(Domain.slug == domain_slug)
        if language_code is not None:
            statement = statement.where(Language.code == language_code)
        rows = self.session.execute(statement)
        return tuple(
            PublishedEditorialSummaryRecord(
                id=post.id,
                slug=post.slug,
                content_type=ContentType(post.content_type),
                domain_slug=str(domain) if domain is not None else None,
                language_code=str(language),
                title=version.title,
                summary=version.summary,
                hero_image_url=version.hero_image_url,
                hero_image_alt=version.hero_image_alt,
                author_name=author.name,
                author_slug=author.slug,
                published_at=self._required_published_at(version),
                updated_at=version.updated_at,
            )
            for post, version, domain, language, author in rows
        )

    def get_published_post(self, slug: str) -> PublishedEditorialPostRecord | None:
        row = self.session.execute(
            select(
                ContentPost,
                ContentPostVersion,
                Domain.slug,
                Language.code,
                ContentAuthor,
            )
            .join(
                ContentPostVersion,
                ContentPostVersion.id == ContentPost.published_version_id,
            )
            .outerjoin(Domain, Domain.id == ContentPost.domain_id)
            .join(Language, Language.id == ContentPost.language_id)
            .join(ContentAuthor, ContentAuthor.id == ContentPostVersion.author_id)
            .where(
                ContentPost.slug == slug,
                ContentPost.status == EditorialStatus.PUBLISHED.value,
                ContentPostVersion.status == EditorialStatus.PUBLISHED.value,
                ContentAuthor.is_active.is_(True),
            )
        ).one_or_none()
        if row is None:
            return None
        post, version, domain_slug, language_code, author = row
        source_rows = self.session.execute(
            select(ContentPostSource, Source, SourceOrganization)
            .join(Source, Source.id == ContentPostSource.source_id)
            .join(SourceOrganization, SourceOrganization.id == Source.organization_id)
            .where(
                ContentPostSource.post_version_id == version.id,
                Source.is_active.is_(True),
                SourceOrganization.is_active.is_(True),
            )
            .order_by(ContentPostSource.sort_order.asc(), ContentPostSource.id.asc())
        )
        translation_rows = self.session.execute(
            select(ContentPost, Language.code, ContentPostVersion.title)
            .join(Language, Language.id == ContentPost.language_id)
            .join(
                ContentPostVersion,
                ContentPostVersion.id == ContentPost.published_version_id,
            )
            .where(
                ContentPost.translation_group_id == post.translation_group_id,
                ContentPost.status == EditorialStatus.PUBLISHED.value,
                ContentPostVersion.status == EditorialStatus.PUBLISHED.value,
            )
            .order_by(Language.code.asc())
        )
        return PublishedEditorialPostRecord(
            id=post.id,
            version_id=version.id,
            version_number=version.version_number,
            slug=post.slug,
            content_type=ContentType(post.content_type),
            domain_slug=str(domain_slug) if domain_slug is not None else None,
            language_code=str(language_code),
            title=version.title,
            summary=version.summary,
            body_markdown=version.body_markdown,
            structured_content=version.structured_content,
            seo_title=version.seo_title,
            seo_description=version.seo_description,
            canonical_url=version.canonical_url,
            hero_image_url=version.hero_image_url,
            hero_image_alt=version.hero_image_alt,
            author=self._author_record(author),
            sources=tuple(
                PublishedEditorialSourceRecord(
                    source_id=reference.source_id,
                    title=source.title,
                    organization=organization.name,
                    url=source.url,
                    locator=reference.locator,
                )
                for reference, source, organization in source_rows
            ),
            translations=tuple(
                PublishedEditorialTranslationRecord(
                    language_code=str(language),
                    slug=translation.slug,
                    title=translation_title,
                )
                for translation, language, translation_title in translation_rows
            ),
            published_at=self._required_published_at(version),
            updated_at=version.updated_at,
            review_due_at=version.review_due_at,
        )

    def list_authors(self) -> tuple[EditorialAuthorRecord, ...]:
        authors = self.session.scalars(
            select(ContentAuthor)
            .where(ContentAuthor.is_active.is_(True))
            .order_by(ContentAuthor.name.asc())
        )
        return tuple(self._author_record(author) for author in authors)

    def create_author(
        self,
        draft: EditorialAuthorDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at,
    ) -> EditorialAuthorRecord:
        existing = self.session.scalar(
            select(ContentAuthor).where(ContentAuthor.principal_id == principal.id)
        )
        if existing is not None:
            raise EditorialError(
                "editorial_author_exists",
                "this staff principal already has an editorial author profile",
            )
        author = ContentAuthor(
            id=uuid4(),
            principal_id=principal.id,
            slug=draft.slug,
            name=draft.name,
            bio=draft.bio,
            avatar_url=draft.avatar_url,
            profile_url=draft.profile_url,
            is_active=True,
            created_at=created_at,
            updated_at=created_at,
        )
        self.session.add(author)
        self.session.flush()
        return self._author_record(author)

    def list_posts(
        self,
        *,
        status: EditorialStatus | None,
        limit: int,
    ) -> tuple[EditorialPostSummaryRecord, ...]:
        latest = aliased(ContentPostVersion)
        latest_revision_id = (
            select(ContentPostVersion.id)
            .where(ContentPostVersion.post_id == ContentPost.id)
            .order_by(ContentPostVersion.version_number.desc())
            .limit(1)
            .correlate(ContentPost)
            .scalar_subquery()
        )
        statement = (
            select(ContentPost, Domain.slug, Language.code, latest)
            .outerjoin(Domain, Domain.id == ContentPost.domain_id)
            .join(Language, Language.id == ContentPost.language_id)
            .join(latest, latest.id == latest_revision_id)
            .order_by(ContentPost.updated_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(latest.status == status.value)
        rows = self.session.execute(statement)
        return tuple(
            EditorialPostSummaryRecord(
                id=post.id,
                slug=post.slug,
                content_type=ContentType(post.content_type),
                domain_slug=str(domain_slug) if domain_slug is not None else None,
                language_code=str(language_code),
                status=EditorialStatus(post.status),
                published_version_id=post.published_version_id,
                latest_revision_id=version.id,
                latest_revision_number=version.version_number,
                latest_revision_status=EditorialStatus(version.status),
                latest_title=version.title,
                updated_at=post.updated_at,
            )
            for post, domain_slug, language_code, version in rows
        )

    def get_detail(self, revision_id: UUID) -> EditorialRevisionDetailRecord | None:
        row = self.session.execute(
            select(
                ContentPostVersion,
                ContentPost,
                Domain.slug,
                Language.code,
                ContentAuthor,
            )
            .join(ContentPost, ContentPost.id == ContentPostVersion.post_id)
            .outerjoin(Domain, Domain.id == ContentPost.domain_id)
            .join(Language, Language.id == ContentPost.language_id)
            .join(ContentAuthor, ContentAuthor.id == ContentPostVersion.author_id)
            .where(ContentPostVersion.id == revision_id)
        ).one_or_none()
        if row is None:
            return None
        version, post, domain_slug, language_code, author = row
        sources = self.session.scalars(
            select(ContentPostSource)
            .where(ContentPostSource.post_version_id == version.id)
            .order_by(ContentPostSource.sort_order.asc(), ContentPostSource.id.asc())
        )
        return EditorialRevisionDetailRecord(
            revision=self._record(version, post.content_type),
            slug=post.slug,
            domain_slug=str(domain_slug) if domain_slug is not None else None,
            language_code=str(language_code),
            translation_group_id=post.translation_group_id,
            title=version.title,
            summary=version.summary,
            body_markdown=version.body_markdown,
            structured_content=version.structured_content,
            seo_title=version.seo_title,
            seo_description=version.seo_description,
            canonical_url=version.canonical_url,
            hero_image_url=version.hero_image_url,
            hero_image_alt=version.hero_image_alt,
            include_in_rag=version.include_in_rag,
            author=self._author_record(author),
            sources=tuple(
                EditorialSourceReference(
                    source_id=source.source_id,
                    document_version_id=source.document_version_id,
                    locator=source.locator,
                    quote=source.quote,
                )
                for source in sources
            ),
        )

    def create_post(
        self,
        draft: EditorialPostDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at,
    ) -> EditorialRevisionRecord:
        domain_id = None
        if draft.domain_slug:
            domain = self.session.scalar(
                select(Domain).where(Domain.slug == draft.domain_slug, Domain.is_active.is_(True))
            )
            if domain is None:
                raise EditorialError("editorial_domain_not_found", "content domain is not active")
            domain_id = domain.id
        language = self.session.scalar(
            select(Language).where(
                Language.code == draft.language_code, Language.is_active.is_(True)
            )
        )
        if language is None:
            raise EditorialError("editorial_language_not_found", "content language is not active")
        self._require_author(draft.author_id)
        self._validate_source_references(draft)

        post = ContentPost(
            id=uuid4(),
            slug=draft.slug,
            content_type=draft.content_type.value,
            domain_id=domain_id,
            language_id=language.id,
            translation_group_id=draft.translation_group_id or uuid4(),
            status=EditorialStatus.DRAFT.value,
            created_by_principal_id=principal.id,
            created_at=created_at,
            updated_at=created_at,
        )
        self.session.add(post)
        self.session.flush()
        self._validate_rag_eligibility(draft, post)
        version = self._new_version(post.id, 1, draft, principal, created_at=created_at)
        return self._record(version, post.content_type)

    def create_revision(
        self,
        post_id: UUID,
        draft: EditorialRevisionDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at,
    ) -> EditorialRevisionRecord:
        post = self.session.scalar(
            select(ContentPost).where(ContentPost.id == post_id).with_for_update()
        )
        if post is None:
            raise EditorialError("editorial_post_not_found", "editorial post does not exist")
        if post.published_version_id is None or post.status != EditorialStatus.PUBLISHED.value:
            raise EditorialError(
                "editorial_post_not_published",
                "new revisions may only be created for a published post",
            )
        open_revision = self.session.scalar(
            select(ContentPostVersion.id).where(
                ContentPostVersion.post_id == post.id,
                ContentPostVersion.status.in_(("draft", "in_review", "approved")),
            )
        )
        if open_revision is not None:
            raise EditorialError(
                "editorial_revision_already_open",
                "this post already has an unpublished revision",
            )
        self._require_author(draft.author_id)
        self._validate_source_references(draft)
        self._validate_rag_eligibility(draft, post)
        version_number = (
            self.session.scalar(
                select(func.max(ContentPostVersion.version_number)).where(
                    ContentPostVersion.post_id == post.id
                )
            )
            or 0
        ) + 1
        version = self._new_version(
            post.id, version_number, draft, principal, created_at=created_at
        )
        return self._record(version, post.content_type)

    def get_for_update(self, revision_id: UUID) -> EditorialRevisionRecord | None:
        row = self.session.execute(
            select(ContentPostVersion, ContentPost.content_type)
            .join(ContentPost, ContentPost.id == ContentPostVersion.post_id)
            .where(ContentPostVersion.id == revision_id)
            .with_for_update()
        ).one_or_none()
        if row is None:
            return None
        version, content_type = row
        return self._record(version, content_type)

    def sources_are_eligible(self, revision_id: UUID) -> bool:
        eligible_count = self.session.scalar(
            select(func.count(ContentPostSource.id))
            .join(Source, Source.id == ContentPostSource.source_id)
            .join(SourceOrganization, SourceOrganization.id == Source.organization_id)
            .where(
                ContentPostSource.post_version_id == revision_id,
                Source.is_active.is_(True),
                Source.crawl_policy.in_(("allowed", "manual_only")),
                SourceOrganization.is_active.is_(True),
                SourceOrganization.is_official.is_(True),
            )
        )
        total_count = self.session.scalar(
            select(func.count(ContentPostSource.id)).where(
                ContentPostSource.post_version_id == revision_id
            )
        )
        return bool(total_count and eligible_count == total_count)

    def update_draft(
        self,
        record: EditorialRevisionRecord,
        draft: EditorialRevisionDraft,
        principal: AuthenticatedPrincipal,
        *,
        updated_at,
    ) -> EditorialRevisionDetailRecord:
        version = self.session.scalar(
            select(ContentPostVersion).where(ContentPostVersion.id == record.id).with_for_update()
        )
        if version is None:
            raise EditorialError(
                "editorial_revision_not_found", "editorial revision does not exist"
            )
        if version.status != EditorialStatus.DRAFT.value:
            raise EditorialError(
                "invalid_editorial_transition", "only draft revisions can be edited"
            )
        self._require_author(draft.author_id)
        self._validate_source_references(draft)
        version.title = draft.title
        version.summary = draft.summary
        version.body_markdown = draft.body_markdown
        version.structured_content = draft.structured_content
        version.seo_title = draft.seo_title
        version.seo_description = draft.seo_description
        version.canonical_url = draft.canonical_url
        version.hero_image_url = draft.hero_image_url
        version.hero_image_alt = draft.hero_image_alt
        version.include_in_rag = draft.include_in_rag
        version.author_id = draft.author_id
        version.checksum_sha256 = draft.checksum_sha256
        version.updated_at = updated_at
        self.session.execute(
            delete(ContentPostSource).where(ContentPostSource.post_version_id == version.id)
        )
        for sort_order, source in enumerate(draft.sources):
            self.session.add(
                ContentPostSource(
                    id=uuid4(),
                    post_version_id=version.id,
                    source_id=source.source_id,
                    document_version_id=source.document_version_id,
                    locator=source.locator,
                    quote=source.quote,
                    sort_order=sort_order,
                )
            )
        post = self.session.get(ContentPost, version.post_id)
        if post is None:
            raise EditorialError("editorial_post_not_found", "editorial post does not exist")
        self._validate_rag_eligibility(draft, post)
        post.updated_at = updated_at
        self.session.flush()
        detail = self.get_detail(version.id)
        if detail is None:
            raise RuntimeError("updated editorial revision could not be reloaded")
        return detail

    def save(self, record: EditorialRevisionRecord) -> None:
        version = self.session.get(ContentPostVersion, record.id)
        if version is None:
            raise EditorialError(
                "editorial_revision_not_found", "editorial revision does not exist"
            )
        version.status = record.status.value
        version.submitted_at = record.submitted_at
        version.reviewed_by_principal_id = record.reviewed_by_principal_id
        version.reviewed_at = record.reviewed_at
        version.decision_reason = record.decision_reason
        version.updated_at = record.updated_at
        post = self.session.get(ContentPost, record.post_id)
        if post is None:
            raise EditorialError("editorial_post_not_found", "editorial post does not exist")
        if post.published_version_id is None:
            post.status = record.status.value
            post.updated_at = record.updated_at
        self.session.flush()

    def publish(
        self,
        record: EditorialRevisionRecord,
        principal: AuthenticatedPrincipal,
        *,
        published_at,
    ) -> EditorialRevisionRecord:
        post = self.session.scalar(
            select(ContentPost).where(ContentPost.id == record.post_id).with_for_update()
        )
        version = self.session.scalar(
            select(ContentPostVersion).where(ContentPostVersion.id == record.id).with_for_update()
        )
        if post is None or version is None:
            raise EditorialError(
                "editorial_revision_not_found", "editorial revision does not exist"
            )
        if version.status != EditorialStatus.APPROVED.value:
            raise EditorialError(
                "invalid_editorial_transition", "revision approval changed before publication"
            )

        prior_version_id = post.published_version_id
        if prior_version_id:
            prior = self.session.get(ContentPostVersion, prior_version_id)
            if prior is not None:
                prior.status = EditorialStatus.STALE.value
                prior.updated_at = published_at

        domain_slug = self.session.scalar(select(Domain.slug).where(Domain.id == post.domain_id))
        review_days = REVIEW_DAYS_BY_DOMAIN.get(str(domain_slug), 90)
        version.status = EditorialStatus.PUBLISHED.value
        version.published_by_principal_id = principal.id
        version.published_at = published_at
        version.review_due_at = published_at + timedelta(days=review_days)
        version.updated_at = published_at
        post.published_version_id = version.id
        post.status = EditorialStatus.PUBLISHED.value
        post.updated_at = published_at
        self.session.add(
            ContentPublicationRecord(
                id=uuid4(),
                post_id=post.id,
                post_version_id=version.id,
                prior_version_id=prior_version_id,
                published_by_principal_id=principal.id,
                published_at=published_at,
            )
        )
        self.session.execute(
            delete(ContentRagChunk).where(ContentRagChunk.post_version_id == version.id)
        )
        if version.include_in_rag:
            for chunk in chunk_editorial_markdown(
                version.title, version.summary, version.body_markdown
            ):
                self.session.add(
                    ContentRagChunk(
                        id=uuid4(),
                        post_version_id=version.id,
                        section_id=chunk.section_id,
                        ordinal=chunk.ordinal,
                        heading=chunk.heading,
                        content=chunk.content,
                        content_hash=chunk.content_hash,
                        token_count=chunk.token_count,
                        created_at=published_at,
                    )
                )
        self.session.flush()
        return self._record(version, post.content_type)

    def append_audit(self, record: EditorialAuditRecord) -> None:
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=record.actor_user_id,
                action=record.action,
                entity_type="content.post_version",
                entity_id=record.entity_id,
                request_id=record.request_id,
                payload=record.payload,
                occurred_at=record.occurred_at,
            )
        )
        self.session.flush()

    def _new_version(
        self,
        post_id: UUID,
        version_number: int,
        draft: EditorialRevisionDraft,
        principal: AuthenticatedPrincipal,
        *,
        created_at,
    ) -> ContentPostVersion:
        version = ContentPostVersion(
            id=uuid4(),
            post_id=post_id,
            version_number=version_number,
            title=draft.title,
            summary=draft.summary,
            body_markdown=draft.body_markdown,
            structured_content=draft.structured_content,
            seo_title=draft.seo_title,
            seo_description=draft.seo_description,
            canonical_url=draft.canonical_url,
            hero_image_url=draft.hero_image_url,
            hero_image_alt=draft.hero_image_alt,
            include_in_rag=draft.include_in_rag,
            author_id=draft.author_id,
            status=EditorialStatus.DRAFT.value,
            checksum_sha256=draft.checksum_sha256,
            created_by_principal_id=principal.id,
            created_at=created_at,
            updated_at=created_at,
        )
        self.session.add(version)
        self.session.flush()
        for sort_order, source in enumerate(draft.sources):
            self.session.add(
                ContentPostSource(
                    id=uuid4(),
                    post_version_id=version.id,
                    source_id=source.source_id,
                    document_version_id=source.document_version_id,
                    locator=source.locator,
                    quote=source.quote,
                    sort_order=sort_order,
                )
            )
        self.session.flush()
        return version

    def _require_author(self, author_id: UUID) -> None:
        author = self.session.scalar(
            select(ContentAuthor).where(
                ContentAuthor.id == author_id, ContentAuthor.is_active.is_(True)
            )
        )
        if author is None:
            raise EditorialError("editorial_author_not_found", "content author is not active")

    @staticmethod
    def _author_record(author: ContentAuthor) -> EditorialAuthorRecord:
        return EditorialAuthorRecord(
            id=author.id,
            principal_id=author.principal_id,
            slug=author.slug,
            name=author.name,
            bio=author.bio,
            avatar_url=author.avatar_url,
            profile_url=author.profile_url,
            is_active=author.is_active,
        )

    @staticmethod
    def _required_published_at(version: ContentPostVersion) -> datetime:
        if version.published_at is None:
            raise RuntimeError("published editorial version is missing its publication timestamp")
        return version.published_at

    def _validate_source_references(self, draft: EditorialRevisionDraft) -> None:
        for reference in draft.sources:
            source = self.session.get(Source, reference.source_id)
            if source is None:
                raise EditorialError(
                    "editorial_source_not_found", "an editorial source does not exist"
                )
            if reference.document_version_id is not None:
                lineage = self.session.scalar(
                    select(DocumentSource).where(
                        DocumentSource.document_version_id == reference.document_version_id,
                        DocumentSource.source_id == reference.source_id,
                    )
                )
                if lineage is None:
                    raise EditorialError(
                        "editorial_source_lineage_invalid",
                        "cited document version is not linked to the selected source",
                    )

    @staticmethod
    def _validate_rag_eligibility(draft: EditorialRevisionDraft, post: ContentPost) -> None:
        if draft.include_in_rag and (post.domain_id is None or not draft.sources):
            raise EditorialError(
                "editorial_rag_requirements_missing",
                "RAG-enabled posts require a knowledge domain and at least one official source",
            )

    @staticmethod
    def _record(version: ContentPostVersion, content_type: str) -> EditorialRevisionRecord:
        return EditorialRevisionRecord(
            id=version.id,
            post_id=version.post_id,
            version_number=version.version_number,
            content_type=ContentType(content_type),
            status=EditorialStatus(version.status),
            checksum_sha256=version.checksum_sha256,
            created_by_principal_id=version.created_by_principal_id,
            include_in_rag=version.include_in_rag,
            submitted_at=version.submitted_at,
            reviewed_by_principal_id=version.reviewed_by_principal_id,
            reviewed_at=version.reviewed_at,
            decision_reason=version.decision_reason,
            published_by_principal_id=version.published_by_principal_id,
            published_at=version.published_at,
            updated_at=version.updated_at,
        )
