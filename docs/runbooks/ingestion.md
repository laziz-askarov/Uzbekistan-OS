# Ingestion operations runbook

## Validate the registry and ingestion code

From the repository root:

```bash
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ingestion.py apps/api/tests/test_object_store.py
apps/api/.venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head --sql
```

The committed development registry is not eligible for automatic fetching. A production run must fail closed until an approved registry entry is supplied.

## Job semantics

- `queued`: ready for a worker claim.
- `running`: one worker owns the current attempt.
- `retry_scheduled`: a transient failure may be retried while attempts remain.
- `succeeded`: the stored result is replayed for the same idempotency key.
- `dead_lettered`: attempts are exhausted or the failure is permanent.
- `cancelled`: an operator stopped the job.

The unique `(source_id, idempotency_key)` constraint is the final concurrency guard. Workers must commit the job transition and snapshot metadata in one database transaction. A content-addressed object left behind by a failed transaction is safe to reconcile because writing different bytes to the same key is prohibited.

## Object storage

Raw source responses and canonical extraction artifacts share the S3-compatible evidence bucket. The adapter stores a SHA-256 value in object metadata and verifies it before accepting a repeated write.

- Set `S3_AUTO_CREATE_BUCKET=true` only for local development.
- Pre-provision and encrypt staging/production buckets; leave auto-creation disabled.
- Restrict the worker identity to the evidence bucket and deny public access.
- Treat a `snapshot_collision` as an integrity incident rather than retrying it.

Each changed snapshot produces one schema-versioned extraction artifact and one `pending` review item. Unchanged responses do not create new review work.

## Reviewer controls

The application review service accepts only a trusted context with a verified actor UUID and the `content_reviewer` or `admin` role. Do not build this context from request headers or body fields.

Legal transitions are:

```text
pending -> in_review -> approved
                     -> rejected
```

- The row must be locked and the review update plus audit insert committed together.
- Only the assigned reviewer may approve or reject the item.
- Record a concise decision reason without personal or applicant information.
- Approval confirms extraction quality only; it does not publish knowledge.
- Audit events cannot be updated or deleted. Corrections require a new compensating event.
- Artifact comparison verifies stored bytes against database lineage before producing a section-level diff.

## Failure triage

1. Confirm the registry entry remains approved and that its crawl policy has not changed.
2. Inspect the job's structured `error`, attempt count, and source URL without logging response bodies.
3. Treat timeouts, HTTP 408/425/429, and HTTP 5xx as candidates for bounded retry.
4. Treat redirects, unsupported content, oversized responses, changed destination URLs, and approval failures as permanent until reviewed.
5. Never move a snapshot into the publication path manually. Requeue through the same idempotent job boundary after correcting the cause.

## Registry synchronization and scheduling

Registry version 1.1 is synchronized into PostgreSQL before the worker and scheduler start. Synchronization fails if the registry environment does not match `APP_ENV`, if an organization country is not seeded, or if stable IDs conflict with an existing slug or URL. Entries absent from the configured environment registry are marked inactive, never deleted.

Only approved, production-eligible, automatically crawlable entries with a non-null schedule receive UTC interval slots. Redis deduplicates a source/slot atomically, while `(source_id, idempotency_key)` remains the database concurrency guard. Missed slots are not backfilled automatically.

## Current limitations

The Redis-backed worker loop, manual enqueue boundary, environment-bound registry synchronization, and opt-in scheduler are implemented. PDF extraction, a production authentication adapter, compare UI, source-specific production adapters, and approved production source entries are not implemented yet. The role-gated review and comparison services, provider-neutral identity mapping, administration routes, and transactional publication core are implemented. Worker and publication operations are documented in [worker.md](./worker.md) and [publication.md](./publication.md). Live Redis/PostgreSQL/MinIO validation remains pending while Docker is unavailable.
