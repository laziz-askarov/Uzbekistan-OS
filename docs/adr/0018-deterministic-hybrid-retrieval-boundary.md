# ADR 0018: Deterministic hybrid retrieval boundary

**Status:** accepted for the Phase 4 core

**Date:** 2026-08-01

## Context

Phase 3 established the only publication and effective-date eligibility view,
reviewed citation lineage, semantic chunks, and provider-neutral embeddings.
Phase 4 needs query planning and hybrid retrieval without allowing generated
model output, stale vectors, disabled sources, or retrieved instructions to
expand that eligibility boundary.

## Decision

- Plan retrieval with typed deterministic outputs before introducing a model
  planner. The plan records language, launch intent, domains, risk, source trust
  tiers, applicability context, and a reproducible fingerprint.
- Treat Immigration, Business Registration, and Healthcare plans as high risk
  and restrict them to tier-one official sources. Other MVP domains may use
  reviewed tier-one or tier-two official sources.
- Query `knowledge.retrievable_chunks` for both lexical and vector candidates,
  then additionally require every linked source and organization to remain
  active, official, and approved for automatic or manual ingestion.
- Use PostgreSQL full-text search and exact pgvector distance initially. Fuse
  independent rankings with weighted reciprocal-rank fusion; do not compare or
  normalize provider-specific raw scores.
- Apply language, domain, trust, and applicability filters again in the service
  layer. Conflicting lineage for the same chunk is an integrity failure.
- Build bounded evidence packs only from cited, distinct chunks. Quarantine
  retrieved content containing orchestration delimiters or instruction-override
  patterns and return an explicit insufficiency result when no safe evidence
  remains.
- Keep the public search and chat APIs planned until retrieval evaluation and
  source approval gates pass.

## Consequences

Retrieval cannot bypass publication, effective-date, source-support, language,
or applicability rules. The same deterministic planner can serve evaluation and
future model-plan validation. Exact vector scans are acceptable for fixtures,
but production ANN dimensions and indexes remain blocked on D-006. Keyword
planning is deliberately conservative and must be evaluated before a model
planner can be introduced behind the same typed schema.
