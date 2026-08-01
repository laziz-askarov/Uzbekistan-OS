# Worker

The ingestion worker is implemented as the `app.worker` entrypoint in the shared Python package so it uses the same deterministic ingestion, repository, evidence-storage, and validation code as the API.

The deployable in this directory joins a Redis Stream consumer group, reclaims stale deliveries, schedules delayed retries, and dead-letters terminal work. PostgreSQL remains authoritative for idempotency, attempt counts, and terminal job state.

Run it through Docker Compose:

```bash
docker compose up --build worker
```

Manual enqueue is intentionally fail-closed and accepts only sources approved for automatic production ingestion. See [the worker runbook](../../docs/runbooks/worker.md) and [ADR 0009](../../docs/adr/0009-redis-stream-ingestion-worker.md).

Automated scheduling, a production source registry, registry-to-database synchronization, and live infrastructure drills remain pending.
