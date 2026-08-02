# ADR 0019: Grounded model orchestration boundary

**Status:** accepted for the Phase 4 core

**Date:** 2026-08-01

## Context

Hybrid retrieval now produces bounded, cited evidence packs. Generated output is
still untrusted and must not become user-visible merely because a provider
returned schema-shaped JSON. Phase 4 also requires prompt versioning, provider
portability, bounded retries, and enforceable latency, token, storage, and cost
controls before a production model or embedding route is approved in D-006.

## Decision

- Store layered prompts as immutable, versioned registry entries. Resolve exactly
  one active version per prompt key and fingerprint all behavior-bearing fields.
- Route by provider-neutral model roles. Provider/model identifiers belong in
  adapters and deployment configuration, never domain logic.
- Reject unapproved or disabled routes and missing providers. Enforce estimated
  input, requested output, reported usage, cost, attempt, and timeout budgets.
- Set provider response storage to false at both the route and request boundary.
- Never invoke a model when the evidence pack is insufficient.
- Require the `grounded-answer.v1` shape. Every factual claim has one or more
  evidence identifiers and an exact quote from the cited chunk.
- Validate language, evidence identity, exact quote membership, and conservative
  lexical support after schema validation. Any failure replaces the entire answer
  with a localized, hard-coded insufficiency response.
- Treat evidence as untrusted data in the system prompt. Prompt content cannot
  weaken API-layer publication, applicability, or citation rules.

## Consequences

The core can be tested without network access or a selected provider. Runtime use
remains fail-closed until D-006 approves and configures a model route and adapter.
Exact-quote and lexical coverage checks are deterministic safety gates, not proof
of semantic entailment; the evaluation suite and later claim verifier must measure
false acceptance and false rejection. Provider adapters must honor the supplied
timeout while the gateway also rejects calls that return after the route deadline.
