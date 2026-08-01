# ADR 0009: Redis Stream ingestion worker with database-authoritative retries

- Status: Accepted for the worker-loop slice
- Date: 2026-08-01

## Context

The ingestion domain already provides exact-URL fetching, evidence storage, idempotent database jobs, bounded retries, dead-letter states, extraction, and review creation. It needs a deployable queue consumer that remains safe across duplicate delivery, process crashes, concurrent workers, Redis failures, and database commit failures.

## Decision

- Use a Redis Stream consumer group for ingestion delivery. Queue messages contain only a source UUID, idempotency key, bounded attempt metadata, and enqueue timestamp.
- Validate every message with a strict schema, cap payload size, and dead-letter malformed or unknown-source messages without opening a database transaction.
- Load sources from the environment's reviewed source registry and reject manual enqueue unless the source is approved and production-eligible for automatic fetching.
- Keep the PostgreSQL crawl job as the retry and terminal-state authority. Redis attempt metadata is operational context and cannot override the locked database record.
- Commit a successful or failed ingestion attempt before acknowledging its Redis delivery. A database commit failure leaves the delivery pending.
- Recover stale pending messages with `XAUTOCLAIM`. A replay after a committed success returns the stored idempotent outcome and can be acknowledged safely.
- Schedule retries in a sorted set with exponential backoff. Add the retry and acknowledge the original Stream entry in one Redis transaction.
- Promote due retries with a Lua operation that removes each sorted-set member and appends it to the Stream atomically.
- Move terminal and invalid deliveries to a dedicated Redis dead-letter Stream and acknowledge the original in one Redis transaction.
- Do not automatically schedule real sources yet. Operators may use the explicit enqueue command after the source registry and matching database source row are approved.

The scheduling deferral above was superseded by the fail-closed, opt-in design in [ADR 0010](./0010-registry-sync-and-crawl-scheduling.md). No production source was approved as part of that later slice.

## Consequences

- Worker replicas can share one consumer group without bypassing database idempotency or concurrency locks.
- A process or queue failure after a database commit causes replay rather than duplicate evidence or review work.
- Redis retains acknowledged Stream entries until an operator performs a pending-aware trim; retention must be defined before production rollout.
- The committed development registry cannot enqueue work because it is intentionally non-production and pending review.
- Live Redis/PostgreSQL/MinIO crash and concurrency drills remain required before production deployment.
