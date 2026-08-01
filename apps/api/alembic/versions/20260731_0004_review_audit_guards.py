"""Guard reviewer state consistency and audit immutability.

Revision ID: 20260731_0004
Revises: 20260731_0003
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260731_0004"
down_revision: str | None = "20260731_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "assignment_consistent",
        "review_items",
        "(status = 'pending' AND assigned_user_id IS NULL) OR "
        "(status IN ('in_review', 'approved', 'rejected') AND assigned_user_id IS NOT NULL) OR "
        "status = 'cancelled'",
        schema="ingestion",
    )
    op.create_check_constraint(
        "decision_fields_consistent",
        "review_items",
        "(status IN ('approved', 'rejected') AND decision_reason IS NOT NULL "
        "AND length(btrim(decision_reason)) > 0 AND decided_at IS NOT NULL) OR "
        "(status NOT IN ('approved', 'rejected') AND decision_reason IS NULL "
        "AND decided_at IS NULL)",
        schema="ingestion",
    )
    op.execute(
        """
        CREATE FUNCTION audit.prevent_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit events are immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit.events
        FOR EACH ROW EXECUTE FUNCTION audit.prevent_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit.events")
    op.execute("DROP FUNCTION IF EXISTS audit.prevent_event_mutation()")
    op.drop_constraint(
        op.f("ck_review_items_decision_fields_consistent"),
        "review_items",
        schema="ingestion",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_review_items_assignment_consistent"),
        "review_items",
        schema="ingestion",
        type_="check",
    )
