# Worker

The ingestion worker is implemented as the `app.worker` entrypoint in the shared Python package so it uses the same deterministic ingestion, repository, evidence-storage, and validation code as the API.

The deployable in this directory supports three operational roles: registry synchronization, deterministic crawl scheduling, and Redis Stream consumption. The consumer reclaims stale deliveries, schedules delayed retries, and dead-letters terminal work. PostgreSQL remains authoritative for source lineage, job idempotency, attempt counts, and terminal state.

Run it through Docker Compose:

```bash
docker compose up --build worker
```

Compose applies migrations and runs `registry-sync` before the worker and scheduler. Manual enqueue and scheduling are intentionally fail-closed and accept only sources approved for automatic production ingestion in the matching environment registry. See [the worker runbook](../../docs/runbooks/worker.md), [ADR 0009](../../docs/adr/0009-redis-stream-ingestion-worker.md), and [ADR 0010](../../docs/adr/0010-registry-sync-and-crawl-scheduling.md).

Approved production sources, source-specific adapters, and live infrastructure drills remain pending.
