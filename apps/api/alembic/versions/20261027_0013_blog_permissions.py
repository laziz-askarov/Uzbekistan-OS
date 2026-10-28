"""Add independently assignable blog permissions."""

from alembic import op

revision = "20261027_0013"
down_revision = "20260831_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO identity.roles (key, name, description) VALUES
        ('blog_create', 'Create blogs', 'Create blog posts and author profiles.'),
        ('blog_edit', 'Edit blogs', 'Edit and submit blog drafts and create revisions.'),
        ('blog_publish', 'Publish blogs', 'Publish approved blog revisions.')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM identity.principal_roles WHERE role_id IN
        (SELECT id FROM identity.roles WHERE key IN ('blog_create','blog_edit','blog_publish'))
    """)
    op.execute("DELETE FROM identity.roles WHERE key IN ('blog_create','blog_edit','blog_publish')")
