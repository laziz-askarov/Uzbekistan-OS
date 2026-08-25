from datetime import datetime
from re import sub
from unicodedata import normalize
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.audit import AuditEvent
from app.database.models.geography import Country
from app.database.models.ingestion import CrawlJob, ExtractionArtifact, ManagedSourceConfig
from app.database.models.knowledge import Source, SourceOrganization
from app.identity.service import AuthenticatedPrincipal
from app.ingestion.admin import (
    AdminIngestionError,
    CreateAdminSourceRequest,
    IngestionJobRecord,
    PreparedCrawlJob,
    SourceDatabaseState,
)
from app.ingestion.models import (
    CrawlPolicy,
    RegistryStatus,
    SourceOrganizationEntry,
    SourceRegistryEntry,
    SourceType,
)


class SqlAlchemyAdminIngestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def source_states(self) -> tuple[SourceDatabaseState, ...]:
        sources = tuple(self.session.scalars(select(Source).order_by(Source.title)))
        records = []
        for source in sources:
            latest = self.session.scalar(
                select(CrawlJob)
                .where(CrawlJob.source_id == source.id)
                .order_by(CrawlJob.scheduled_at.desc(), CrawlJob.id.desc())
                .limit(1)
            )
            records.append(
                SourceDatabaseState(
                    id=source.id,
                    active=source.is_active,
                    last_verified_at=source.last_verified_at,
                    latest_job_status=latest.status if latest else None,
                )
            )
        return tuple(records)

    def managed_sources(self) -> tuple[SourceRegistryEntry, ...]:
        rows = self.session.execute(
            select(ManagedSourceConfig, Source, SourceOrganization, Country)
            .join(Source, Source.id == ManagedSourceConfig.source_id)
            .join(SourceOrganization, SourceOrganization.id == Source.organization_id)
            .join(Country, Country.id == SourceOrganization.country_id)
            .order_by(Source.title, Source.id)
        )
        return tuple(
            self._managed_source_entry(config, source, organization, country)
            for config, source, organization, country in rows
        )

    def create_managed_source(
        self,
        request: CreateAdminSourceRequest,
        principal: AuthenticatedPrincipal,
        *,
        idempotency_key: str,
        created_at: datetime,
    ) -> SourceRegistryEntry:
        replay = self.session.scalar(
            select(ManagedSourceConfig)
            .where(ManagedSourceConfig.idempotency_key == idempotency_key)
            .with_for_update()
        )
        if replay is not None:
            if replay.request_sha256 != request.sha256:
                raise AdminIngestionError(
                    "source_idempotency_conflict",
                    "idempotency key is already linked to different source details",
                )
            return self._entry_for_config(replay)

        existing_source = self.session.scalar(
            select(Source).where(Source.url == str(request.url)).with_for_update()
        )
        if existing_source is not None:
            raise AdminIngestionError(
                "source_url_conflict",
                "an ingestion source already uses this official URL",
            )
        country = self.session.scalar(select(Country).where(Country.iso2 == "UZ"))
        if country is None or not country.is_active:
            raise AdminIngestionError(
                "source_country_unavailable",
                "Uzbekistan must be present in the active country registry",
            )

        organization = self.session.scalar(
            select(SourceOrganization)
            .where(SourceOrganization.website_url == str(request.organization_website_url))
            .with_for_update()
        )
        if organization is not None and not organization.is_official:
            raise AdminIngestionError(
                "source_organization_not_official",
                "the matching organization is not approved as an official source",
            )
        if organization is None:
            organization_id = uuid4()
            organization = SourceOrganization(
                id=organization_id,
                country_id=country.id,
                slug=self._available_organization_slug(request.organization_name, organization_id),
                name=request.organization_name,
                website_url=str(request.organization_website_url),
                is_official=True,
                is_active=True,
            )
            self.session.add(organization)
            self.session.flush()
        else:
            organization.is_active = True

        source_id = uuid4()
        source = Source(
            id=source_id,
            organization_id=organization.id,
            url=str(request.url),
            title=request.title,
            source_type=SourceType.MANUAL.value,
            crawl_policy=CrawlPolicy.MANUAL_ONLY.value,
            # Admin-created sources require an explicit official-domain confirmation,
            # then every uploaded document still passes review and publication. Treat
            # that reviewed lineage as tier 1 so high-risk retrieval can use it.
            trust_tier=1,
            is_active=True,
            last_verified_at=created_at,
        )
        # ManagedSourceConfig uses its source_id as both its primary key and a
        # foreign key. Flush the parent explicitly so SQLAlchemy cannot emit the
        # configuration insert before knowledge.sources when no ORM relationship
        # is present between these models. The surrounding request transaction
        # still commits or rolls back all source-creation writes atomically.
        self.session.add(source)
        self.session.flush()
        config = ManagedSourceConfig(
            source_id=source_id,
            slug=self._available_source_slug(request.title, source_id),
            domains=list(request.domains),
            languages=list(request.languages),
            adapter_key="generic-manual",
            registry_status=RegistryStatus.APPROVED.value,
            production_eligible=True,
            created_by_principal_id=principal.id,
            idempotency_key=idempotency_key,
            request_sha256=request.sha256,
            created_at=created_at,
            updated_at=created_at,
        )
        self.session.add(config)
        self.session.add(
            AuditEvent(
                id=uuid4(),
                actor_user_id=principal.id,
                action="ingestion.source_created",
                entity_type="knowledge.source",
                entity_id=source_id,
                request_id=principal.request_id,
                payload={
                    "source_url": str(request.url),
                    "organization": request.organization_name,
                    "domains": list(request.domains),
                    "languages": list(request.languages),
                    "crawl_policy": CrawlPolicy.MANUAL_ONLY.value,
                },
                occurred_at=created_at,
            )
        )
        self.session.flush()
        return self._managed_source_entry(config, source, organization, country)

    def list_jobs(self, *, limit: int) -> tuple[IngestionJobRecord, ...]:
        rows = self.session.execute(
            select(CrawlJob, Source.title)
            .join(Source, Source.id == CrawlJob.source_id)
            .order_by(CrawlJob.scheduled_at.desc(), CrawlJob.id.desc())
            .limit(limit)
        )
        return tuple(self._job_record(job, title) for job, title in rows)

    def list_topics(self) -> tuple[str, ...]:
        topic = ExtractionArtifact.details["topic"].as_string()
        values = self.session.scalars(
            select(topic).where(topic.is_not(None), topic != "").distinct().order_by(topic)
        )
        return tuple(str(value) for value in values if value)

    def prepare_crawl_job(
        self,
        source_id: UUID,
        idempotency_key: str,
        *,
        max_attempts: int,
        scheduled_at: datetime,
    ) -> PreparedCrawlJob:
        source = self.session.get(Source, source_id)
        if source is None:
            raise AdminIngestionError(
                "source_not_synchronized",
                "configured source is not synchronized to the database",
            )
        job = self.session.scalar(
            select(CrawlJob)
            .where(
                CrawlJob.source_id == source_id,
                CrawlJob.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        if job is not None:
            if job.max_attempts != max_attempts:
                raise AdminIngestionError(
                    "ingestion_job_conflict",
                    "idempotency key is already linked to different retry settings",
                )
            return PreparedCrawlJob(record=self._job_record(job, source.title), created=False)
        job = CrawlJob(
            id=uuid4(),
            source_id=source_id,
            idempotency_key=idempotency_key,
            status="queued",
            attempt_count=0,
            max_attempts=max_attempts,
            scheduled_at=scheduled_at,
            error={},
            result={},
        )
        self.session.add(job)
        self.session.flush()
        return PreparedCrawlJob(record=self._job_record(job, source.title), created=True)

    def _entry_for_config(self, config: ManagedSourceConfig) -> SourceRegistryEntry:
        row = self.session.execute(
            select(Source, SourceOrganization, Country)
            .join(SourceOrganization, SourceOrganization.id == Source.organization_id)
            .join(Country, Country.id == SourceOrganization.country_id)
            .where(Source.id == config.source_id)
        ).one_or_none()
        if row is None:
            raise AdminIngestionError(
                "managed_source_lineage_missing",
                "admin-managed source configuration has incomplete database lineage",
            )
        source, organization, country = row
        return self._managed_source_entry(config, source, organization, country)

    def _available_organization_slug(self, name: str, identifier: UUID) -> str:
        candidate = self._slug(name)
        conflict = self.session.scalar(
            select(SourceOrganization.id).where(SourceOrganization.slug == candidate)
        )
        return candidate if conflict is None else f"{candidate}-{identifier.hex[:8]}"

    def _available_source_slug(self, title: str, identifier: UUID) -> str:
        candidate = self._slug(title)
        conflict = self.session.scalar(
            select(ManagedSourceConfig.source_id).where(ManagedSourceConfig.slug == candidate)
        )
        return candidate if conflict is None else f"{candidate}-{identifier.hex[:8]}"

    @staticmethod
    def _slug(value: str) -> str:
        ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
        return sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "official-source"

    @staticmethod
    def _managed_source_entry(
        config: ManagedSourceConfig,
        source: Source,
        organization: SourceOrganization,
        country: Country,
    ) -> SourceRegistryEntry:
        return SourceRegistryEntry(
            id=source.id,
            slug=config.slug,
            organization=SourceOrganizationEntry(
                id=organization.id,
                slug=organization.slug,
                name=organization.name,
                website_url=organization.website_url,
                country_iso2=str(country.iso2).upper(),
                is_official=organization.is_official,
            ),
            title=source.title,
            url=source.url,
            source_type=SourceType(source.source_type),
            domains=config.domains,
            languages=config.languages,
            crawl_policy=CrawlPolicy(source.crawl_policy),
            adapter_key=config.adapter_key,
            trust_tier=source.trust_tier,
            status=RegistryStatus(config.registry_status),
            owner=str(config.created_by_principal_id),
            reviewed_at=source.last_verified_at,
            production_eligible=config.production_eligible,
            schedule=None,
        )

    @staticmethod
    def _job_record(job: CrawlJob, source_title: str) -> IngestionJobRecord:
        return IngestionJobRecord(
            id=job.id,
            source_id=job.source_id,
            source_title=source_title,
            idempotency_key=job.idempotency_key,
            status=job.status,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            scheduled_at=job.scheduled_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_code=str(job.error.get("code")) if job.error.get("code") else None,
            error_message=(str(job.error.get("message")) if job.error.get("message") else None),
        )
