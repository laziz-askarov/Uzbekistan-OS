"""Guarantee one editorial post per language in a translation group.

Revision ID: 20260831_0012
Revises: 20260831_0011
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0012"
down_revision: str | None = "20260831_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_content_posts_translation_language",
        "posts",
        ["translation_group_id", "language_id"],
        schema="content",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_content_posts_translation_language",
        "posts",
        schema="content",
        type_="unique",
    )
