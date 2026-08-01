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

## Failure triage

1. Confirm the registry entry remains approved and that its crawl policy has not changed.
2. Inspect the job's structured `error`, attempt count, and source URL without logging response bodies.
3. Treat timeouts, HTTP 408/425/429, and HTTP 5xx as candidates for bounded retry.
4. Treat redirects, unsupported content, oversized responses, changed destination URLs, and approval failures as permanent until reviewed.
5. Never move a snapshot into the publication path manually. Requeue through the same idempotent job boundary after correcting the cause.

## Current limitations

The Redis-backed worker loop, PDF extraction, authenticated review/decision APIs, compare UI, transactional publication, and production source entries are not implemented yet. The local and S3-compatible storage adapters are implemented, but live MinIO validation remains pending while Docker is unavailable.
