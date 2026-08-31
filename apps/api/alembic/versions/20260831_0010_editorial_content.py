"""Add secure, versioned editorial content workflow.

Revision ID: 20260831_0010
Revises: 20260825_0009
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260831_0010"
down_revision: str | None = "20260825_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONTENT_TABLES = (
    "authors",
    "posts",
    "post_versions",
    "post_sources",
    "post_relations",
    "media_assets",
    "publication_records",
)
CONTENT_AUTHOR_ROLE_ID = "00000000-0000-0000-0000-000000004004"


def upgrade() -> None:
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
                "id": CONTENT_AUTHOR_ROLE_ID,
                "key": "content_author",
                "name": "Content author",
                "description": "May create and revise editorial content drafts.",
            }
        ],
    )
    op.execute('CREATE SCHEMA IF NOT EXISTS "content"')

    op.create_table(
        "authors",
        sa.Column("principal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["principal_id"], ["identity.principals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("principal_id"),
        sa.UniqueConstraint("slug"),
        schema="content",
    )
    op.create_table(
        "posts",
        sa.Column("slug", postgresql.CITEXT(), nullable=False),
        sa.Column("content_type", sa.String(length=24), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("language_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "translation_group_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("created_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "content_type IN ('article', 'guide', 'platform_update', 'interview')",
            name=op.f("ck_posts_content_type_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')",
            name=op.f("ck_posts_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["domain_id"], ["knowledge.domains.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["language_id"], ["geography.languages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["created_by_principal_id"],
            ["identity.principals.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        schema="content",
    )
    op.create_index("ix_content_posts_domain_id", "posts", ["domain_id"], schema="content")
    op.create_index("ix_content_posts_language_id", "posts", ["language_id"], schema="content")
    op.create_index(
        "ix_content_posts_translation_group_id",
        "posts",
        ["translation_group_id"],
        schema="content",
    )
    op.create_index(
        "ix_content_posts_created_by_principal_id",
        "posts",
        ["created_by_principal_id"],
        schema="content",
    )
    op.create_index(
        "ix_content_posts_status_domain", "posts", ["status", "domain_id"], schema="content"
    )

    op.create_table(
        "post_versions",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column(
            "structured_content",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("seo_title", sa.String(length=70), nullable=True),
        sa.Column("seo_description", sa.String(length=200), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("hero_image_url", sa.Text(), nullable=True),
        sa.Column("hero_image_alt", sa.String(length=500), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_principal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("published_by_principal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "version_number >= 1", name=op.f("ck_post_versions_version_number_positive")
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'in_review', 'approved', 'published', 'stale', 'archived')",
            name=op.f("ck_post_versions_status_allowed"),
        ),
        sa.CheckConstraint(
            "status = 'draft' OR submitted_at IS NOT NULL",
            name=op.f("ck_post_versions_submission_fields_consistent"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('approved', 'published', 'stale', 'archived') OR "
            "(reviewed_by_principal_id IS NOT NULL AND reviewed_at IS NOT NULL)",
            name=op.f("ck_post_versions_review_fields_consistent"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('published', 'stale', 'archived') OR "
            "(published_by_principal_id IS NOT NULL AND published_at IS NOT NULL)",
            name=op.f("ck_post_versions_publication_fields_consistent"),
        ),
        sa.ForeignKeyConstraint(["post_id"], ["content.posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["content.authors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["created_by_principal_id"], ["identity.principals.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_principal_id"], ["identity.principals.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["published_by_principal_id"], ["identity.principals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "version_number", name="uq_content_post_version_number"),
        schema="content",
    )
    op.create_index(
        "ix_content_post_versions_post_id", "post_versions", ["post_id"], schema="content"
    )
    op.create_index(
        "ix_content_post_versions_author_id", "post_versions", ["author_id"], schema="content"
    )
    op.create_index(
        "ix_content_post_versions_status_review_due",
        "post_versions",
        ["status", "review_due_at"],
        schema="content",
    )

    op.add_column(
        "posts",
        sa.Column("published_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="content",
    )
    op.create_foreign_key(
        "fk_content_posts_published_version",
        "posts",
        "post_versions",
        ["published_version_id"],
        ["id"],
        source_schema="content",
        referent_schema="content",
        ondelete="SET NULL",
    )

    op.create_table(
        "post_sources",
        sa.Column("post_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_post_sources_sort_order_nonnegative")),
        sa.ForeignKeyConstraint(
            ["post_version_id"], ["content.post_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge.sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["knowledge.document_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "post_version_id", "source_id", "locator", name="uq_content_post_source_locator"
        ),
        schema="content",
    )
    op.create_index(
        "ix_content_post_sources_post_version_id",
        "post_sources",
        ["post_version_id"],
        schema="content",
    )
    op.create_index(
        "ix_content_post_sources_source_id", "post_sources", ["source_id"], schema="content"
    )

    op.create_table(
        "post_relations",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "post_id <> related_post_id", name=op.f("ck_post_relations_not_self_referential")
        ),
        sa.CheckConstraint(
            "relation_type IN ('related', 'next', 'previous')",
            name=op.f("ck_post_relations_relation_type_allowed"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name=op.f("ck_post_relations_sort_order_nonnegative")
        ),
        sa.ForeignKeyConstraint(["post_id"], ["content.posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_post_id"], ["content.posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "related_post_id", "relation_type"),
        schema="content",
    )

    op.create_table(
        "media_assets",
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=160), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("alt_text", sa.String(length=500), nullable=False),
        sa.Column("created_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("byte_size > 0", name=op.f("ck_media_assets_byte_size_positive")),
        sa.ForeignKeyConstraint(
            ["created_by_principal_id"], ["identity.principals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        schema="content",
    )

    op.create_table(
        "publication_records",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prior_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_principal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["content.posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["post_version_id"], ["content.post_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["prior_version_id"], ["content.post_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["published_by_principal_id"], ["identity.principals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_version_id"),
        schema="content",
    )
    op.create_index(
        "ix_content_publication_records_post_id",
        "publication_records",
        ["post_id"],
        schema="content",
    )
    op.create_index(
        "ix_content_publication_records_published_at",
        "publication_records",
        ["published_at"],
        schema="content",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION content.guard_post_version_update()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            IF OLD.status = 'draft'
               AND NEW.status NOT IN ('draft', 'in_review') THEN
                RAISE EXCEPTION 'invalid content revision transition: % -> %',
                    OLD.status, NEW.status;
            ELSIF OLD.status = 'in_review'
                  AND NEW.status NOT IN ('in_review', 'draft', 'approved') THEN
                RAISE EXCEPTION 'invalid content revision transition: % -> %',
                    OLD.status, NEW.status;
            ELSIF OLD.status = 'approved'
                  AND NEW.status NOT IN ('approved', 'draft', 'published') THEN
                RAISE EXCEPTION 'invalid content revision transition: % -> %',
                    OLD.status, NEW.status;
            ELSIF OLD.status = 'published'
                  AND NEW.status NOT IN ('published', 'stale', 'archived') THEN
                RAISE EXCEPTION 'invalid content revision transition: % -> %',
                    OLD.status, NEW.status;
            ELSIF OLD.status = 'stale' AND NEW.status NOT IN ('stale', 'archived') THEN
                RAISE EXCEPTION 'invalid content revision transition: % -> %',
                    OLD.status, NEW.status;
            ELSIF OLD.status = 'archived' AND NEW.status <> 'archived' THEN
                RAISE EXCEPTION 'archived content revisions are immutable';
            END IF;

            IF OLD.status <> 'draft' AND (
                NEW.title IS DISTINCT FROM OLD.title OR
                NEW.summary IS DISTINCT FROM OLD.summary OR
                NEW.body_markdown IS DISTINCT FROM OLD.body_markdown OR
                NEW.structured_content IS DISTINCT FROM OLD.structured_content OR
                NEW.seo_title IS DISTINCT FROM OLD.seo_title OR
                NEW.seo_description IS DISTINCT FROM OLD.seo_description OR
                NEW.canonical_url IS DISTINCT FROM OLD.canonical_url OR
                NEW.hero_image_url IS DISTINCT FROM OLD.hero_image_url OR
                NEW.hero_image_alt IS DISTINCT FROM OLD.hero_image_alt OR
                NEW.author_id IS DISTINCT FROM OLD.author_id OR
                NEW.checksum_sha256 IS DISTINCT FROM OLD.checksum_sha256
            ) THEN
                RAISE EXCEPTION 'non-draft content revisions cannot be edited';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_content_post_versions_guard
        BEFORE UPDATE ON content.post_versions
        FOR EACH ROW EXECUTE FUNCTION content.guard_post_version_update();
        """
    )

    op.execute('REVOKE ALL ON SCHEMA "content" FROM PUBLIC')
    for table in CONTENT_TABLES:
        op.execute(f'ALTER TABLE "content"."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL PRIVILEGES ON TABLE "content"."{table}" FROM PUBLIC')
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON SCHEMA content FROM %I', role_name);
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA content FROM %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END;
        $$;
        """
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA content REVOKE ALL PRIVILEGES ON TABLES FROM PUBLIC"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_content_post_versions_guard ON content.post_versions")
    op.execute("DROP FUNCTION IF EXISTS content.guard_post_version_update()")
    op.drop_table("publication_records", schema="content")
    op.drop_table("media_assets", schema="content")
    op.drop_table("post_relations", schema="content")
    op.drop_table("post_sources", schema="content")
    op.drop_constraint(
        "fk_content_posts_published_version", "posts", schema="content", type_="foreignkey"
    )
    op.drop_column("posts", "published_version_id", schema="content")
    op.drop_table("post_versions", schema="content")
    op.drop_table("posts", schema="content")
    op.drop_table("authors", schema="content")
    op.execute('DROP SCHEMA IF EXISTS "content"')
    op.execute(
        sa.text("DELETE FROM identity.roles WHERE id = CAST(:id AS uuid)").bindparams(
            id=CONTENT_AUTHOR_ROLE_ID
        )
    )
