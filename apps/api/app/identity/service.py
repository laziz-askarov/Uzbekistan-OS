from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.ingestion.review import ReviewerContext, ReviewerRole


class IdentityError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    provider: str
    subject: str
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    id: UUID
    roles: frozenset[str]
    request_id: str | None = None

    def reviewer_context(self) -> ReviewerContext:
        reviewer_roles = frozenset(
            ReviewerRole(role)
            for role in self.roles
            if role in {ReviewerRole.CONTENT_REVIEWER.value, ReviewerRole.ADMIN.value}
        )
        return ReviewerContext(
            actor_user_id=self.id,
            roles=reviewer_roles,
            request_id=self.request_id,
        )


@dataclass(frozen=True, slots=True)
class PrincipalRecord:
    id: UUID
    status: str
    roles: frozenset[str]


class IdentityRepository(Protocol):
    def find_by_verified_subject(self, provider: str, subject: str) -> PrincipalRecord | None: ...

    def touch_authenticated(self, principal_id: UUID) -> None: ...


class IdentityService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def resolve(self, identity: VerifiedIdentity) -> AuthenticatedPrincipal:
        provider = identity.provider.strip()
        subject = identity.subject.strip()
        if not provider or not subject:
            raise IdentityError(
                "invalid_verified_identity",
                "verified identity provider and subject are required",
            )
        principal = self.repository.find_by_verified_subject(provider, subject)
        if principal is None:
            raise IdentityError("principal_not_provisioned", "principal is not provisioned")
        if principal.status != "active":
            raise IdentityError("principal_disabled", "principal is disabled")
        self.repository.touch_authenticated(principal.id)
        return AuthenticatedPrincipal(
            id=principal.id,
            roles=principal.roles,
            request_id=identity.request_id,
        )
