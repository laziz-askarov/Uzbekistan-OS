# ADR 0014: Approved MVP launch workflows

Date: 2026-08-01

Status: Accepted

Decision: D-001

## Context

Phase 2 required a bounded set of 10–15 high-value workflows before product-flow
contracts could be closed. Without a portfolio decision, source prioritization,
domain modeling, retrieval evaluation, and responsive acceptance could not share a
stable target.

## Decision

The 15 workflows in `docs/product/launch-workflows.md` are the approved initial
portfolio. They cover Arrival & Entry, Visa Eligibility, Foreigner Registration,
Moving, LLC Formation, Temporary Residence, Work, Study, Banking, PINFL,
Healthcare, Renting, Personal Imports, Stay Extension, and Departure.

The shared responsive and accessibility contract in
`docs/product/responsive-flow-wireframes.md` applies to each workflow. High-risk
procedural outputs remain fail-closed: the API must not provide a result when
applicability, freshness, source support, or publication eligibility cannot be
established.

## Consequences

- Product, content, and domain work can prioritize sources and rules against a
  stable initial portfolio.
- Cross-workflow dependencies must use stable workflow identifiers and avoid
  duplicating domain rules.
- Portfolio approval does not approve source URLs or authorize crawling.
- Additions or removals require a scope decision and updated acceptance evidence.
