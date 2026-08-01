# ADR 0004: Safe, idempotent ingestion boundary

- Status: Accepted for the first ingestion slice
- Date: 2026-07-31

## Context

Source ingestion handles externally controlled bytes and can accidentally publish stale, unapproved, or unsupported guidance. It must remain reproducible across retries and preserve exact evidence even before the queue runtime, reviewer API, and first production sources are selected.

## Decision

- Keep source approval in a schema-backed registry. Automatic fetching requires an approved entry, `allowed` crawl policy, production eligibility, an owner, and a review timestamp.
- Fetch only the exact registered URL and reject redirects. Production source discovery and arbitrary URL fetching are not supported.
- Store raw responses under a content-addressed key and retain raw and normalized SHA-256 values, response metadata, byte size, and retrieval time in PostgreSQL.
- Normalize supported HTML and text deterministically. Unsupported media types fail closed until a reviewed per-type adapter exists.
- Identify jobs by `(source_id, idempotency_key)`. A completed job replays its result without fetching again.
- Use bounded attempts with explicit `retry_scheduled` and `dead_lettered` states. Only transient transport and HTTP failures are retryable.
- Stop this slice at an immutable, normalized snapshot. No fetched content becomes a published knowledge version without validation and human review.

## Consequences

- Retries cannot silently create duplicate snapshot records or repeat a completed fetch.
- Exact source bytes and change decisions remain auditable.
- The generic adapter intentionally supports only HTML and text. ADR 0005 adds structured artifacts, S3-compatible storage, and queue creation; PDF extraction, reviewer actions, and scheduling remain later Phase 3 work.
- No real source is authorized by this ADR; accountable owners must still resolve launch workflow, crawl permission, precedence, and freshness decisions.
