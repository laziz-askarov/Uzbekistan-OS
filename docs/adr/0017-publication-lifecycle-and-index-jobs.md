# ADR 0017: Auditable publication lifecycle and provider-neutral index jobs

- Status: Accepted
- Date: 2026-08-01

## Context

Phase 3 requires publishers to expire and re-index reviewed documents without
mutating immutable document versions. Index work must remain provider-neutral,
idempotent, observable, and unable to make expired or otherwise ineligible
content retrievable.

## Decision

- Expiration changes the stable document status to `expired` and appends one
  immutable lifecycle event per document version. The version itself is not
  edited.
- Every expiration and re-index request emits an immutable audit event carrying
  the authenticated principal and propagated request ID.
- Re-index requests are accepted only for the current, published, effective
  version and are idempotent on `(document_version_id, Idempotency-Key)`.
- Persist index-job attempts, bounded retry/dead-letter state, model routing key,
  token count, latency, and cost in integer micro-US-dollars.
- Keep the embedding provider behind a protocol. Validate vector count,
  dimensions, and finite values before storing an embedding.
- Keep `knowledge.retrievable_chunks` as the sole eligibility boundary. An index
  worker cancels work if the document becomes ineligible before claim.
- Do not add an ANN index or hard-code model dimensions until D-006 is accepted.

## Consequences

- Expiration is immediately fail-closed for retrieval even when old vectors
  remain stored.
- Exact expiration and re-index retries are safe; a reused caller key with a
  different model is a conflict.
- Provider selection, production dimensions, ANN parameters, and cost thresholds
  remain explicit launch decisions rather than domain-code constants.
- Corrections still require a new reviewed snapshot and a monotonically newer
  document version.
