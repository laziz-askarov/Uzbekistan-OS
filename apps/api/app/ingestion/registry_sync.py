from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.ingestion.models import SourceOrganizationEntry, SourceRegistry, SourceRegistryEntry


class RegistrySyncError(RuntimeError):
    pass


class SourceRegistryRepository(Protocol):
    def acquire_sync_lock(self) -> None: ...

    def upsert_organization(self, organization: SourceOrganizationEntry) -> bool: ...

    def upsert_source(self, source: SourceRegistryEntry) -> bool: ...

    def deactivate_sources_except(self, source_ids: set[UUID]) -> int: ...

    def deactivate_organizations_except(self, organization_ids: set[UUID]) -> int: ...


@dataclass(frozen=True, slots=True)
class RegistrySyncResult:
    organizations_created: int
    organizations_updated: int
    sources_created: int
    sources_updated: int
    sources_deactivated: int
    organizations_deactivated: int


class RegistrySyncService:
    def __init__(self, *, repository: SourceRegistryRepository, environment: str) -> None:
        self.repository = repository
        self.environment = environment

    def synchronize(self, registry: SourceRegistry) -> RegistrySyncResult:
        if registry.environment != self.environment:
            raise RegistrySyncError(
                f"registry environment {registry.environment!r} does not match "
                f"runtime environment {self.environment!r}"
            )

        organizations: dict[UUID, SourceOrganizationEntry] = {}
        for source in registry.sources:
            existing = organizations.get(source.organization.id)
            if existing is not None and existing != source.organization:
                raise RegistrySyncError(
                    f"organization {source.organization.id} has conflicting registry definitions"
                )
            organizations[source.organization.id] = source.organization

        self.repository.acquire_sync_lock()

        organizations_created = 0
        for organization in organizations.values():
            organizations_created += int(self.repository.upsert_organization(organization))

        sources_created = 0
        for source in registry.sources:
            sources_created += int(self.repository.upsert_source(source))

        source_ids = {source.id for source in registry.sources}
        organization_ids = set(organizations)
        sources_deactivated = self.repository.deactivate_sources_except(source_ids)
        organizations_deactivated = self.repository.deactivate_organizations_except(
            organization_ids
        )

        return RegistrySyncResult(
            organizations_created=organizations_created,
            organizations_updated=len(organizations) - organizations_created,
            sources_created=sources_created,
            sources_updated=len(registry.sources) - sources_created,
            sources_deactivated=sources_deactivated,
            organizations_deactivated=organizations_deactivated,
        )
