"""Promote reviewed admin-managed official sources for high-risk retrieval.

Revision ID: 20260825_0009
Revises: 20260823_0008
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260825_0009"
down_revision: str | None = "20260823_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE knowledge.sources AS source
        SET trust_tier = 1
        FROM ingestion.managed_source_configs AS config,
             knowledge.source_organizations AS organization
        WHERE config.source_id = source.id
          AND organization.id = source.organization_id
          AND config.registry_status = 'approved'
          AND config.production_eligible = true
          AND source.is_active = true
          AND organization.is_active = true
          AND organization.is_official = true
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE knowledge.sources AS source
        SET trust_tier = 2
        FROM ingestion.managed_source_configs AS config
        WHERE config.source_id = source.id
        """
    )
