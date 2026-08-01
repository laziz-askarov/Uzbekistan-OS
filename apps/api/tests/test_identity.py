from uuid import uuid4

import pytest

from app.identity.service import (
    IdentityError,
    IdentityService,
    PrincipalRecord,
    VerifiedIdentity,
)
from app.ingestion.review import ReviewerRole


class MemoryIdentityRepository:
    def __init__(self, record: PrincipalRecord | None) -> None:
        self.record = record
        self.touched = []

    def find_by_verified_subject(self, provider: str, subject: str) -> PrincipalRecord | None:
        if provider == "test-provider" and subject == "verified-subject":
            return self.record
        return None

    def touch_authenticated(self, principal_id) -> None:
        self.touched.append(principal_id)


def test_verified_identity_maps_to_internal_roles() -> None:
    record = PrincipalRecord(
        id=uuid4(),
        status="active",
        roles=frozenset({"content_reviewer", "knowledge_publisher"}),
    )
    repository = MemoryIdentityRepository(record)
    principal = IdentityService(repository).resolve(
        VerifiedIdentity(
            provider="test-provider",
            subject="verified-subject",
            request_id="identity-request",
        )
    )

    assert principal.id == record.id
    assert principal.roles == record.roles
    assert principal.reviewer_context().roles == frozenset({ReviewerRole.CONTENT_REVIEWER})
    assert repository.touched == [record.id]


def test_disabled_principal_is_rejected() -> None:
    record = PrincipalRecord(id=uuid4(), status="disabled", roles=frozenset({"admin"}))

    with pytest.raises(IdentityError, match="disabled"):
        IdentityService(MemoryIdentityRepository(record)).resolve(
            VerifiedIdentity(provider="test-provider", subject="verified-subject")
        )


def test_unprovisioned_subject_is_rejected() -> None:
    with pytest.raises(IdentityError, match="not provisioned"):
        IdentityService(MemoryIdentityRepository(None)).resolve(
            VerifiedIdentity(provider="test-provider", subject="verified-subject")
        )
