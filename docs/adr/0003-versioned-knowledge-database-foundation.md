# ADR 0003: Versioned knowledge database foundation

- Status: Accepted
- Date: 2026-07-31

## Context

Ingestion and retrieval both require stable provenance, immutable document versions, explicit publication state, effective dates, multilingual variants, deterministic seed identifiers, and enforceable exclusion of ineligible content. The embedding model and dimensions remain an open routing decision.

## Decision

- Create all PostgreSQL namespaces from the DDS now, while implementing the first tables only in `geography`, `knowledge`, `ingestion`, and `audit`.
- Treat `knowledge.documents` as stable identities and `knowledge.document_versions` as immutable content records.
- Point each published document to exactly one current version.
- Expose `knowledge.retrievable_chunks` as the eligibility boundary: only current, published, effective versions can appear.
- Store source snapshots outside PostgreSQL while retaining their storage key and SHA-256 provenance in PostgreSQL.
- Store vectors without a fixed dimension until D-006 selects the embedding model. Add the ANN index in the same migration that fixes the production embedding role and dimensions.
- Seed languages, Uzbekistan, and the five MVP domains with deterministic UUIDs.

## Consequences

- Publishing must be transactional: persist a reviewed version, set its publication timestamp, move the document's current-version pointer, and change the document status together.
- Retrieval code must query the eligibility view instead of raw chunks.
- No vector ANN index exists yet; early fixtures can be stored, but production semantic retrieval remains gated on D-006.
- Identity, workflow, conversation, and AI observability tables remain follow-up migrations with independent review.

