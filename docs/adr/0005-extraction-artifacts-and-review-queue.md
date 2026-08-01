# ADR 0005: Extraction artifacts and review queue

- Status: Accepted for the second ingestion slice
- Date: 2026-07-31

## Context

Raw source bytes are necessary evidence but are not directly reviewable or safe to publish. The ingestion path needs a deterministic intermediate representation, production-compatible object storage, and an explicit handoff to human review without coupling extraction to publication.

## Decision

- Store raw snapshots and canonical extraction JSON through one content-addressed object-store port with local filesystem and S3-compatible adapters.
- Verify the SHA-256 metadata of an existing S3 object before treating a repeated write as successful. Reject key collisions.
- Auto-create the development bucket only when `S3_AUTO_CREATE_BUCKET=true`; production infrastructure must provision buckets explicitly.
- Represent pre-review extraction as schema-versioned JSON containing source and snapshot lineage, adapter identity, raw and normalized hashes, retrieval time, media type, and heading-preserving sections.
- Persist extraction-artifact metadata separately from raw snapshots so future adapter/schema revisions can coexist.
- Enqueue exactly one review item per extraction artifact. New items begin in `pending`; no ingestion code can publish knowledge.

## Consequences

- Reviewers can compare stable structured artifacts while retaining exact raw evidence.
- Storage writes are safe to replay, and PostgreSQL remains the authoritative lineage/index layer.
- The generic extractor supports HTML and text only. PDF-specific extraction requires a separate reviewed adapter.
- Reviewer assignment/decision APIs, authorization, audit events, comparison UI, and transactional knowledge publication remain subsequent work.
