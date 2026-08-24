from datetime import UTC, datetime
from uuid import uuid4

from app.database.models.audit import AuditEvent
from app.database.models.geography import Country
from app.database.models.ingestion import ManagedSourceConfig
from app.database.models.knowledge import Source, SourceOrganization
from app.identity.service import AuthenticatedPrincipal
from app.ingestion.admin import CreateAdminSourceRequest
from app.ingestion.admin_repositories import SqlAlchemyAdminIngestionRepository


class RecordingCreateSourceSession:
    def __init__(self, country: Country) -> None:
        self.scalar_results = iter((None, None, country, None, None, None))
        self.events: list[object] = []

    def scalar(self, statement):
        del statement
        return next(self.scalar_results)

    def add(self, value: object) -> None:
        self.events.append(value)

    def flush(self) -> None:
        self.events.append("flush")


def test_managed_source_flushes_parent_source_before_foreign_key_config() -> None:
    country = Country(
        id=uuid4(),
        iso2="UZ",
        iso3="UZB",
        name="Uzbekistan",
        default_language_id=uuid4(),
        is_active=True,
    )
    session = RecordingCreateSourceSession(country)
    repository = SqlAlchemyAdminIngestionRepository(session)  # type: ignore[arg-type]
    principal = AuthenticatedPrincipal(
        id=uuid4(),
        roles=frozenset({"admin"}),
        request_id="source-create-request",
    )

    created = repository.create_managed_source(
        CreateAdminSourceRequest(
            title="Tourist Entry Guide",
            url="https://uzbekistan.travel",
            organization_name="Uzbekistan Travel",
            organization_website_url="https://uzbekistan.travel",
            domains=["tourism"],
            languages=["uz"],
            confirmed_official=True,
        ),
        principal,
        idempotency_key="create-tourism-source",
        created_at=datetime(2026, 8, 24, 13, 30, tzinfo=UTC),
    )

    organization_index = next(
        index for index, event in enumerate(session.events) if isinstance(event, SourceOrganization)
    )
    source_index = next(
        index for index, event in enumerate(session.events) if isinstance(event, Source)
    )
    config_index = next(
        index
        for index, event in enumerate(session.events)
        if isinstance(event, ManagedSourceConfig)
    )
    audit_index = next(
        index for index, event in enumerate(session.events) if isinstance(event, AuditEvent)
    )

    assert session.events[organization_index + 1] == "flush"
    assert session.events[source_index + 1] == "flush"
    assert organization_index < source_index < config_index < audit_index
    assert created.id == session.events[source_index].id
    assert created.slug == "tourist-entry-guide"
