"""Add opt-in editorial retrieval chunks.

Revision ID: 20260831_0011
Revises: 20260831_0010
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260831_0011"
down_revision: str | None = "20260831_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "post_versions",
        sa.Column(
            "include_in_rag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="content",
    )
    op.create_table(
        "rag_chunks",
        sa.Column("post_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", sa.String(length=160), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("ordinal >= 0", name=op.f("ck_rag_chunks_ordinal_nonnegative")),
        sa.CheckConstraint("token_count > 0", name=op.f("ck_rag_chunks_token_count_positive")),
        sa.ForeignKeyConstraint(
            ["post_version_id"], ["content.post_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_version_id", "ordinal", name="uq_content_rag_chunk_ordinal"),
        schema="content",
    )
    op.create_index(
        "ix_content_rag_chunks_post_version_id",
        "rag_chunks",
        ["post_version_id"],
        schema="content",
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION content.guard_post_version_rag_update()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = ''
        AS $$
        BEGIN
            IF OLD.status <> 'draft'
               AND NEW.include_in_rag IS DISTINCT FROM OLD.include_in_rag THEN
                RAISE EXCEPTION 'non-draft RAG eligibility cannot be edited';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_content_post_versions_rag_guard
        BEFORE UPDATE ON content.post_versions
        FOR EACH ROW EXECUTE FUNCTION content.guard_post_version_rag_update();
        """
    )
    op.execute('ALTER TABLE "content"."rag_chunks" ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL PRIVILEGES ON TABLE "content"."rag_chunks" FROM PUBLIC')
    op.execute(
        """
        DO $$
        DECLARE role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON TABLE content.rag_chunks FROM %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_content_post_versions_rag_guard ON content.post_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS content.guard_post_version_rag_update()")
    op.drop_table("rag_chunks", schema="content")
    op.drop_column("post_versions", "include_in_rag", schema="content")
