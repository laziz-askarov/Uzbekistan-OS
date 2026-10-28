"""Admin-controlled editorial grants; evaluated from the database on every request."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.database.models.audit import AuditEvent
from app.database.models.identity import Principal, PrincipalRole, Role
from app.database.session import get_database_session
from app.dependencies import get_authenticated_principal
from app.identity.service import AuthenticatedPrincipal
from app.schemas import ResponseMeta, SuccessResponse

router = APIRouter(prefix="/admin/blog-permissions", tags=["editorial content"])
BlogPermission = Literal["blog_create", "blog_edit", "blog_publish"]
BLOG_PERMISSIONS = frozenset({"blog_create", "blog_edit", "blog_publish"})


class BlogGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    permissions: list[BlogPermission] = Field(max_length=3)


class BlogUserData(BaseModel):
    id: UUID
    email: str | None
    permissions: list[BlogPermission]


def require_admin(principal: AuthenticatedPrincipal) -> None:
    if "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Administrator permission is required")


def user_data(session: Session, user: Principal) -> BlogUserData:
    roles = session.scalars(
        select(Role.key)
        .join(PrincipalRole, PrincipalRole.role_id == Role.id)
        .where(PrincipalRole.principal_id == user.id, Role.key.in_(BLOG_PERMISSIONS))
    )
    return BlogUserData(id=user.id, email=user.email, permissions=sorted(roles))


@router.get(
    "", response_model=SuccessResponse[list[BlogUserData]], operation_id="listBlogPermissions"
)
def list_blog_permissions(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    session: Annotated[Session, Depends(get_database_session)],
) -> SuccessResponse[list[BlogUserData]]:
    require_admin(principal)
    users = session.scalars(
        select(Principal)
        .where(
            Principal.id.in_(
                select(PrincipalRole.principal_id)
                .join(Role, Role.id == PrincipalRole.role_id)
                .where(Role.key.in_(BLOG_PERMISSIONS))
            )
        )
        .order_by(Principal.email)
        .limit(200)
    )
    return SuccessResponse(
        data=[user_data(session, user) for user in users],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.put("", response_model=SuccessResponse[BlogUserData], operation_id="setBlogPermissions")
def set_blog_permissions(
    payload: BlogGrantRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    session: Annotated[Session, Depends(get_database_session)],
) -> SuccessResponse[BlogUserData]:
    require_admin(principal)
    # Resolve a registered, non-anonymous Supabase account; never trust a submitted user ID.
    account = (
        session.execute(
            text(
                "SELECT id, email FROM auth.users WHERE lower(email) = lower(:email) "
                "AND is_anonymous = false AND deleted_at IS NULL"
            ),
            {"email": payload.email.strip()},
        )
        .mappings()
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Registered user not found")
    user = session.scalar(
        select(Principal)
        .where(Principal.provider == "supabase", Principal.subject == str(account["id"]))
        .with_for_update()
    )
    if user is None:
        user = Principal(
            provider="supabase", subject=str(account["id"]), email=account["email"], status="active"
        )
        session.add(user)
        session.flush()
    before = user_data(session, user).permissions
    roles = list(session.scalars(select(Role).where(Role.key.in_(BLOG_PERMISSIONS))))
    if len(roles) != len(BLOG_PERMISSIONS):
        raise HTTPException(status_code=503, detail="Blog permissions migration is required")
    session.execute(
        delete(PrincipalRole).where(
            PrincipalRole.principal_id == user.id,
            PrincipalRole.role_id.in_([role.id for role in roles]),
        )
    )
    for role in roles:
        if role.key in payload.permissions:
            session.add(
                PrincipalRole(
                    principal_id=user.id, role_id=role.id, granted_by_principal_id=principal.id
                )
            )
    session.add(
        AuditEvent(
            actor_user_id=principal.id,
            action="content.permissions_updated",
            entity_type="principal",
            entity_id=user.id,
            request_id=principal.request_id,
            payload={"before": before, "after": sorted(set(payload.permissions))},
        )
    )
    session.flush()
    return SuccessResponse(
        data=user_data(session, user), meta=ResponseMeta(request_id=request.state.request_id)
    )
