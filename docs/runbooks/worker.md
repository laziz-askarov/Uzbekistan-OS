# Ingestion worker runbook

## Start the worker

The complete local stack includes the `worker` service:

```bash
docker compose up --build worker
```

To run the installed Python package directly from the repository root:

```bash
apps/api/.venv/bin/python -m app.worker run
```

The worker creates or joins the configured Redis consumer group, promotes due retries, reclaims stale pending messages, then blocks for new work.

## Synchronize and schedule approved sources

Run an explicit synchronization during deployment:

```bash
apps/api/.venv/bin/python -m app.worker sync-registry
```

The command fails closed unless `APP_ENV` exactly matches the registry environment. It upserts stable registry organization/source UUIDs and deactivates database rows absent from the configured registry without deleting lineage. Docker Compose runs migrations and then the one-shot `registry-sync` service before the worker and scheduler.

Start the scheduler directly with:

```bash
apps/api/.venv/bin/python -m app.worker schedule
```

The scheduler enqueues only sources that are approved, production-eligible, configured with `crawl_policy: allowed`, and have a non-null schedule. Each source uses a deterministic UTC interval slot and bounded attempt count. Redis atomically deduplicates repeated polls and scheduler replicas. Missed slots are intentionally not backfilled.

## Enqueue one approved source

```bash
apps/api/.venv/bin/python -m app.worker enqueue \
  --source-id 00000000-0000-0000-0000-000000000000 \
  --idempotency-key manual:2026-08-01T00:00:00Z \
  --max-attempts 3
```

The command first synchronizes `WORKER_REGISTRY_PATH`, then fails closed unless the source is approved, production-eligible, and configured with `crawl_policy: allowed`. The registry environment must match `APP_ENV`.

Use a stable idempotency key for a logical fetch. Reusing a key replays a completed result and does not create duplicate snapshots or review items.

## Delivery and retry behavior

- Database work is committed before the Redis message is acknowledged.
- A database commit or queue operation failure leaves the Stream message pending for stale recovery.
- Retryable failures are scheduled with exponential backoff up to `WORKER_RETRY_MAX_SECONDS`.
- The locked database crawl job decides whether retry attempts remain.
- Invalid, unknown-source, ineligible, exhausted, and otherwise permanent work moves to `WORKER_DEAD_LETTER_STREAM`.
- `job_in_progress` is retried without consuming queue attempt metadata because another worker may still commit the same logical job.
- Scheduled work is deduplicated per source and UTC interval slot before it enters the Stream; PostgreSQL job uniqueness is still authoritative.

Do not manually change a crawl job from `dead_lettered` to a runnable state. Correct the source, registry, adapter, or infrastructure issue and enqueue a new reviewed operation with a new idempotency key.

## Failure triage

1. Correlate the Redis message source/key with `ingestion.crawl_jobs`.
2. Inspect the database job status and structured error before the queue envelope; PostgreSQL is authoritative.
3. Confirm the registry entry is still approved and its matching database source is active.
4. For pending messages, inspect consumer ownership and idle time before reclaiming.
5. For evidence-integrity or snapshot-collision errors, stop the source and follow the ingestion incident process.
6. Replay only through the enqueue boundary after correcting the cause.

## Stream maintenance

Acknowledged Redis Stream entries are retained for investigation. Before trimming, verify the consumer group has no affected pending entries and preserve dead-letter evidence according to the approved retention policy. Do not use a blind maximum-length trim in production because it can remove unacknowledged work.

## Validation

```bash
apps/api/.venv/bin/python -m ruff check apps/api scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests
apps/api/.venv/bin/python -m app.worker --help
```

Docker-backed failover, stale-claim, retry-promotion, and object-store drills remain pending while Docker is unavailable in this workspace.
