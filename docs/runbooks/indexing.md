# Knowledge indexing runbook

## Eligibility and queueing

Only a `knowledge_publisher` or `admin` may call
`POST /api/v1/admin/documents/{document_id}/reindex`. The request requires an
`Idempotency-Key` header and a configured model-routing key. The API persists a
job only when the selected version is current, published, and effective on the
request date.

The unique `(document_version_id, idempotency_key)` constraint is the final
concurrency guard. An exact replay returns the existing job; a replay naming a
different model returns `index_job_conflict`.

## Worker behavior

The database-authoritative index repository claims only `queued` or due
`retry_scheduled` jobs. On claim it rechecks the same retrieval eligibility used
by the public retrieval view. If the document was expired, superseded, archived,
or moved outside its effective dates, the job becomes `cancelled` and no provider
call is made.

The provider-neutral processor:

1. submits chunks in ordinal order through the configured embedding interface;
2. rejects mismatched vector counts, inconsistent/zero dimensions, and non-finite
   values;
3. upserts one embedding per chunk and model key;
4. records tokens, duration in milliseconds, cost in micro-US-dollars, vector
   dimensions, and chunk count; and
5. retries only explicitly transient provider failures with bounded exponential
   backoff, then dead-letters exhausted/permanent failures.

## Validation

The fast suite exercises provider validation, retry/dead-letter decisions,
telemetry, semantic chunk provenance, authorization, and API contracts. The live
PostgreSQL test is opt-in and rolls back its fixture transaction:

```bash
PHASE3_INTEGRATION_DATABASE_URL=postgresql+psycopg://uzbekistan_os:local-development-only@localhost:5432/uzbekistan_os \
  apps/api/.venv/bin/python -m pytest apps/api/tests/integration/test_phase3_postgres.py
```

Production model/provider selection, dimensions, ANN parameters, budgets, and
evaluation thresholds remain blocked by D-006. Do not substitute the development
role name for an approved production model.
