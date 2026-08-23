from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.ingestion.models import CrawlPolicy, RegistryStatus, SourceRegistryEntry
from app.ingestion.registry import load_source_registry
from app.ingestion.registry_repositories import SqlAlchemySourceRegistryRepository
from app.ingestion.registry_sync import RegistrySyncError, RegistrySyncService

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "data/sources/registry.development.json"


class RecordingRegistryRepository:
    def __init__(self) -> None:
        self.locks = 0
        self.organizations: list[object] = []
        self.sources: list[SourceRegistryEntry] = []
        self.retained_source_ids: set[UUID] | None = None
        self.retained_organization_ids: set[UUID] | None = None

    def acquire_sync_lock(self) -> None:
        self.locks += 1

    def upsert_organization(self, organization) -> bool:
        self.organizations.append(organization)
        return len(self.organizations) == 1

    def upsert_source(self, source: SourceRegistryEntry) -> bool:
        self.sources.append(source)
        return False

    def deactivate_sources_except(self, source_ids: set[UUID]) -> int:
        self.retained_source_ids = source_ids
        return 2

    def deactivate_organizations_except(self, organization_ids: set[UUID]) -> int:
        self.retained_organization_ids = organization_ids
        return 1


class StatementRecordingSession:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return type("Result", (), {"rowcount": 0})()


def test_registry_sync_materializes_entries_and_deactivates_absent_rows() -> None:
    registry = load_source_registry(REGISTRY_PATH)
    repository = RecordingRegistryRepository()

    result = RegistrySyncService(
        repository=repository,
        environment="development",
    ).synchronize(registry)

    assert result.organizations_created == 1
    assert result.sources_updated == 1
    assert result.sources_deactivated == 2
    assert result.organizations_deactivated == 1
    assert repository.retained_source_ids == {registry.sources[0].id}
    assert repository.retained_organization_ids == {registry.sources[0].organization.id}
    assert repository.locks == 1


def test_registry_deactivation_preserves_admin_managed_sources_and_organizations() -> None:
    session = StatementRecordingSession()
    repository = SqlAlchemySourceRegistryRepository(session)

    repository.deactivate_sources_except(set())
    repository.deactivate_organizations_except(set())

    statements = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.statements
    ]
    assert all("managed_source_configs" in statement for statement in statements)


def test_registry_sync_fails_before_writes_for_environment_mismatch() -> None:
    repository = RecordingRegistryRepository()

    with pytest.raises(RegistrySyncError, match="does not match"):
        RegistrySyncService(repository=repository, environment="production").synchronize(
            load_source_registry(REGISTRY_PATH)
        )

    assert repository.sources == []
    assert repository.organizations == []
    assert repository.locks == 0


def test_registry_sync_rejects_conflicting_organization_definitions() -> None:
    registry = load_source_registry(REGISTRY_PATH)
    source = registry.sources[0]
    approved = source.model_copy(
        update={
            "id": uuid4(),
            "slug": "second-source",
            "url": "https://example.invalid/second-source",
            "organization": source.organization.model_copy(update={"name": "Conflicting name"}),
            "crawl_policy": CrawlPolicy.ALLOWED,
            "status": RegistryStatus.APPROVED,
            "owner": "content-team",
            "reviewed_at": datetime(2026, 8, 1, tzinfo=UTC),
            "production_eligible": True,
        }
    )
    conflicting_registry = registry.model_copy(update={"sources": [source, approved]})

    with pytest.raises(RegistrySyncError, match="conflicting registry definitions"):
        RegistrySyncService(
            repository=RecordingRegistryRepository(),
            environment="development",
        ).synchronize(conflicting_registry)
