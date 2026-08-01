# Ingestion operations runbook

## Validate the registry and ingestion code

From the repository root:

```bash
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests/test_ingestion.py
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

## Failure triage

1. Confirm the registry entry remains approved and that its crawl policy has not changed.
2. Inspect the job's structured `error`, attempt count, and source URL without logging response bodies.
3. Treat timeouts, HTTP 408/425/429, and HTTP 5xx as candidates for bounded retry.
4. Treat redirects, unsupported content, oversized responses, changed destination URLs, and approval failures as permanent until reviewed.
5. Never move a snapshot into the publication path manually. Requeue through the same idempotent job boundary after correcting the cause.

## Current limitations

The first slice uses a local filesystem snapshot adapter for tests and development. S3-compatible storage, the Redis-backed worker loop, PDF extraction, structured parsing, review APIs, and production source entries are not implemented yet.
