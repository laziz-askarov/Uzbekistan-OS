"""Add provider-neutral identity roles and publication lineage.

Revision ID: 20260731_0005
Revises: 20260731_0004
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0005"
down_revision: str | None = "20260731_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_REVIEWER_ROLE_ID = "00000000-0000-0000-0000-000000004001"
KNOWLEDGE_PUBLISHER_ROLE_ID = "00000000-0000-0000-0000-000000004002"
ADMIN_ROLE_ID = "00000000-0000-0000-0000-000000004003"


def upgrade() -> None:
    op.create_table(
        "principals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("display_name", sa.String(length=240), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("last_authenticated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="status_allowed"),
        sa.PrimaryKeyConstraint("id", name="pk_principals"),
        sa.UniqueConstraint(
            "provider",
            "subject",
            name="uq_principals_provider_subject",
        ),
        schema="identity",
    )

    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("key", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("key", name="uq_roles_key"),
        schema="identity",
    )

    roles = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", postgresql.CITEXT()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        schema="identity",
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": CONTENT_REVIEWER_ROLE_ID,
                "key": "content_reviewer",
                "name": "Content reviewer",
                "description": "May claim, compare, approve, and reject extraction artifacts.",
            },
            {
                "id": KNOWLEDGE_PUBLISHER_ROLE_ID,
                "key": "knowledge_publisher",
                "name": "Knowledge publisher",
                "description": "May publish approved, schema-valid knowledge candidates.",
            },
            {
                "id": ADMIN_ROLE_ID,
                "key": "admin",
                "name": "Administrator",
                "description": "May perform reviewer and publisher operations.",
            },
        ],
    )

    op.create_table(
        "principal_roles",
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by_principal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_principal_id"],
            ["identity.principals.id"],
            name="fk_principal_roles_granted_by_principal_id_principals",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["identity.principals.id"],
            name="fk_principal_roles_principal_id_principals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["identity.roles.id"],
            name="fk_principal_roles_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("principal_id", "role_id", name="pk_principal_roles"),
        schema="identity",
    )

    # NOT VALID preserves pre-identity development audit/review rows while enforcing new writes.
    op.execute(
        "ALTER TABLE ingestion.review_items "
        "ADD CONSTRAINT fk_review_items_assigned_user_id_principals "
        "FOREIGN KEY (assigned_user_id) REFERENCES identity.principals(id) "
        "ON DELETE RESTRICT NOT VALID"
    )
    op.execute(
        "ALTER TABLE audit.events "
        "ADD CONSTRAINT fk_events_actor_user_id_principals "
        "FOREIGN KEY (actor_user_id) REFERENCES identity.principals(id) "
        "ON DELETE RESTRICT NOT VALID"
    )

    op.create_table(
        "publication_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("review_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge.document_versions.id"],
            name="fk_publication_records_document_version_id_document_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_principal_id"],
            ["identity.principals.id"],
            name="fk_publication_records_published_by_principal_id_principals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_item_id"],
            ["ingestion.review_items.id"],
            name="fk_publication_records_review_item_id_review_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_publication_records"),
        sa.UniqueConstraint(
            "document_version_id",
            name="uq_publication_records_document_version_id",
        ),
        sa.UniqueConstraint("review_item_id", name="uq_publication_records_review_item_id"),
        schema="knowledge",
    )
    op.create_index(
        "ix_publication_records_published_by_principal_id",
        "publication_records",
        ["published_by_principal_id"],
        schema="knowledge",
    )


def downgrade() -> None:
    op.drop_table("publication_records", schema="knowledge")
    op.drop_constraint(
        "fk_events_actor_user_id_principals",
        "events",
        schema="audit",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_review_items_assigned_user_id_principals",
        "review_items",
        schema="ingestion",
        type_="foreignkey",
    )
    op.drop_table("principal_roles", schema="identity")
    op.drop_table("roles", schema="identity")
    op.drop_table("principals", schema="identity")
