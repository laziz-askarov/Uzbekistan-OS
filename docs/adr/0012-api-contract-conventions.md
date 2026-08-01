# ADR 0012: API contract conventions

- Status: Accepted
- Date: 2026-08-01

## Context

The API already exposes structured success/error envelopes, request IDs,
Bearer-authenticated administration operations, cursor metadata, and a planned
SSE chat boundary. Phase 2 needs one provider-neutral policy that applies these
behaviors consistently across implemented and planned operations.

## Decision

### Versioning and ownership

- The checked-in OpenAPI 3.1 document is the public contract source of truth.
- Public endpoints live under `/api/v1`; the server URL supplies this prefix so
  contract paths do not repeat it.
- Planned operations remain in the contract with
  `x-implementation-status: planned` until runtime compatibility tests cover
  them.

### Envelopes and request correlation

- JSON success responses use `{ "data": ..., "meta": ... }`.
- JSON errors use `{ "error": { "code", "message", "details" }, "meta": ... }`.
- `meta.request_id` and the `X-Request-ID` response header carry the same
  application request identifier when one is available.
- Timestamps use RFC 3339 UTC values; identifiers are UUIDs unless a schema
  explicitly defines a stable slug or opaque token.

### Authentication and authorization

- Public, optional-principal, and authenticated operations are declared
  explicitly. There is no implicit authentication default.
- Role-gated operations declare their accepted application roles in the
  OpenAPI operation using `x-authorization`.
- Bearer tokens are trusted only after verification by the configured identity
  adapter. Missing or unavailable verification fails closed.
- Resource ownership and publication eligibility remain deterministic API
  rules and are never delegated to a model or client.

### Pagination

- Collection endpoints use opaque cursor pagination with shared `cursor` and
  `limit` parameters.
- A response supplies `meta.next_cursor`; `null` means there is no next page.
- Clients must not parse, synthesize, or modify cursors.

### Idempotency

- Retry-safe create, publish, and state-transition operations declare
  `x-idempotency` and accept the `Idempotency-Key` header when the operation
  requires a caller-provided key.
- Replaying the same key with an equivalent request returns the original
  outcome. Reusing the key for a different request returns a conflict error.
- Naturally idempotent reads and deterministic same-actor state replays do not
  require a caller-provided key but still document their replay behavior.

### Server-sent events

- Chat streaming exposes application-owned `start`, `chunk`, `citation`,
  `workflow`, `done`, and `error` events only.
- Every event carries a stream identifier and monotonic sequence number.
- Provider event names and payloads never cross the API boundary.
- A terminal `done` or `error` event ends the stream. Unsupported factual
  content must degrade to an insufficiency/error outcome rather than bypass
  evidence validation.

## Consequences

- Contract validation can enforce security, pagination, and idempotency
  metadata before the corresponding runtime operations are implemented.
- Generated clients receive stable envelopes and application-owned stream
  types independent of identity or AI providers.
- Adding an endpoint requires choosing authorization and replay semantics up
  front, which adds design work but prevents inconsistent client behavior.
