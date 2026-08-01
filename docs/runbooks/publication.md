# Knowledge publication runbook

## Safety boundary

Only trusted authentication middleware may construct a `VerifiedIdentity`. Resolve it to a provisioned, active internal principal before reviewer or publication services are called. Never accept provider, subject, principal ID, or roles from request headers or body fields unless a configured authentication adapter has cryptographically verified them.

Publication requires the `knowledge_publisher` or `admin` role. The `content_reviewer` role alone is intentionally insufficient.

## Transaction requirements

Run identity resolution, review lineage locking, and publication within a caller-owned SQLAlchemy session transaction. Repositories flush but do not commit. A successful transaction atomically persists:

- a new immutable document version;
- its reviewed source snapshot link;
- section-preserving chunks;
- the document's current-version pointer and published status;
- a one-to-one publication record for the review item; and
- an immutable `knowledge.published` audit event.

An exception must roll back the complete transaction. Do not retry by manually inserting missing rows.

## Preconditions

Before publishing, confirm that:

1. the principal is active and has publisher authorization;
2. the review item is `approved` and has a decision timestamp;
3. the extraction artifact bytes match the stored artifact checksum;
4. the artifact's raw checksum matches the reviewed source snapshot;
5. the source is active, approved for allowed/manual ingestion, and belongs to an active official organization;
6. every candidate section and its order exactly match the approved artifact;
7. every citation references that reviewed source and quoted text exists in its section;
8. domain and language are active; and
9. the candidate version is newer than the current document version.

The first successful publication stores a canonical candidate hash. Repeating that candidate is safe and returns the existing result. Reusing the same review item for different content produces `publication_conflict` and requires operator investigation.

## Failure handling

- `publication_forbidden`: verify role provisioning; do not grant a role from request data.
- `review_not_approved`: return the item to the normal review workflow.
- `artifact_integrity_failure` or `snapshot_lineage_mismatch`: stop publication and treat as an evidence-integrity incident.
- `candidate_artifact_mismatch` or citation mismatch: regenerate the candidate from the approved artifact; do not alter the evidence to fit the candidate.
- `source_not_publication_eligible` or `source_organization_not_eligible`: stop publication until the source registry and accountable approval process are complete.
- `document_identity_conflict`: use the intended document stream or correct the candidate slug.
- `version_not_monotonic`: choose the next valid version after checking the current published version.
- `publication_conflict`: compare the stored candidate hash and audit trail before any further action.

Published versions and audit events are immutable. Corrections are made through a new snapshot, extraction review, and higher document version. Database repair, if ever required, needs an approved incident procedure and a compensating audit event.

## Validation

From the repository root:

```bash
apps/api/.venv/bin/python -m ruff check apps/api scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head --sql
```

The SQL-only migration check verifies compilation, not live constraint or concurrency behavior. Run upgrade/downgrade and publication concurrency tests against disposable PostgreSQL before deployment.

## Current limitations

Authentication/token verification, reviewer and publisher HTTP routes, multi-source evidence packages, and live PostgreSQL integration tests are not implemented. The identity model does not resolve the open launch authentication decision. Docker-backed validation is pending because Docker is unavailable in this workspace.
