from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.identity.service import AuthenticatedPrincipal
from app.routes.blog_permissions import BlogGrantRequest, require_admin


@pytest.mark.parametrize(
    "roles",
    [
        [],
        ["blog_create"],
        ["blog_edit"],
        ["blog_publish"],
        ["content_author"],
        ["content_reviewer"],
    ],
)
def test_only_admin_can_assign_blog_permissions(roles):
    with pytest.raises(HTTPException) as error:
        require_admin(AuthenticatedPrincipal(id=uuid4(), roles=frozenset(roles)))
    assert error.value.status_code == 403


def test_admin_can_manage_permissions():
    require_admin(AuthenticatedPrincipal(id=uuid4(), roles=frozenset({"admin"})))


@pytest.mark.parametrize("permissions", [["admin"], ["content_reviewer"], ["knowledge_publisher"]])
def test_blog_grants_cannot_assign_staff_privileges(permissions):
    with pytest.raises(ValidationError):
        BlogGrantRequest(email="writer@example.com", permissions=permissions)


def test_empty_grant_revokes_all_blog_permissions():
    assert BlogGrantRequest(email="writer@example.com", permissions=[]).permissions == []


def test_grant_updates_only_blog_roles_and_audits_before_and_after():
    from unittest.mock import MagicMock

    from starlette.requests import Request

    from app.database.models.audit import AuditEvent
    from app.database.models.identity import Principal, PrincipalRole, Role
    from app.routes.blog_permissions import set_blog_permissions

    actor = AuthenticatedPrincipal(id=uuid4(), roles=frozenset({"admin"}), request_id="grant-1")
    target = Principal(
        id=uuid4(),
        provider="supabase",
        subject=str(uuid4()),
        email="writer@example.com",
        status="active",
    )
    roles = [
        Role(id=uuid4(), key=key, name=key, description=key)
        for key in ("blog_create", "blog_edit", "blog_publish")
    ]
    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = {
        "id": target.subject,
        "email": target.email,
    }
    session.scalar.return_value = target
    session.scalars.side_effect = [["blog_publish"], roles, ["blog_create", "blog_edit"]]
    request = Request({"type": "http", "state": {"request_id": "grant-1"}})
    result = set_blog_permissions(
        BlogGrantRequest(email=target.email, permissions=["blog_create", "blog_edit"]),
        request,
        actor,
        session,
    )
    assert result.data.permissions == ["blog_create", "blog_edit"]
    added = [call.args[0] for call in session.add.call_args_list]
    grants = [item for item in added if isinstance(item, PrincipalRole)]
    assert {item.role_id for item in grants} == {roles[0].id, roles[1].id}
    assert all(item.granted_by_principal_id == actor.id for item in grants)
    audit = next(item for item in added if isinstance(item, AuditEvent))
    assert audit.request_id == "grant-1"
    assert audit.payload == {"before": ["blog_publish"], "after": ["blog_create", "blog_edit"]}
    deletion = session.execute.call_args_list[1].args[0]
    assert set(deletion.compile().params["role_id_1"]) == {role.id for role in roles}


def test_non_admin_request_does_not_read_or_write_users():
    from unittest.mock import MagicMock

    from app.routes.blog_permissions import set_blog_permissions

    session = MagicMock()
    with pytest.raises(HTTPException):
        set_blog_permissions(
            BlogGrantRequest(email="writer@example.com", permissions=["blog_publish"]),
            MagicMock(),
            AuthenticatedPrincipal(id=uuid4(), roles=frozenset({"blog_publish"})),
            session,
        )
    assert session.mock_calls == []
