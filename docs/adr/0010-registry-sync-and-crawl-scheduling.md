# ADR 0010: Environment-bound registry synchronization and crawl scheduling

- Status: Accepted for the scheduling slice
- Date: 2026-08-01

## Context

The reviewed JSON source registry is the approval authority for ingestion, while PostgreSQL owns source lineage and Redis delivers work. Before scheduling can run, registry entries must be materialized without turning database rows into a second approval system. Scheduling must also tolerate duplicate scheduler replicas and repeated polls without producing duplicate logical crawls.

## Decision

- Upgrade the registry contract to version 1.1 with an explicit organization country and an optional per-source schedule.
- Require the registry environment to exactly match `APP_ENV` before synchronization, enqueue, worker startup, or scheduler startup.
- Upsert organizations and sources by their stable registry UUIDs under a PostgreSQL advisory transaction lock. Reject slug, URL, country, or repeated-organization conflicts instead of guessing identity.
- Materialize only operational source fields in PostgreSQL. The reviewed registry remains authoritative for owner, adapter, language/domain coverage, approval, and scheduling policy.
- Mark registry-absent database sources and organizations inactive rather than deleting them, preserving evidence and publication lineage.
- Keep scheduling opt-in. A schedule is valid only for an approved, production-eligible source owned by an official organization with `crawl_policy: allowed`.
- Derive one UTC idempotency key per source interval slot. Do not backfill missed slots automatically.
- Atomically check the Redis deduplication marker, append the Stream message, and retain the marker with a bounded TTL in one Lua operation. PostgreSQL job uniqueness remains the final idempotency guard.
- Run registry synchronization as a deployment prerequisite and again at worker/scheduler startup so unsafe registry or database drift fails before ingestion.
- Keep the committed development fixture unscheduled and ineligible. This decision does not approve any production source or set a freshness policy.

## Consequences

- Removing a source from the environment registry disables its database row without destroying historical lineage.
- Multiple scheduler replicas can poll the same interval without normally adding duplicate Stream messages; a replay that bypasses Redis deduplication still converges on the database job identity.
- Operators must select source intervals and attempt limits during source approval. Those values are policy inputs, not application defaults for production content.
- Registry synchronization requires the referenced ISO 3166-1 alpha-2 country to exist in `geography.countries`.
- Live PostgreSQL/Redis concurrency and deployment-order drills remain required before production rollout.
