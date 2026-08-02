# ADR 0020: PRD-aligned MVP AI runtime settings

**Status:** accepted for the Phase 4 configuration baseline

**Date:** 2026-08-02

## Context

The MVP PRD requires grounded conversational guidance across Immigration,
Tourism, Business Registration, Healthcare, and Everyday Living in English,
Uzbek, and Russian. It calls for official citations, conversational memory,
streaming, first content under three seconds, average completion under eight
seconds, and at least 95% cited answers in benchmarks. D-006 still requires a
measured production model-routing decision.

Current OpenAI guidance describes `gpt-5.6-terra` as the balanced intelligence
and cost tier and recommends low reasoning for latency-sensitive workloads. It
also recommends the Responses API for multi-turn workflows and explicit
reasoning settings. See the [GPT-5.6 model guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6)
and [Responses migration guidance](https://developers.openai.com/api/docs/guides/migrate-to-responses).

## Decision

- Treat the five PRD domains, three PRD languages, official-source-only
  retrieval, required citations, and provider response non-storage as product
  invariants rather than weakening feature flags.
- Configure retrieval to return at most eight chunks and evidence generation to
  accept at most six distinct cited chunks or 9,000 characters.
- Retain eight recent conversation turns and trigger a bounded summary after 12
  turns, with a 4,000-character summary ceiling. These are context budgets, not
  a retention-policy decision; D-008 remains open.
- Use targets of 2 seconds for the application-owned stream start, 3 seconds for
  first supported content, and 8 seconds for completion.
- Set the frozen benchmark citation-coverage target to at least 95%. Runtime
  answer validation remains stricter: every factual claim must carry validated
  evidence.
- Propose `gpt-5.6-terra` at low reasoning for the balanced grounded-answer role,
  with a 7-second provider timeout, one attempt, 12,000 input tokens, 2,000
  output tokens, and a $0.05 request ceiling.
- Keep the route status `proposed` and `AI_GENERATION_ENABLED=false`. D-006 may
  approve it only after representative English, Uzbek, and Russian evaluations
  meet groundedness, citation, latency, and cost thresholds.
- Validate all cross-setting invariants and registry linkage when the API is
  constructed. Enabling generation without an approved route or provider
  credential fails closed.

## Consequences

Development and staging expose the intended MVP operating envelope without
silently activating a paid external service. The provider-specific model name
is mapped to a provider-neutral role at the configuration boundary. Changing the
model, reasoning, budget, or approval status requires evaluation evidence and a
reviewed registry/configuration change; product workflows remain unchanged.
