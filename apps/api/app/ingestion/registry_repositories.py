from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.database.models.geography import Country
from app.database.models.knowledge import Source, SourceOrganization
from app.ingestion.models import SourceOrganizationEntry, SourceRegistryEntry
from app.ingestion.registry_sync import RegistrySyncError


class SqlAlchemySourceRegistryRepository:
    _SYNC_LOCK_KEY = 7_886_201_001

    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_sync_lock(self) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": self._SYNC_LOCK_KEY},
        )

    def upsert_organization(self, organization: SourceOrganizationEntry) -> bool:
        country_id = self.session.scalar(
            select(Country.id).where(Country.iso2 == organization.country_iso2)
        )
        if country_id is None:
            raise RegistrySyncError(
                f"organization country {organization.country_iso2!r} is not seeded"
            )
        conflict = self.session.scalar(
            select(SourceOrganization.id).where(
                SourceOrganization.slug == organization.slug,
                SourceOrganization.id != organization.id,
            )
        )
        if conflict is not None:
            raise RegistrySyncError(
                f"organization slug {organization.slug!r} belongs to a different database row"
            )

        row = self.session.get(SourceOrganization, organization.id)
        created = row is None
        if row is None:
            row = SourceOrganization(id=organization.id)
            self.session.add(row)
        row.country_id = country_id
        row.slug = organization.slug
        row.name = organization.name
        row.website_url = str(organization.website_url)
        row.is_official = organization.is_official
        row.is_active = organization.is_official
        self.session.flush()
        return created

    def upsert_source(self, source: SourceRegistryEntry) -> bool:
        conflict = self.session.scalar(
            select(Source.id).where(Source.url == str(source.url), Source.id != source.id)
        )
        if conflict is not None:
            raise RegistrySyncError(
                f"source URL {source.url!s} belongs to a different database row"
            )

        row = self.session.get(Source, source.id)
        created = row is None
        if row is None:
            row = Source(id=source.id)
            self.session.add(row)
        row.organization_id = source.organization.id
        row.url = str(source.url)
        row.title = source.title
        row.source_type = source.source_type.value
        row.crawl_policy = source.crawl_policy.value
        row.trust_tier = source.trust_tier
        row.is_active = source.production_eligible and source.organization.is_official
        row.last_verified_at = source.reviewed_at
        self.session.flush()
        return created

    def deactivate_sources_except(self, source_ids: set[UUID]) -> int:
        statement = update(Source).where(Source.is_active.is_(True))
        if source_ids:
            statement = statement.where(Source.id.not_in(source_ids))
        result = self.session.execute(statement.values(is_active=False))
        return int(result.rowcount or 0)

    def deactivate_organizations_except(self, organization_ids: set[UUID]) -> int:
        statement = update(SourceOrganization).where(SourceOrganization.is_active.is_(True))
        if organization_ids:
            statement = statement.where(SourceOrganization.id.not_in(organization_ids))
        result = self.session.execute(statement.values(is_active=False))
        return int(result.rowcount or 0)
