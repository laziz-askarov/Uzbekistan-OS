from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.identity import Principal, PrincipalRole, Role
from app.identity.service import PrincipalRecord


class SqlAlchemyIdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_verified_subject(self, provider: str, subject: str) -> PrincipalRecord | None:
        principal = self.session.scalar(
            select(Principal).where(
                Principal.provider == provider,
                Principal.subject == subject,
            )
        )
        if principal is None:
            return None
        roles = frozenset(
            self.session.scalars(
                select(Role.key)
                .join(PrincipalRole, PrincipalRole.role_id == Role.id)
                .where(PrincipalRole.principal_id == principal.id)
            )
        )
        return PrincipalRecord(id=principal.id, status=principal.status, roles=roles)

    def touch_authenticated(self, principal_id: UUID) -> None:
        principal = self.session.get(Principal, principal_id)
        if principal is None:
            raise RuntimeError(f"principal does not exist: {principal_id}")
        principal.last_authenticated_at = datetime.now(UTC)
        self.session.flush()
