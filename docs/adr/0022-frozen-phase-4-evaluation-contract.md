# ADR 0022: Frozen Phase 4 evaluation contract

**Status:** accepted for the Phase 4 evaluation boundary

**Date:** 2026-08-02

## Context

Phase 4 cannot approve retrieval or generation from unit tests alone. It needs a
repeatable multilingual benchmark that distinguishes a measured failure from
evidence that cannot yet be collected because production content or a model
route is unapproved. Citation, retrieval-quality, latency, and cost thresholds
also include open product and platform decisions and must not become accepted
merely because a number was checked into source control.

## Decision

- Freeze a versioned 45-case benchmark covering each of the 15 launch
  workflows in English, Uzbek, and Russian. Each workflow has a golden,
  adversarial, and abstention case.
- Record expected intent, domain, risk, response outcome, and source relevance
  labels in strict runtime-validated models. Answer cases without approved
  source labels carry an explicit `approved_content` blocker.
- Record whether an evaluation run has resolved the approved-content and
  model-route blockers. Metrics that rely on unresolved prerequisites remain
  unavailable rather than being counted as zero or as passing.
- Calculate planning exact accuracy, recall@8, MRR, nDCG@8, retrieval eligibility
  violations, claim-level citation coverage, citation validity, unsupported
  claims, schema/language/safety rates, abstention accuracy, latency percentiles,
  and maximum request cost deterministically.
- Keep thresholds separately versioned from benchmark cases. A proposed
  threshold always produces a blocked gate until its owner approves it.
- Make release status fail if any approved gate fails, blocked if no approved
  gate fails but any prerequisite or threshold approval is missing, and pass
  only when every gate is approved, sufficiently sampled, available, and met.
- Use command exit codes `0` for pass, `1` for fail, and `2` for blocked so CI and
  release automation cannot confuse incomplete evidence with success.

## Consequences

The deterministic planning and prompt-injection boundary can be evaluated now.
Retrieval and answer-quality evidence becomes executable as official content is
approved and the provider route is enabled. D-002 still owns citation-threshold
approval, D-006 still owns model routing and production cost/latency approval,
and Phase 3 source approval still owns expected-source labels.
