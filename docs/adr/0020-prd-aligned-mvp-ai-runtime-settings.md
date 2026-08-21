# ADR 0020: PRD-aligned MVP AI runtime settings

**Status:** accepted; model route approved 2026-08-21

**Date:** 2026-08-02

## Context

The MVP PRD requires grounded conversational guidance across Immigration,
Tourism, Business Registration, Healthcare, and Everyday Living in English,
Uzbek, and Russian. It calls for official citations, conversational memory,
streaming, first content under three seconds, average completion under eight
seconds, and at least 95% cited answers in benchmarks. D-006 was approved on
2026-08-21 with the runtime validation and rollback controls below.

The production adapter uses the Responses API with structured JSON output,
explicit low reasoning, and `store: false`. The provider model remains a
configuration-bound implementation detail rather than domain logic.

## Decision

- Treat the five PRD domains, three PRD languages, official-source-only
  retrieval, required citations, and provider response non-storage as product
  invariants rather than weakening feature flags.
- Configure retrieval to return at most eight chunks and evidence generation to
  accept at most six distinct cited chunks or 9,000 characters.
- Retain eight recent conversation turns and trigger a bounded summary after 12
  turns, with a 4,000-character summary ceiling and a 16,000-character total
  context ceiling. These are context budgets, not a retention-policy decision;
  D-008 remains open.
- Use targets of 2 seconds for the application-owned stream start, 3 seconds for
  first supported content, and 8 seconds for completion.
- Set the frozen benchmark citation-coverage target to at least 95%. Runtime
  answer validation remains stricter: every factual claim must carry validated
  evidence.
- Use `gpt-5.4-mini` at low reasoning for the balanced grounded-answer role,
  with a 7-second provider timeout, one attempt, 12,000 input tokens, 2,000
  output tokens, and a $0.05 request ceiling.
- Keep `AI_GENERATION_ENABLED=false` as the safe environment default while the
  checked-in route is approved. Deployment enablement still requires credentials,
  published eligible evidence, and staging evaluation gates.
- Validate all cross-setting invariants and registry linkage when the API is
  constructed. Enabling generation without an approved route or provider
  credential fails closed.

## Consequences

Development and staging expose the intended MVP operating envelope without
silently activating a paid external service. The provider-specific model name
is mapped to a provider-neutral role at the configuration boundary. Changing the
model, reasoning, budget, or approval status requires evaluation evidence and a
reviewed registry/configuration change; product workflows remain unchanged.
